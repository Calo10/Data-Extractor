from pyspark.sql import SparkSession
from models import SparkConfig

def create_spark_session(spark_config: SparkConfig = None):
    """Create and return a Spark session with database connectivity"""
    if spark_config is None:
        spark_config = SparkConfig()

    builder = SparkSession.builder \
        .appName("DataExtractor") \
        .config("spark.driver.allowMultipleContexts", "true") \
        .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow") \
        .config("spark.jars.packages", 
                "org.postgresql:postgresql:42.2.18," + 
                "mysql:mysql-connector-java:8.0.28," +
                "com.databricks:spark-xml_2.12:0.15.0") \
        .config("spark.driver.memory", spark_config.driver_memory) \
        .config("spark.executor.memory", spark_config.executor_memory) \
        .config("spark.executor.cores", spark_config.executor_cores) \
        .config("spark.sql.shuffle.partitions", spark_config.shuffle_partitions) \
        .config("spark.default.parallelism", spark_config.default_parallelism) \
        .config("spark.memory.offHeap.enabled", spark_config.off_heap_enabled) \
        .config("spark.memory.offHeap.size", spark_config.off_heap_size) \
        .master("local[*]")

    return builder.getOrCreate()

def extract_data(spark, db_params, query, output_path, format="csv", spark_config: SparkConfig = None):
    """Extract data from database and save to specified format"""
    if spark_config is None:
        spark_config = SparkConfig()

    try:
        df = spark.read \
            .format("jdbc") \
            .option("url", f"{db_params.jdbc_url}?sslmode=disable") \
            .option("driver", db_params.driver) \
            .option("dbtable", f"({query}) as tmp") \
            .option("user", db_params.user) \
            .option("password", db_params.password) \
            .option("fetchsize", spark_config.fetch_size) \
            .option("numPartitions", spark_config.num_partitions) \
            .load()
        
        if format == "sql":
            # Convert DataFrame to SQL INSERT statements
            rows = df.collect()
            columns = df.columns
            table_name = output_path.split('/')[-1].replace('.sql', '')
            
            with open(output_path, 'w') as f:
                # Write CREATE TABLE statement
                column_types = [f"{col} {df.schema[col].dataType.simpleString()}" 
                              for col in columns]
                create_table = f"CREATE TABLE IF NOT EXISTS {table_name} (\n  "
                create_table += ",\n  ".join(column_types)
                create_table += "\n);\n\n"
                f.write(create_table)
                
                # Write INSERT statements
                for row in rows:
                    values = [f"'{str(val)}'" if val is not None else 'NULL' 
                            for val in row]
                    insert = f"INSERT INTO {table_name} ({', '.join(columns)}) "
                    insert += f"VALUES ({', '.join(values)});\n"
                    f.write(insert)
                
        elif format == "json":
            df.write.mode("overwrite").json(output_path)
        elif format == "xml":
            df.write.mode("overwrite").format("xml") \
                .option("rootTag", "data") \
                .option("rowTag", "record") \
                .save(output_path)
        elif format == "parquet":
            df.write.mode("overwrite").parquet(output_path)
        else:
            df.write.mode("overwrite").option("header", "true").csv(output_path)
        
        return {"status": "success", "message": f"Data extracted to {output_path}", "row_count": df.count()}
    except Exception as e:
        raise Exception(f"Extraction failed: {str(e)}") 