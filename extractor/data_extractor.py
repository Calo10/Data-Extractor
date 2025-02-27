from pyspark.sql import SparkSession

def create_spark_session():
    """Create and return a Spark session with database connectivity"""
    return SparkSession.builder \
        .appName("DataExtractor") \
        .config("spark.driver.allowMultipleContexts", "true") \
        .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow") \
        .config("spark.jars.packages", 
                "org.postgresql:postgresql:42.2.18," + 
                "mysql:mysql-connector-java:8.0.28," +
                "com.databricks:spark-xml_2.12:0.15.0") \
        .master("local[*]") \
        .getOrCreate()

def extract_data(spark, db_params, query, output_path, format="csv"):
    """Extract data from database and save to specified format"""
    try:
        df = spark.read \
            .format("jdbc") \
            .option("url", db_params.jdbc_url) \
            .option("driver", db_params.driver) \
            .option("dbtable", f"({query}) as tmp") \
            .option("user", db_params.user) \
            .option("password", db_params.password) \
            .load()
        
        if format == "json":
            df.write \
                .mode("overwrite") \
                .json(output_path)
        elif format == "xml":
            df.write \
                .mode("overwrite") \
                .format("xml") \
                .option("rootTag", "data") \
                .option("rowTag", "record") \
                .save(output_path)
        else:
            df.write \
                .mode("overwrite") \
                .option("header", "true") \
                .csv(output_path)
        
        return {"status": "success", "message": f"Data extracted to {output_path}", "row_count": df.count()}
    except Exception as e:
        raise Exception(f"Extraction failed: {str(e)}") 