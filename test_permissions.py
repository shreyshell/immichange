#!/usr/bin/env python3
"""
Test BigQuery permissions and access methods.
"""

import os
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(credentials=credentials, project=project_id)
    else:
        client = bigquery.Client(project=project_id)
    
    print(f"Project ID: {project_id}")
    
    # Test different access methods
    try:
        # Method 1: List tables (this worked before)
        print("Testing table listing...")
        dataset = client.dataset('Immichange')
        tables = list(client.list_tables(dataset))
        print(f"✓ Can list tables: {[t.table_id for t in tables]}")
        
        # Method 2: Get table schema
        print("Testing table schema access...")
        table_ref = f"{project_id}.Immichange.policy_events"
        table = client.get_table(table_ref)
        print(f"✓ Can access table schema: {len(table.schema)} fields")
        
        # Method 3: Try a simple query
        print("Testing query execution...")
        query = f"SELECT COUNT(*) as total FROM `{project_id}.Immichange.policy_events`"
        query_job = client.query(query)
        result = list(query_job.result())[0]
        print(f"✓ Query successful: {result.total} total rows")
        
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    main()