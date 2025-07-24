import asyncio
import os
import base64
from datetime import datetime
from typing import Optional, List, Dict, Any
import threading
from uuid import uuid4
import psycopg2
import pymysql
import pyodbc
import cx_Oracle
from models import DatabaseConfig, DBType, FTPConfig, JobStatus, JobSummary
from ftplib import FTP, FTP_TLS
import tempfile
import shutil

class FileDownloadProgressTracker:
    def __init__(self):
        self.jobs: Dict[str, JobStatus] = {}
        self._lock = threading.Lock()
    
    def create_job(self) -> str:
        job_id = str(uuid4())
        with self._lock:
            self.jobs[job_id] = JobStatus(
                job_id=job_id,
                status="pending",
                progress=0.0,
                message="Job created",
                start_time=datetime.now()
            )
        return job_id
    
    def update_job(self, job_id: str, **kwargs):
        with self._lock:
            if job_id in self.jobs:
                for key, value in kwargs.items():
                    if hasattr(self.jobs[job_id], key):
                        setattr(self.jobs[job_id], key, value)
    
    def get_job(self, job_id: str) -> Optional[JobStatus]:
        with self._lock:
            return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[JobStatus]:
        with self._lock:
            return list(self.jobs.values())

file_download_tracker = FileDownloadProgressTracker()

def get_database_connection(db_config: DatabaseConfig):
    """Create a database connection based on the database type."""
    if db_config.db_type == DBType.POSTGRES:
        return psycopg2.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.user,
            password=db_config.password
        )
    elif db_config.db_type == DBType.MYSQL:
        return pymysql.connect(
            host=db_config.host,
            port=int(db_config.port),
            database=db_config.database,
            user=db_config.user,
            password=db_config.password
        )
    elif db_config.db_type == DBType.MSSQL:
        # Handle named instances
        host_parts = db_config.host.split('\\')
        if len(host_parts) > 1:
            server = host_parts[0]
            instance = host_parts[1]
            connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server}\\{instance};DATABASE={db_config.database};UID={db_config.user};PWD={db_config.password}"
        else:
            connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_config.host}:{db_config.port};DATABASE={db_config.database};UID={db_config.user};PWD={db_config.password}"
        return pyodbc.connect(connection_string)
    elif db_config.db_type == DBType.ORACLE:
        if db_config.database.startswith("/"):  # Service name
            dsn = f"{db_config.host}:{db_config.port}{db_config.database}"
        else:  # SID
            dsn = f"{db_config.host}:{db_config.port}:{db_config.database}"
        return cx_Oracle.connect(db_config.user, db_config.password, dsn)
    else:
        raise ValueError(f"Unsupported database type: {db_config.db_type}")

async def upload_file_to_ftp(local_file_path: str, ftp_config: FTPConfig, remote_filename: str):
    """Upload a single file to FTP server."""
    try:
        if ftp_config.use_tls:
            ftp = FTP_TLS()
        else:
            ftp = FTP()
        
        ftp.connect(ftp_config.host, ftp_config.port, timeout=30)
        ftp.login(ftp_config.user, ftp_config.password.get_secret_value())
        
        if ftp_config.use_tls:
            ftp.prot_p()
        
        if ftp_config.passive_mode:
            ftp.set_pasv(True)
        
        # Change to the specified directory
        if ftp_config.directory != "/":
            try:
                ftp.cwd(ftp_config.directory)
            except Exception as e:
                print(f"Warning: Could not change to directory {ftp_config.directory}: {e}")
        
        # Upload the file
        with open(local_file_path, 'rb') as file:
            ftp.storbinary(f'STOR {remote_filename}', file)
        
        ftp.quit()
        return True
    except Exception as e:
        print(f"FTP upload failed: {e}")
        raise Exception(f"FTP upload failed: {str(e)}")

