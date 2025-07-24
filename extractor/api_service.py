from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from data_extractor import create_spark_session, extract_data, extract_data_async, progress_tracker
from file_downloader import download_files_async, file_download_tracker, get_file_download_job_summary
from models import ExtractionRequest, FileDownloadRequest, DatabaseConfig, DBType, JobStatus, JobSummary
from pydantic import BaseModel, Field
from datetime import datetime

app = FastAPI(
    title="Data Extraction API",
    description="API for extracting data from databases using Apache Spark",
    version="1.0.0",
    docs_url="/swagger"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class PreviewRequest(BaseModel):
    query: str = Field(..., description="SQL query to execute")
    db_config: DatabaseConfig = Field(..., description="Database connection configuration")

def handle_extraction_error(e: Exception, db_config: DatabaseConfig = None) -> HTTPException:
    """Centralized error handling for extraction endpoints"""
    error_msg = str(e)
    
    if "SQLSyntaxErrorException" in error_msg:
        if "doesn't exist" in error_msg or "not found" in error_msg:
            table_name = error_msg.split("'")[1] if "'" in error_msg else "specified table"
            return HTTPException(
                status_code=404,
                detail={
                    "error": "Table Not Found",
                    "message": f"The table {table_name} does not exist in database {db_config.database}",
                    "details": error_msg,
                    "suggestions": [
                        "Verify the table name in your query",
                        "Check if you have access to the database and table",
                        "Ensure you're connecting to the correct database",
                        f"Current database: {db_config.database}"
                    ]
                }
            )
        return HTTPException(
            status_code=400,
            detail={
                "error": "SQL Syntax Error",
                "message": "The SQL query contains syntax errors",
                "details": error_msg,
                "suggestions": [
                    "Check your SQL query syntax",
                    "Verify table and column names",
                    "Ensure all SQL keywords are properly used"
                ]
            }
        )
    elif "TCP/IP connection" in error_msg or "Connection refused" in error_msg:
        return HTTPException(
            status_code=503,
            detail={
                "error": "Connection Failed",
                "message": f"Could not connect to database server at {db_config.host}:{db_config.port}",
                "details": error_msg,
                "suggestions": [
                    "Verify the host and port are correct",
                    "Check if the database server is running",
                    "Ensure network connectivity to the database"
                ]
            }
        )
    elif "Access denied" in error_msg or "password authentication failed" in error_msg:
        return HTTPException(
            status_code=401,
            detail={
                "error": "Authentication Failed",
                "message": f"Database authentication failed for user '{db_config.user}'",
                "details": error_msg,
                "suggestions": [
                    "Verify username and password",
                    "Check if the user has necessary permissions"
                ]
            }
        )
    elif "OutOfMemoryError" in error_msg:
        return HTTPException(
            status_code=503,
            detail={
                "error": "Resource Exhausted",
                "message": "The operation exceeded available memory",
                "details": error_msg,
                "suggestions": [
                    "Reduce the data size in your query",
                    "Increase Spark memory settings",
                    "Use pagination or filtering in your query"
                ]
            }
        )
    else:
        return HTTPException(
            status_code=500,
            detail={
                "error": "Extraction Failed",
                "message": "An unexpected error occurred during data extraction",
                "details": error_msg,
                "timestamp": datetime.now().isoformat()
            }
        )

@app.post("/extract_csv", 
    response_description="Extraction result with status and row count",
    summary="Extract data from database to CSV",
    description="Executes a SQL query against the specified database and saves the results to a CSV file")
async def extract_to_csv(request: ExtractionRequest):
    """
    Extract data from database and save to CSV file
    
    - **query**: SQL query to execute
    - **output_filename**: Name of the output CSV file
    - **db_config**: Database connection configuration
    """
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, request.output_filename)
    
    spark = create_spark_session(request.spark_config)
    try:
        # Start async extraction
        job_id = await extract_data_async(
            spark, 
            request.db_config, 
            request.query, 
            output_path, 
            format="csv",
            spark_config=request.spark_config,
            output_destination=request.output_destination,
            ftp_config=request.ftp_config
        )
        return {"job_id": job_id, "status": "started"}
    except Exception as e:
        spark.stop()
        raise handle_extraction_error(e, request.db_config)

@app.post("/extract_json")
async def extract_to_json(request: ExtractionRequest):
    """Extract data from database and save as JSON"""
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    output_filename = request.output_filename
    if not output_filename.endswith('.json'):
        output_filename = f"{output_filename}.json"
    
    output_path = os.path.join(output_dir, output_filename)
    
    spark = create_spark_session(request.spark_config)
    try:
        job_id = await extract_data_async(
            spark, 
            request.db_config, 
            request.query, 
            output_path, 
            format="json",
            spark_config=request.spark_config
        )
        return {"job_id": job_id, "status": "started"}
    except Exception as e:
        spark.stop()
        raise handle_extraction_error(e, request.db_config)

@app.post("/extract_xml")
async def extract_to_xml(request: ExtractionRequest):
    """Extract data from database and save to XML file"""
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    output_filename = request.output_filename
    if not output_filename.endswith('.xml'):
        output_filename = f"{output_filename}.xml"
    
    output_path = os.path.join(output_dir, output_filename)
    
    spark = create_spark_session(request.spark_config)
    try:
        job_id = extract_data_async(
            spark, 
            request.db_config, 
            request.query, 
            output_path, 
            format="xml",
            spark_config=request.spark_config
        )
        return {"job_id": job_id, "status": "started"}
    except Exception as e:
        spark.stop()
        raise handle_extraction_error(e, request.db_config)

