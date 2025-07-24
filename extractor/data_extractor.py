from pyspark.sql import SparkSession
from models import SparkConfig, JobStatus
from uuid import uuid4
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from datetime import datetime
import asyncio
from ftplib import FTP, FTP_TLS
import os
from io import BytesIO
import json

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
                "com.microsoft.sqlserver:mssql-jdbc:9.4.1.jre8," +
                "com.databricks:spark-xml_2.12:0.15.0," +
                "com.oracle.database.jdbc:ojdbc8:21.5.0.0") \
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
        # Add Oracle-specific connection options
        jdbc_options = {
            "url": db_params.jdbc_url,
            "driver": db_params.driver,
            "dbtable": f"({query}) as tmp",
            "user": db_params.user,
            "password": db_params.password,
            "fetchsize": spark_config.fetch_size if spark_config else 10000,
        }
        
        # Add Oracle-specific options
        if "oracle" in db_params.driver.lower():
            jdbc_options.update({
                "oracle.jdbc.timezoneAsRegion": "false",
                "oracle.jdbc.defaultNChar": "true",
                "oracle.jdbc.mapDateToTimestamp": "false"
            })

        df = spark.read \
            .format("jdbc") \
            .options(**jdbc_options) \
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

class ProgressTracker:
    def __init__(self):
        self._jobs = {}
    
    def create_job(self) -> str:
        job_id = str(uuid4())
        self._jobs[job_id] = JobStatus(job_id=job_id)
        return job_id
    
    def update_job(self, job_id: str, **kwargs):
        if job_id in self._jobs:
            for key, value in kwargs.items():
                setattr(self._jobs[job_id], key, value)
    
    def get_job(self, job_id: str) -> Optional[JobStatus]:
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[JobStatus]:
        return list(self._jobs.values())

progress_tracker = ProgressTracker()

async def upload_to_ftp(local_path, ftp_config, original_filename=None):
    """Upload file to FTP server"""
    ftp = None
    temp_file = None
    try:
        print(f"Starting FTP upload process for: {local_path}")
        print(f"Path exists: {os.path.exists(local_path)}")
        print(f"Is directory: {os.path.isdir(local_path)}")
        
        # For CSV or JSON files, Spark creates a directory
        if os.path.isdir(local_path):
            print(f"Directory contents: {os.listdir(local_path)}")
            
            # Check if this is a JSON directory by looking for JSON files
            json_files = [f for f in os.listdir(local_path) if f.endswith('.json')]
            if json_files:
                print("Found JSON files:", json_files)
                # Use the first JSON file
                json_file = json_files[0]
                local_path = os.path.join(local_path, json_file)
                print(f"Using JSON file: {local_path}")
                print(f"JSON file exists: {os.path.exists(local_path)}")
                print(f"JSON file size: {os.path.getsize(local_path)} bytes")
                # Keep original filename for upload
                filename = original_filename
            else:
                # Handle CSV files
                print("Handling as CSV...")
                csv_files = sorted([f for f in os.listdir(local_path) if f.endswith('.csv')])
                if not csv_files:
                    raise Exception(f"No CSV/JSON files found in directory {local_path}")
                
                temp_file = os.path.join(os.path.dirname(local_path), "combined.csv")
                first_file = os.path.join(local_path, csv_files[0])
                
                with open(first_file, 'r') as f:
                    header = f.readline()
                
                with open(temp_file, 'w') as outfile:
                    outfile.write(header)
                    for csv_file in csv_files:
                        file_path = os.path.join(local_path, csv_file)
                        with open(file_path, 'r') as infile:
                            if file_path != first_file:
                                next(infile)
                            for line in infile:
                                outfile.write(line)
                
                local_path = temp_file

        filename = original_filename or os.path.basename(local_path)
        print(f"Will upload as: {filename}")
        print(f"Final path check - exists: {os.path.exists(local_path)}, size: {os.path.getsize(local_path)}")
        
        # Create basic FTP connection (no TLS)
        ftp = FTP()
        print("Using FTP connection")
        
        # Increase timeout and set to binary mode
        ftp.timeout = 60
        ftp.set_debuglevel(2)
        
        # Connect with exact same parameters as FileZilla
        print(f"Connecting to {ftp_config.host}:{ftp_config.port}")
        ftp.connect(
            host=ftp_config.host, 
            port=ftp_config.port,
            timeout=60
        )
        
        # Login with exact same credentials
        print(f"Logging in as anonymous")
        ftp.login(
            user="anonymous", 
            passwd="CMcalo10$"
        )
        print("Login successful")
        
        print(f"Server welcome: {ftp.welcome}")
        print(f"Current directory: {ftp.pwd()}")
        
        # Always use passive mode (like FileZilla)
        print("Setting passive mode")
        ftp.set_pasv(True)
        
        # Upload file
        print(f"Starting file upload of {filename}")
        with open(local_path, 'rb') as file:
            ftp.storbinary(f'STOR {filename}', file)
        print("File upload completed")
            
        ftp.quit()
        return True
        
    except Exception as e:
        print(f"FTP Error: {str(e)}")
        if ftp:
            try:
                ftp.quit()
            except:
                pass
        raise Exception(f"FTP upload failed: {str(e)}")
    finally:
        # Clean up temporary combined file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"Warning: Failed to delete temporary file {temp_file}: {str(e)}")