async def download_files_async(
    table_name: str,
    name_column: str,
    file_column: str,
    extension_column: str,
    db_config: DatabaseConfig,
    output_destination: str = "local",
    ftp_config: Optional[FTPConfig] = None
):
    """Download files from database and optionally upload to FTP."""
    job_id = file_download_tracker.create_job()
    temp_dir = None
    
    file_download_tracker.update_job(
        job_id, 
        db_config=db_config, 
        message="Starting file download process"
    )
    
    try:
        async def download():
            nonlocal temp_dir
            connection = None
            try:
                # Create database connection
                file_download_tracker.update_job(job_id, status="running", message="Connecting to database...")
                connection = get_database_connection(db_config)
                cursor = connection.cursor()
                
                # Get total count for progress tracking
                count_query = f"SELECT COUNT(*) FROM {table_name}"
                cursor.execute(count_query)
                total_files = cursor.fetchone()[0]
                
                if total_files == 0:
                    file_download_tracker.update_job(
                        job_id, 
                        status="completed", 
                        progress=100.0, 
                        message="No files found in table",
                        end_time=datetime.now()
                    )
                    return
                
                file_download_tracker.update_job(
                    job_id, 
                    total_rows=total_files,
                    message=f"Found {total_files} files to download"
                )
                
                # Create output directory
                if output_destination == "ftp":
                    temp_dir = tempfile.mkdtemp()
                    output_dir = temp_dir
                else:
                    output_dir = "downloads"
                    os.makedirs(output_dir, exist_ok=True)
                
                # Query to get all files
                select_query = f"SELECT {name_column}, {file_column}, {extension_column} FROM {table_name}"
                cursor.execute(select_query)
                
                downloaded_count = 0
                uploaded_count = 0
                
                for row in cursor.fetchall():
                    filename, file_data, extension = row
                    
                    # Ensure filename has proper extension
                    if not filename.endswith(f'.{extension}'):
                        filename = f"{filename}.{extension}"
                    
                    # Create local file path
                    local_file_path = os.path.join(output_dir, filename)
                    
                    # Write file data
                    if file_data:
                        if isinstance(file_data, str):
                            # Handle base64 encoded data
                            try:
                                decoded_data = base64.b64decode(file_data)
                                with open(local_file_path, 'wb') as f:
                                    f.write(decoded_data)
                            except Exception as e:
                                print(f"Error decoding base64 data for {filename}: {e}")
                                continue
                        else:
                            # Handle binary data
                            with open(local_file_path, 'wb') as f:
                                f.write(file_data)
                        
                        downloaded_count += 1
                        
                        # Upload to FTP if requested
                        if output_destination == "ftp" and ftp_config:
                            try:
                                await upload_file_to_ftp(local_file_path, ftp_config, filename)
                                uploaded_count += 1
                                # Remove local file after successful upload
                                os.remove(local_file_path)
                            except Exception as e:
                                print(f"Failed to upload {filename}: {e}")
                        
                        # Update progress
                        progress = (downloaded_count / total_files) * 100
                        file_download_tracker.update_job(
                            job_id,
                            progress=progress,
                            processed_rows=downloaded_count,
                            message=f"Downloaded {downloaded_count}/{total_files} files"
                        )
                
                # Clean up
                if connection:
                    cursor.close()
                    connection.close()
                
                # Clean up temp directory if FTP was used
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                
                # Update completion status
                end_time = datetime.now()
                completion_message = f"Downloaded {downloaded_count} files"
                if output_destination == "ftp":
                    completion_message += f", uploaded {uploaded_count} to FTP"
                
                file_download_tracker.update_job(
                    job_id,
                    status="completed",
                    progress=100.0,
                    end_time=end_time,
                    message=completion_message,
                    processed_rows=downloaded_count
                )
                
            except Exception as e:
                # Clean up on error
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                if connection:
                    connection.close()
                
                file_download_tracker.update_job(
                    job_id,
                    status="failed",
                    end_time=datetime.now(),
                    message=f"Error: {str(e)}",
                    errors=[str(e)]
                )
                raise
        
        # Run the download process asynchronously
        asyncio.create_task(download())
        return job_id
        
    except Exception as e:
        file_download_tracker.update_job(
            job_id,
            status="failed",
            end_time=datetime.now(),
            message=f"Error: {str(e)}",
            errors=[str(e)]
        )
        raise

def get_file_download_job_summary(job_id: str) -> Optional[JobSummary]:
    """Get a summary of a file download job."""
    job = file_download_tracker.get_job(job_id)
    if not job:
        return None
    
    elapsed_time = None
    if job.start_time and job.end_time:
        elapsed_time = (job.end_time - job.start_time).total_seconds()
    
    return JobSummary(
        job_id=job.job_id,
        start_time=job.start_time,
        end_time=job.end_time,
        elapsed_time=elapsed_time,
        status=job.status,
        total_records=job.total_rows or 0,
        output_file=None,  # Files are downloaded individually
        format="files",
        errors=job.errors
    ) 