from pydantic import BaseModel, Field, SecretStr
from enum import Enum
from typing import Optional
from datetime import datetime

class DBType(str, Enum):
    POSTGRES = "postgresql"
    MYSQL = "mysql"
    MSSQL = "sqlserver"

class SparkConfig(BaseModel):
    driver_memory: str = Field(default="10g", description="Spark driver memory")
    executor_memory: str = Field(default="10g", description="Spark executor memory")
    executor_cores: int = Field(default=4, description="Number of cores per executor")
    shuffle_partitions: int = Field(default=100, description="Number of shuffle partitions")
    default_parallelism: int = Field(default=100, description="Default parallelism")
    off_heap_enabled: bool = Field(default=True, description="Enable off-heap memory")
    off_heap_size: str = Field(default="10g", description="Off-heap memory size")
    fetch_size: int = Field(default=10000, description="JDBC fetch size")
    num_partitions: int = Field(default=10, description="Number of partitions for JDBC read")

class DatabaseConfig(BaseModel):
    db_type: DBType = Field(..., description="Database type (postgresql, mysql, or sqlserver)")
    host: str = Field(..., description="Database host", example="localhost")
    port: str = Field(..., description="Database port", example="3306")
    database: str = Field(..., description="Database name")
    user: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")

    @property
    def driver(self) -> str:
        return {
            DBType.POSTGRES: "org.postgresql.Driver",
            DBType.MYSQL: "com.mysql.cj.jdbc.Driver",
            DBType.MSSQL: "com.microsoft.sqlserver.jdbc.SQLServerDriver"
        }[self.db_type]
    
    @property
    def jdbc_url(self) -> str:
        if self.db_type == DBType.MSSQL:
            return f"jdbc:sqlserver://{self.host}:{self.port};databaseName={self.database}"
        return f"jdbc:{self.db_type}://{self.host}:{self.port}/{self.database}"

class OutputDestination(str, Enum):
    LOCAL = "local"
    FTP = "ftp"
    SFTP = "sftp"

class FTPConfig(BaseModel):
    host: str = Field(..., description="FTP server host")
    port: int = Field(default=21, description="FTP server port")
    user: str = Field(..., description="FTP username")
    password: SecretStr = Field(..., description="FTP password")
    directory: str = Field(default="/", description="Remote directory")
    use_tls: bool = Field(default=False, description="Use FTPS (FTP over TLS)")
    passive_mode: bool = Field(default=True, description="Use passive mode")

class ExtractionRequest(BaseModel):
    query: str = Field(..., description="SQL query to execute", example="SELECT * FROM employees")
    output_filename: str = Field(..., description="Name of the output file", example="employees.csv/json/xml/parquet/sql")
    db_config: DatabaseConfig = Field(..., description="Database connection configuration")
    spark_config: Optional[SparkConfig] = Field(default=None, description="Spark configuration parameters")
    output_destination: OutputDestination = Field(default=OutputDestination.LOCAL)
    ftp_config: Optional[FTPConfig] = None

# Add new model for job summary
class JobSummary(BaseModel):
    job_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    elapsed_time: Optional[float] = None  # in seconds
    status: str
    total_records: int = 0
    output_file: Optional[str] = None
    format: Optional[str] = None
    errors: list[str] = []

# Add new model for job status
class JobStatus(BaseModel):
    job_id: str
    status: str = "pending"
    progress: float = 0
    total_rows: Optional[int] = None
    processed_rows: int = 0
    message: str = ""
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    output_file: Optional[str] = None
    format: Optional[str] = None
    errors: list[str] = []
    db_config: Optional[DatabaseConfig] = None 