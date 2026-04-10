import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from pyspark.sql.functions import explode, col, to_timestamp, input_file_name, regexp_extract

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# ✅ Read JSON WITHOUT partition confusion
df = spark.read.option("recursiveFileLookup", "true") \
                .option("multiLine", "true") \
               .json("s3://aws-data-pipeline-bronze-harsh/raw_data/")

# ✅ Extract region from file path (important)
df = df.withColumn("file_path", input_file_name())

df = df.withColumn("region", regexp_extract("file_path", "region=([^/]+)", 1)) \
       .withColumn("date", regexp_extract("file_path", "date=([^/]+)", 1))

# ✅ Explode items
df_exploded = df.select(
    explode(col("items")).alias("item"),
    col("region"),
    col("date")
)

# ✅ Flatten JSON
df_clean = df_exploded.select(
    col("item.id").alias("video_id"),
    col("item.snippet.title").alias("title"),
    col("item.snippet.channelTitle").alias("channel_title"),
    col("item.snippet.publishedAt").alias("published_at"),
    col("item.snippet.categoryId").alias("category_id"),
    col("item.statistics.viewCount").cast("long").alias("views"),
    col("item.statistics.likeCount").cast("long").alias("likes"),
    col("item.statistics.commentCount").cast("long").alias("comments"),
    col("region"),
    col("date")
)

# Convert timestamp
df_clean = df_clean.withColumn("published_at", to_timestamp("published_at"))

# ✅ Write clean parquet
df_clean.write.mode("overwrite").parquet("s3://aws-data-pipeline-silver-harsh/transformed_data/")