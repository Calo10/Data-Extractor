from pydantic import BaseModel, Field
from enum import Enum

class DBType(str, Enum):
    POSTGRES = "postgresql"
    MYSQL = "mysql"

class DatabaseConfig(BaseModel):
    db_type: DBType = Field(..., description="Database type (postgresql or mysql)")
    host: str = Field(..., description="Database host", example="localhost")
    port: str = Field(..., description="Database port", example="3306")
    database: str = Field(..., description="Database name")
    user: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")

    @property
    def driver(self) -> str:
        return {
            DBType.POSTGRES: "org.postgresql.Driver",
            DBType.MYSQL: "com.mysql.cj.jdbc.Driver"
        }[self.db_type]
    
    @property
    def jdbc_url(self) -> str:
        return f"jdbc:{self.db_type}://{self.host}:{self.port}/{self.database}"

class ExtractionRequest(BaseModel):
    query: str = Field(..., description="SQL query to execute", example="SELECT * FROM employees")
    output_filename: str = Field(..., description="Name of the output CSV file", example="employees.csv")
    db_config: DatabaseConfig = Field(..., description="Database connection configuration") 