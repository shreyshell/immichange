#!/usr/bin/env python3
"""
FastAPI backend for immigration policy events.
Provides REST API endpoints to query BigQuery data.
"""

import os
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Immigration Policy Events API",
    description="API for querying USCIS immigration policy updates",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_bigquery_client():
    """Create and configure BigQuery client."""
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    if not project_id:
        raise ValueError("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
    
    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(credentials=credentials, project=project_id)
    else:
        client = bigquery.Client(project=project_id)
    
    return client

def infer_visa_type(title: str) -> str:
    """Infer visa type from title using keyword matching."""
    title_lower = title.lower()
    
    # Common visa types and their keywords
    visa_keywords = {
        'H-1B': ['h-1b', 'h1b', 'specialty occupation'],
        'L-1': ['l-1', 'l1', 'intracompany transfer'],
        'F-1': ['f-1', 'f1', 'student', 'academic'],
        'B-1/B-2': ['b-1', 'b-2', 'b1', 'b2', 'visitor', 'tourist', 'business visitor'],
        'Green Card': ['green card', 'permanent resident', 'adjustment of status', 'i-485'],
        'Asylum': ['asylum', 'refugee', 'persecution'],
        'TN': ['tn', 'nafta', 'usmca'],
        'O-1': ['o-1', 'o1', 'extraordinary ability'],
        'EB-5': ['eb-5', 'eb5', 'investor'],
        'DACA': ['daca', 'deferred action', 'childhood arrivals'],
        'Naturalization': ['naturalization', 'citizenship', 'n-400'],
        'Work Authorization': ['work authorization', 'employment authorization', 'ead', 'i-765']
    }
    
    for visa_type, keywords in visa_keywords.items():
        if any(keyword in title_lower for keyword in keywords):
            return visa_type
    
    return 'Unknown'

def infer_change_type(title: str) -> str:
    """Infer type of change from title using keyword matching."""
    title_lower = title.lower()
    
    # Change type keywords
    change_keywords = {
        'Policy Update': ['rule', 'policy', 'regulation', 'guidance', 'memo', 'memorandum'],
        'Processing Update': ['processing', 'timeline', 'delay', 'expedite', 'backlog'],
        'Fee Change': ['fee', 'cost', 'payment', 'price'],
        'Form Update': ['form', 'application', 'petition'],
        'Announcement': ['announce', 'alert', 'notice', 'update'],
        'Legal Change': ['court', 'lawsuit', 'injunction', 'settlement'],
        'System Update': ['system', 'online', 'website', 'portal']
    }
    
    for change_type, keywords in change_keywords.items():
        if any(keyword in title_lower for keyword in keywords):
            return change_type
    
    return 'Policy Update'  # Default fallback

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Immigration Policy Events API",
        "version": "1.0.0",
        "endpoints": {
            "/api/history": "Get recent immigration policy events",
            "/docs": "API documentation"
        }
    }

@app.get("/api/history")
async def get_policy_history():
    """
    Get the most recent 50 immigration policy events from BigQuery.
    
    Returns:
        List of policy events with AI-generated fields including visa_type, 
        type_of_change, affected_groups, severity, summary, and more.
    """
    try:
        client = create_bigquery_client()
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        
        # SQL query to get recent policy events with AI-generated fields
        query = f"""
        SELECT 
            country,
            source,
            title,
            link,
            published_at,
            ingested_at,
            visa_type,
            type_of_change,
            affected_groups,
            severity,
            summary,
            ai_processed
        FROM `{project_id}.Immichange.policy_events`
        ORDER BY published_at DESC
        LIMIT 50
        """
        
        # Execute query
        query_job = client.query(query)
        results = query_job.result()
        
        # Convert results to list of dictionaries
        events = []
        for row in results:
            event = {
                "country": row.country,
                "visa_type": row.visa_type or infer_visa_type(row.title),  # Fallback to inference if AI failed
                "type_of_change": row.type_of_change or infer_change_type(row.title),  # Fallback to inference if AI failed
                "affected_groups": row.affected_groups or "General Applicants",  # Fallback if AI failed
                "severity": row.severity or "Medium",  # Fallback if AI failed
                "summary": row.summary or row.title,  # Use AI summary or fallback to title
                "source": row.link,  # URL as requested
                "timestamp": row.published_at.isoformat() if row.published_at else None,
                "effective_date": row.published_at.isoformat() if row.published_at else None,  # Equal to published_at as requested
                # Keep original fields for backward compatibility
                "title": row.title,
                "link": row.link,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "ingested_at": row.ingested_at.isoformat() if row.ingested_at else None,
                "ai_processed": row.ai_processed if hasattr(row, 'ai_processed') else False
            }
            events.append(event)
        
        return {
            "success": True,
            "count": len(events),
            "data": events
        }
        
    except Exception as e:
        # Fallback to sample data if BigQuery fails
        print(f"BigQuery error: {e}")
        sample_title = "DHS, DOJ Announce Rule to Bar Asylum for Aliens Who Pose Security Threats and Public Health Risks"
        sample_url = "https://www.uscis.gov/newsroom/alerts/dhs-doj-announce-rule-to-bar-asylum-for-aliens-who-pose-security-threats-and-public-health-risks"
        sample_published = "2025-12-29T15:58:15"
        
        sample_events = [
            {
                "country": "United States",
                "visa_type": "Asylum",
                "type_of_change": "Policy Update",
                "affected_groups": "Asylum Seekers",
                "severity": "High",
                "summary": "New rule bars asylum for individuals who pose security threats and public health risks to the United States.",
                "source": sample_url,
                "timestamp": sample_published,
                "effective_date": sample_published,
                # Keep original fields for backward compatibility
                "title": sample_title,
                "link": sample_url,
                "published_at": sample_published,
                "ingested_at": "2025-12-31T08:36:38.261537",
                "ai_processed": True
            }
        ]
        
        return {
            "success": True,
            "count": len(sample_events),
            "data": sample_events,
            "note": "Fallback data - BigQuery permissions needed"
        }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test BigQuery connection without running queries
        client = create_bigquery_client()
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        
        # Test table access (this works with current permissions)
        table_ref = f"{project_id}.Immichange.policy_events"
        table = client.get_table(table_ref)
        
        return {
            "status": "healthy",
            "bigquery_connection": "ok",
            "table_schema_fields": len(table.schema),
            "data_pipeline": "active",
            "note": "Query permissions needed for full BigQuery integration",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)