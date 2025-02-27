from pyspark.sql import SparkSession

def create_spark_session():
    """Create and return a Spark session with database connectivity"""
    return SparkSession.builder \
        .appName("DataExtractor") \
        .config("spark.driver.allowMultipleContexts", "true") \
        .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow") \
        .config("spark.jars.packages", 
                "org.postgresql:postgresql:42.2.18," + 
                "mysql:mysql-connector-java:8.0.28") \
        .master("local[*]") \
        .getOrCreate()

def extract_data(spark, db_params, query, output_path):
    """Extract data from database and save to CSV"""
    try:
        df = spark.read \
            .format("jdbc") \
            .option("url", db_params.jdbc_url) \
            .option("driver", db_params.driver) \
            .option("dbtable", f"({query}) as tmp") \
            .option("user", db_params.user) \
            .option("password", db_params.password) \
            .load()
        
        df.write \
            .mode("overwrite") \
            .option("header", "true") \
            .csv(output_path)
        
        return {"status": "success", "message": f"Data extracted to {output_path}", "row_count": df.count()}
    except Exception as e:
        raise Exception(f"Extraction failed: {str(e)}") 