async def extract_data_async(
    spark, 
    db_config, 
    query, 
    output_path, 
    format="csv",
    spark_config=None,
    output_destination="local",
    ftp_config=None
):
    """Asynchronous data extraction with progress tracking"""
    job_id = progress_tracker.create_job()
    local_path = None
    temp_dir = None
    
    try:
        async def extract():
            nonlocal local_path, temp_dir
            try:
                # Get total count for progress calculation
                count_query = f"SELECT COUNT(*) as total FROM ({query}) as t"
                total_rows = get_total_rows(spark, db_config, count_query)
                
                progress_tracker.update_job(
                    job_id,
                    status="running",
                    total_rows=total_rows
                )
                
                # Process in batches
                df = spark.read \
                    .format("jdbc") \
                    .option("url", db_config.jdbc_url) \
                    .option("driver", db_config.driver) \
                    .option("dbtable", f"({query}) as tmp") \
                    .option("user", db_config.user) \
                    .option("password", db_config.password) \
                    .load()

                # For FTP, always use temp directory
                if output_destination == "ftp":
                    temp_dir = os.path.join(os.getcwd(), "temp")
                    os.makedirs(temp_dir, exist_ok=True)
                    local_path = os.path.join(temp_dir, os.path.basename(output_path))
                else:
                    # For local files, use exports directory
                    exports_dir = "exports"
                    os.makedirs(exports_dir, exist_ok=True)
                    local_path = os.path.join(exports_dir, os.path.basename(output_path))

                # Write the data
                if format == "json":
                    print(f"Writing JSON to {local_path}")
                    if output_destination == "ftp":
                        print(f"Using temp directory for FTP: {temp_dir}")
                        # Write to temp directory first
                        df.coalesce(1).write \
                            .mode("overwrite") \
                            .option("multiline", "true") \
                            .json(local_path)  # Use local_path which is already in temp dir
                        
                        print(f"JSON written to temp directory: {local_path}")
                        print(f"Directory contents: {os.listdir(local_path)}")
                        
                        # Find the JSON file in the directory
                        json_files = [f for f in os.listdir(local_path) if f.endswith('.json')]
                        if not json_files:
                            raise Exception("No JSON file was created")
                        
                        # Update local_path to point to the actual JSON file
                        local_path = os.path.join(local_path, json_files[0])
                        print(f"Final JSON path: {local_path}")
                        print(f"File exists: {os.path.exists(local_path)}")
                        print(f"File size: {os.path.getsize(local_path)} bytes")
                    else:
                        # Local file writing
                        df.coalesce(1).write \
                            .mode("overwrite") \
                            .option("multiline", "true") \
                            .json(local_path)
                        
                        # Find the JSON file in the directory
                        json_files = [f for f in os.listdir(local_path) if f.endswith('.json')]
                        if not json_files:
                            raise Exception("No JSON file was created")
                        
                        # Create final file path
                        json_file = os.path.join(local_path, json_files[0])
                        print(f"JSON file created: {json_file}")
                        print(f"File size: {os.path.getsize(json_file)} bytes")
                
                elif format == "csv":
                    df.coalesce(1).write.mode("overwrite").option("header", "true").csv(local_path)
                elif format == "xml":
                    df.coalesce(1).write.mode("overwrite").format("xml") \
                        .option("rootTag", "data") \
                        .option("rowTag", "record") \
                        .save(local_path)
                elif format == "parquet":
                    df.coalesce(1).write.mode("overwrite").parquet(local_path)

                # Handle FTP upload if requested
                if output_destination == "ftp" and ftp_config:
                    progress_tracker.update_job(
                        job_id,
                        status="uploading",
                        message=f"Uploading to FTP server {ftp_config.host}..."
                    )
                    
                    try:
                        print(f"Starting FTP upload for {format} file")
                        print(f"Local path: {local_path}")
                        print(f"File exists: {os.path.exists(local_path)}")
                        print(f"File size: {os.path.getsize(local_path)} bytes")
                        
                        await upload_to_ftp(local_path, ftp_config, os.path.basename(output_path))
                        print("FTP upload completed successfully")
                    except Exception as e:
                        print(f"FTP upload failed: {str(e)}")
                        raise Exception(f"FTP upload failed: {str(e)}")
                    finally:
                        if temp_dir and os.path.exists(temp_dir) and format != "json":
                            try:
                                import shutil
                                print(f"Cleaning up temp directory: {temp_dir}")
                                shutil.rmtree(temp_dir)
                            except Exception as e:
                                print(f"Warning: Failed to delete temp directory {temp_dir}: {str(e)}")

                # Update completion status
                end_time = datetime.now()
                progress_tracker.update_job(
                    job_id,
                    status="completed",
                    progress=100.0,
                    end_time=end_time,
                    message="Extraction and upload completed successfully",
                    processed_rows=total_rows
                )

            except Exception as e:
                print(f"Error in extract: {str(e)}")
                end_time = datetime.now()
                progress_tracker.update_job(
                    job_id,
                    status="failed",
                    message=str(e),
                    end_time=end_time,
                    errors=[str(e)]
                )
                raise

        # Start the extraction process
        asyncio.create_task(extract())
        return job_id
        
    except Exception as e:
        raise

def get_total_rows(spark, db_config, count_query):
    """Get total number of rows for a query"""
    count_df = spark.read \
        .format("jdbc") \
        .option("url", db_config.jdbc_url) \
        .option("driver", db_config.driver) \
        .option("dbtable", f"({count_query}) as count_tmp") \
        .option("user", db_config.user) \
        .option("password", db_config.password) \
        .load()
    
    return count_df.collect()[0]['total'] 