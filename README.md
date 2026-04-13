# 🚀 YouTube Trending Data Pipeline on AWS

An end-to-end **serverless data engineering pipeline** built on AWS that ingests YouTube trending data, processes it through a medallion architecture (Bronze → Silver → Gold), and enables analytics using Athena.

---

## 📌 Project Overview

This project demonstrates how to build a **scalable, automated data pipeline** using AWS services:

* Extracts trending video data from YouTube API
* Stores raw data in S3 (Bronze layer)
* Transforms data using AWS Glue (Silver & Gold layers)
* Queries processed data using Amazon Athena
* Automates execution using EventBridge
* Sends alerts using SNS

---

## 🏗️ Architecture


![Project_Architecture](https://github.com/user-attachments/assets/162c9ed6-0eb2-43b5-aa14-18f03e1c47a0)


---

## ⚙️ Tech Stack

* **AWS Lambda** – Serverless ingestion
* **Amazon S3** – Data lake storage
* **AWS Glue** – ETL processing
* **Amazon Athena** – Query service
* **Amazon EventBridge** – Scheduling
* **Amazon SNS** – Alerts & notifications
* **YouTube Data API v3** – Data source

---

## 📂 Data Lake Structure

```
s3://your-bucket/

├── raw_data/                # Bronze Layer
│   └── region=IN/date=YYYY-MM-DD/hour=HH/data.json
│
├── silver/                  # Silver Layer (cleaned)
│   └── region=IN/date=YYYY-MM-DD/
│
└── gold/                    # Gold Layer (aggregated)
    └── analytics tables
```

---

## 🔄 Pipeline Workflow

1. **EventBridge Trigger**

   * Runs on a defined schedule (cron/rate)

2. **Lambda Execution**

   * Calls YouTube API
   * Fetches trending videos
   * Stores raw JSON in S3 (Bronze)
   * Triggers Glue jobs

3. **Glue Processing**

   * **Bronze → Silver**

     * Data cleaning
     * Schema standardization
   * **Silver → Gold**

     * Aggregations
     * Analytics-ready tables

4. **Athena Querying**

   * SQL queries on curated data

5. **SNS Alerts**

   * Notifies on failures

---

## 🧠 Key Features

* ✅ Fully serverless architecture
* ✅ Automated scheduling using EventBridge
* ✅ Medallion architecture (Bronze, Silver, Gold)
* ✅ Partitioned data for efficient querying
* ✅ Scalable and cost-efficient
* ✅ Fault monitoring with CloudWatch & SNS

---

## 📊 Sample Athena Query

```sql
SELECT title, views, region
FROM gold_table
ORDER BY views DESC
LIMIT 10;
```

---

## 🚀 Setup Instructions

### 1. Configure YouTube API

* Generate API key from Google Cloud Console
* Add it in Lambda environment variables

---

### 2. Create S3 Buckets

* `aws-data-pipeline-bronze-harsh/raw_data`
* `aws-data-pipeline-silver-harsh/silver`
* `aws-data-pipeline-gold-harsh/gold`

---

### 3. Deploy Lambda

* Add ingestion script
* Set IAM role with:

  * S3 access
  * Glue access
  * SNS publish

---

### 4. Create Glue Jobs

* `bronze_to_silver`
* `silver_to_gold`

---

### 5. Setup EventBridge

* Create scheduled rule
* Attach Lambda as target

---

### 6. Setup Athena

* Create external tables
* Query Gold data

---

## 🔍 Monitoring

* **CloudWatch Logs** – Lambda execution logs
* **Glue Job Runs** – ETL status
* **EventBridge Metrics** – Trigger status
* **SNS Notifications** – Failure alerts
