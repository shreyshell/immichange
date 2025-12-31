#!/usr/bin/env python3
"""
Setup script to create BigQuery dataset and table for immigration policy events.
"""

import os
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv

def create_bigquery_client():
    """Create and configure BigQuery client."""
    # Get credentials from environment
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    if not project_id:
        raise ValueError("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
    
    if credentials_path and os.path.exists(credentials_path):
        # Use service account file
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(credentials=credentials, project=project_id)
    else:
        # Use default credentials (for Cloud Run, GCE, etc.)
        client = bigquery.Client(project=project_id)
    
    return client

def setup_dataset_and_table():
    """Create BigQuery dataset and table if they don't exist."""
    load_dotenv()
    
    client = create_bigquery_client()
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    dataset_id = 'immichange'
    table_id = 'policy_events'
    
    # Create dataset
    dataset_ref = client.dataset(dataset_id)
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {dataset_id} already exists")
    except Exception:
        print(f"Creating dataset {dataset_id}")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"  # Set location
        dataset = client.create_dataset(dataset)
        print(f"Created dataset {dataset.dataset_id}")
    
    # Create table
    table_ref = dataset_ref.table(table_id)
    try:
        client.get_table(table_ref)
        print(f"Table {dataset_id}.{table_id} already exists")
    except Exception:
        print(f"Creating table {dataset_id}.{table_id}")
        
        # Define table schema
        schema = [
            bigquery.SchemaField("country", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("link", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("published_at", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
        ]
        
        table = bigquery.Table(table_ref, schema=schema)
        table = client.create_table(table)
        print(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")
    
    print("BigQuery setup complete!")

if __name__ == "__main__":
    setup_dataset_and_table()