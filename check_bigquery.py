#!/usr/bin/env python3
"""
Check BigQuery datasets and tables.
"""

import os
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    # Get credentials from environment
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(credentials=credentials, project=project_id)
    else:
        client = bigquery.Client(project=project_id)
    
    print(f"Project ID: {project_id}")
    print("Available datasets:")
    
    datasets = list(client.list_datasets())
    if datasets:
        for dataset in datasets:
            print(f"  - {dataset.dataset_id}")
            
            # List tables in each dataset
            tables = list(client.list_tables(dataset.dataset_id))
            if tables:
                for table in tables:
                    print(f"    └── {table.table_id}")
            else:
                print("    └── (no tables)")
    else:
        print("  No datasets found")

if __name__ == "__main__":
    main()