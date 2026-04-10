import json
import os
import logging
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

import boto3
import time  # make sure this is at top
glue_client = boto3.client("glue")  # make sure this is at top

# ── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── AWS Clients ──────────────────────────────────────────────────────────────
s3_client = boto3.client("s3")
sns_client = boto3.client("sns")

# ── Config ───────────────────────────────────────────────────────────────────
API_KEY = os.environ["YOUTUBE_API_KEY"]
BUCKET = os.environ["S3_BUCKET_BRONZE"]
REGIONS = os.environ.get("YOUTUBE_REGIONS", "US,GB,CA,DE,FR,IN,JP,KR,MX,RU").split(",")
SNS_TOPIC = os.environ.get("SNS_ALERT_TOPIC_ARN", "")
API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_RESULTS = 50


def fetch_trending_videos(region_code: str) -> dict:
    """
    Call the YouTube Data API to get the current trending videos
    for a given region.
    """
    params = urlencode({
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": MAX_RESULTS,
        "key": API_KEY,
    })
    url = f"{API_BASE}/videos?{params}"

    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_video_categories(region_code: str) -> dict:
    """
    Fetch the video category mapping for a region.
    This replaces the static JSON reference files from Kaggle.
    """
    params = urlencode({
        "part": "snippet",
        "regionCode": region_code,
        "key": API_KEY,
    })
    url = f"{API_BASE}/videoCategories?{params}"

    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_to_s3(data: dict, bucket: str, key: str) -> dict:
    """Write JSON data to S3 with metadata."""
    body = json.dumps(data, ensure_ascii=False, indent=2)
    response = s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/json",
        Metadata={
            "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "youtube_data_api_v3",
        },
    )
    return response


def send_alert(subject: str, message: str):
    """Send failure alert via SNS."""
    if SNS_TOPIC:
        sns_client.publish(
            TopicArn=SNS_TOPIC,
            Subject=subject[:100],
            Message=message,
        )


def lambda_handler(event, context):
    """
    Main handler. Iterates over regions, fetches trending videos
    and category mappings, writes everything to Bronze layer.
    """
    now = datetime.now(timezone.utc)
    date_partition = now.strftime("%Y-%m-%d")
    hour_partition = now.strftime("%H")
    ingestion_id = now.strftime("%Y%m%d_%H%M%S")

    results = {"success": [], "failed": []}

    for region in REGIONS:
        region = region.strip().lower()
        logger.info(f"Processing region: {region}")

        # ── Fetch trending videos ────────────────────────────────────────
        try:
            trending_data = fetch_trending_videos(region)
            video_count = len(trending_data.get("items", []))

            # Add pipeline metadata to the raw response
            trending_data["_pipeline_metadata"] = {
                "ingestion_id": ingestion_id,
                "region": region,
                "ingestion_timestamp": now.isoformat(),
                "video_count": video_count,
                "source": "youtube_data_api_v3",
            }

            # S3 key with Hive-style partitioning
            # s3://bucket/youtube/raw_statistics/region=US/date=2026-03-02/hour=14/data.json
            s3_key = (
                f"raw_data/"
                f"region={region}/"
                f"date={date_partition}/"
                f"hour={hour_partition}/"
                f"{ingestion_id}.json"
            )
            write_to_s3(trending_data, BUCKET, s3_key)
            logger.info(f"  Wrote {video_count} videos → s3://{BUCKET}/{s3_key}")

        except (HTTPError, URLError) as e:
            logger.error(f"  API error for {region} trending: {e}")
            results["failed"].append({"region": region, "type": "trending", "error": str(e)})
            continue
        except Exception as e:
            logger.error(f"  Unexpected error for {region} trending: {e}")
            results["failed"].append({"region": region, "type": "trending", "error": str(e)})
            continue

        # ── Fetch category reference data ────────────────────────────────
        try:
            category_data = fetch_video_categories(region)
            category_data["_pipeline_metadata"] = {
                "ingestion_id": ingestion_id,
                "region": region,
                "ingestion_timestamp": now.isoformat(),
                "source": "youtube_data_api_v3",
            }

            ref_key = (
                f"raw_data/"
                f"region={region}/"
                f"date={date_partition}/"
                f"{region}_category_id.json"
            )
            write_to_s3(category_data, BUCKET, ref_key)
            logger.info(f"  Wrote categories → s3://{BUCKET}/{ref_key}")

        except (HTTPError, URLError) as e:
            logger.error(f"  API error for {region} categories: {e}")
            results["failed"].append({"region": region, "type": "categories", "error": str(e)})
            continue

        results["success"].append(region)

    # ── Summary & Alerting ───────────────────────────────────────────────
    summary = (
        f"Ingestion {ingestion_id} complete. "
        f"Success: {len(results['success'])}/{len(REGIONS)} regions. "
        f"Failed: {len(results['failed'])}."
    )
    logger.info(summary)

    if results["failed"]:
        send_alert(
            subject=f"[YT Pipeline] Ingestion partial failure — {ingestion_id}",
            message=json.dumps(results, indent=2),
        )

    print("Data inserted into Bronze")

# =========================
# TRIGGER GLUE (SEQUENTIAL)
# =========================


    if results["success"]:
        print("Starting Silver Glue Job...")

    # 1. Start Silver Job
    try:
        silver_job = glue_client.start_job_run(
            JobName="bronze_to_silver"
        )
        silver_job_id = silver_job["JobRunId"]
        print(f"Silver Job Started: {silver_job_id}")
    except Exception as e:
        logger.error(f"Failed to start Silver job: {e}")
        raise e

    # 2. Wait for Silver Job to Complete
    while True:
        response = glue_client.get_job_run(
            JobName="bronze_to_silver",
            RunId=silver_job_id
        )

        status = response["JobRun"]["JobRunState"]
        print(f"Silver Job Status: {status}")

        if status in ["SUCCEEDED", "FAILED", "STOPPED", "TIMEOUT"]:
            break

        time.sleep(20)

    # 3. Check Status
    if status != "SUCCEEDED":
        raise Exception(f"Silver job failed with status: {status}")

    print("Silver Job Completed Successfully")

    # 4. Start Gold Job
    try:
        gold_job = glue_client.start_job_run(
            JobName="Silver_to_gold"
        )
        print(f"Gold Job Started: {gold_job['JobRunId']}")
    except Exception as e:
        logger.error(f"Failed to start Gold job: {e}")
        raise e