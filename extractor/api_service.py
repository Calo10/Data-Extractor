from fastapi import FastAPI, HTTPException
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
    
    spark = create_spark_session()
    try:
        result = extract_data(spark, request.db_config, request.query, output_path)
        return result
    finally:
        spark.stop()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 