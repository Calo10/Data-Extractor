from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from data_extractor import create_spark_session, extract_data
from models import ExtractionRequest

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
        result = extract_data(
            spark, 
            request.db_config, 
            request.query, 
            output_path, 
            format="csv",
            spark_config=request.spark_config
        )
        return result
    finally:
        spark.stop()

@app.post("/extract_json")
async def extract_to_json(request: ExtractionRequest):
    """Extract data from database and save to JSON file"""
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure filename ends with .json
    output_filename = request.output_filename
    if not output_filename.endswith('.json'):
        output_filename = f"{output_filename}.json"
    
    output_path = os.path.join(output_dir, output_filename)
    
    spark = create_spark_session()
    try:
        result = extract_data(spark, request.db_config, request.query, output_path, format="json")
        return result
    finally:
        spark.stop()

@app.post("/extract_xml")
async def extract_to_xml(request: ExtractionRequest):
    """Extract data from database and save to XML file"""
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure filename ends with .xml
    output_filename = request.output_filename
    if not output_filename.endswith('.xml'):
        output_filename = f"{output_filename}.xml"
    
    output_path = os.path.join(output_dir, output_filename)
    
    spark = create_spark_session()
    try:
        result = extract_data(spark, request.db_config, request.query, output_path, format="xml")
        return result
    finally:
        spark.stop()

@app.post("/extract_parquet")
async def extract_to_parquet(request: ExtractionRequest):
    """Extract data from database and save to Parquet file"""
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure filename ends with .parquet
    output_filename = request.output_filename
    if not output_filename.endswith('.parquet'):
        output_filename = f"{output_filename}.parquet"
    
    output_path = os.path.join(output_dir, output_filename)
    
    spark = create_spark_session()
    try:
        result = extract_data(spark, request.db_config, request.query, output_path, format="parquet")
        return result
    finally:
        spark.stop()

@app.post("/extract_sql")
async def extract_to_sql(request: ExtractionRequest):
    """Extract data from database and save as SQL dump file"""
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure filename ends with .sql
    output_filename = request.output_filename
    if not output_filename.endswith('.sql'):
        output_filename = f"{output_filename}.sql"
    
    output_path = os.path.join(output_dir, output_filename)
    
    spark = create_spark_session()
    try:
        result = extract_data(spark, request.db_config, request.query, output_path, format="sql")
        return result
    finally:
        spark.stop()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 