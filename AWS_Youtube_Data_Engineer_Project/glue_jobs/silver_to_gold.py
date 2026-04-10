import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from pyspark.sql.functions import sum as _sum, count

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# ✅ Read Parquet directly (NO Visual confusion)
df = spark.read.parquet("s3://aws-data-pipeline-silver-harsh/transformed_data/")

# Debug (optional)
print("Schema:")
df.printSchema()

# ✅ Aggregation
df_agg = df.groupBy("channel_title").agg(
    _sum("views").alias("total_views"),
    _sum("likes").alias("total_likes"),
    _sum("comments").alias("total_comments"),
    count("video_id").alias("total_videos")
)

# ✅ Write output
df_agg.write.mode("overwrite").parquet("s3://aws-data-pipeline-gold-harsh/aggregated/")