@app.post("/extract_parquet")
async def extract_to_parquet(request: ExtractionRequest):
    """Extract data from database and save to Parquet file"""
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    output_filename = request.output_filename
    if not output_filename.endswith('.parquet'):
        output_filename = f"{output_filename}.parquet"
    
    output_path = os.path.join(output_dir, output_filename)
    
    spark = create_spark_session(request.spark_config)
    try:
        job_id = extract_data_async(
            spark, 
            request.db_config, 
            request.query, 
            output_path, 
            format="parquet",
            spark_config=request.spark_config
        )
        return {"job_id": job_id, "status": "started"}
    except Exception as e:
        spark.stop()
        raise handle_extraction_error(e, request.db_config)

@app.post("/extract_sql")
async def extract_to_sql(request: ExtractionRequest):
    """Extract data from database and save as SQL dump file"""
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    output_filename = request.output_filename
    if not output_filename.endswith('.sql'):
        output_filename = f"{output_filename}.sql"
    
    output_path = os.path.join(output_dir, output_filename)
    
    spark = create_spark_session(request.spark_config)
    try:
        job_id = extract_data_async(
            spark, 
            request.db_config, 
            request.query, 
            output_path, 
            format="sql",
            spark_config=request.spark_config
        )
        return {"job_id": job_id, "status": "started"}
    except Exception as e:
        spark.stop()
        raise handle_extraction_error(e, request.db_config)

@app.post("/preview")
async def preview_data(request: PreviewRequest):
    """Preview first 100 rows of query result"""
    try:
        query = request.query.strip().rstrip(';')
        if 'LIMIT' not in query.upper():
            query = f"{query} LIMIT 100"
        
        spark = create_spark_session()
        try:
            connection_props = {
                "url": request.db_config.jdbc_url,
                "driver": request.db_config.driver,
                "dbtable": f"({query}) as tmp",
                "user": request.db_config.user,
                "password": request.db_config.password
            }
            
            # Add SQL Server specific options
            if request.db_config.db_type == DBType.MSSQL:
                connection_props["encrypt"] = "false"
                connection_props["trustServerCertificate"] = "true"
            elif request.db_config.db_type == DBType.POSTGRES:
                connection_props["url"] = f"{connection_props['url']}?sslmode=disable"

            df = spark.read.format("jdbc").options(**connection_props).load()
            
            return {
                "status": "success",
                "columns": df.columns,
                "data": [row.asDict() for row in df.collect()],
                "row_count": df.count()
            }
        finally:
            spark.stop()
    except Exception as e:
        raise handle_extraction_error(e, request.db_config)

@app.post("/download_files", 
    response_description="File download result with job ID",
    summary="Download files from database",
    description="Downloads files stored in database BLOB/BINARY columns and saves them locally or uploads to FTP")
async def download_files(request: FileDownloadRequest):
    try:
        job_id = await download_files_async(
            table_name=request.table_name,
            name_column=request.name_column,
            file_column=request.file_column,
            extension_column=request.extension_column,
            db_config=request.db_config,
            output_destination=request.output_destination,
            ftp_config=request.ftp_config
        )
        return {"job_id": job_id, "status": "started"}
    except Exception as e:
        raise handle_extraction_error(e, request.db_config)

@app.get("/file_download_status/{job_id}")
async def get_file_download_status(job_id: str):
    status = file_download_tracker.get_job(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    if status.status == "failed":
        error_msg = status.errors[0] if status.errors else "Unknown error"
        raise handle_extraction_error(Exception(error_msg), status.db_config)
    return status

@app.get("/file_download_summary/{job_id}")
async def get_file_download_summary(job_id: str):
    summary = get_file_download_job_summary(job_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Job not found")
    return summary

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of an extraction job"""
    status = progress_tracker.get_job(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # If job failed, return error details
    if status.status == "failed":
        error_msg = status.errors[0] if status.errors else "Unknown error"
        raise handle_extraction_error(Exception(error_msg), status.db_config)
        
    return status

@app.get("/summary", response_model=list[JobSummary])
async def get_jobs_summary():
    """Get summary of all extraction jobs"""
    jobs = progress_tracker.get_all_jobs()
    summaries = []
    
    for job in jobs:
        elapsed = None
        if job.start_time and job.end_time:
            elapsed = (job.end_time - job.start_time).total_seconds()
        
        summaries.append(JobSummary(
            job_id=job.job_id,
            start_time=job.start_time,
            end_time=job.end_time,
            elapsed_time=elapsed,
            status=job.status,
            total_records=job.total_rows or 0,
            output_file=job.output_file,
            format=job.format,
            errors=job.errors
        ))
    
    return summaries

@app.get("/summary/{job_id}")
async def get_job_summary(job_id: str):
    """Get detailed summary of a specific extraction job"""
    job = progress_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    elapsed = None
    if job.start_time and job.end_time:
        elapsed = (job.end_time - job.start_time).total_seconds()
    
    return JobSummary(
        job_id=job.job_id,
        start_time=job.start_time,
        end_time=job.end_time,
        elapsed_time=elapsed,
        status=job.status,
        total_records=job.total_rows or 0,
        output_file=job.output_file,
        format=job.format,
        errors=job.errors
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)