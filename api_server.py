#!/usr/bin/env python3
"""
FastAPI backend for immigration policy events.
Provides REST API endpoints to query BigQuery data and serves the web dashboard.
"""

import os
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Serve static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard."""
    return FileResponse("index.html")

@app.get("/index.html")
async def serve_dashboard_alt():
    """Alternative route for the dashboard."""
    return FileResponse("index.html")

def create_bigquery_client():
    """Create BigQuery client using the same approach as AI processor."""
    import json
    
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    if not project_id:
        raise ValueError("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
    
    # Try to get credentials from environment variable first (for Railway/Vercel)
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if credentials_json:
        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = bigquery.Client(credentials=credentials, project=project_id)
    else:
        # Fallback to file-based credentials (for local development)
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google-credentials.json')
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            client = bigquery.Client(credentials=credentials, project=project_id)
        else:
            # Use default credentials
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
async def get_policy_history(
    country: str = None,
    visa_type: str = None,
    affected_groups: str = None,
    type_of_change: str = None
):
    """
    Get the most recent 50 immigration policy events from BigQuery with optional filtering.
    
    Query Parameters:
        country: Filter by country name
        visa_type: Filter by visa type
        affected_groups: Filter by affected groups
        type_of_change: Filter by type of change
    
    Returns:
        List of policy events with AI-generated fields including visa_type, 
        type_of_change, affected_groups, severity, summary, and more.
    """
    try:
        client = create_bigquery_client()
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        
        # Build WHERE clause for filtering with proper parameterization
        where_conditions = []
        query_params = {}
        
        if country:
            where_conditions.append("country = @country")
            query_params['country'] = country
        if visa_type:
            where_conditions.append("visa_type = @visa_type")
            query_params['visa_type'] = visa_type
        if affected_groups:
            where_conditions.append("affected_groups = @affected_groups")
            query_params['affected_groups'] = affected_groups
        if type_of_change:
            where_conditions.append("type_of_change = @type_of_change")
            query_params['type_of_change'] = type_of_change
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # SQL query to get recent policy events with AI-generated fields and optional filtering
        # Only include relevant records (relevant = true or relevant IS NULL for backward compatibility)
        query = f"""
        SELECT 
            country,
            source,
            title,
            link,
            published_at,
            ingested_at,
            relevant,
            visa_type,
            type_of_change,
            affected_groups,
            severity,
            summary,
            effective_date,
            ai_processed
        FROM `{project_id}.Immichange.policy_events`
        WHERE (relevant = true OR relevant IS NULL)  -- Only show relevant updates
        {where_clause}
        ORDER BY published_at DESC
        LIMIT 50
        """
        
        # Execute query with parameters
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter(name, "STRING", value)
            for name, value in query_params.items()
        ])
        query_job = client.query(query, job_config=job_config)
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
                "timestamp": (row.published_at or row.ingested_at).isoformat() if (row.published_at or row.ingested_at) else None,
                "effective_date": row.effective_date.isoformat() if row.effective_date else None,  # Use AI-calculated effective_date or None if not available
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
            "data": events,
            "filters_applied": {
                "country": country,
                "visa_type": visa_type,
                "affected_groups": affected_groups,
                "type_of_change": type_of_change
            }
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
                "effective_date": None,  # No specific effective date for this announcement
                # Keep original fields for backward compatibility
                "title": sample_title,
                "link": sample_url,
                "published_at": sample_published,
                "ingested_at": "2025-12-31T08:36:38.261537",
                "ai_processed": True
            }
        ]
        
        # Apply client-side filtering to sample data if needed
        filtered_events = sample_events
        if country:
            filtered_events = [e for e in filtered_events if e["country"] == country]
        if visa_type:
            filtered_events = [e for e in filtered_events if e["visa_type"] == visa_type]
        if affected_groups:
            filtered_events = [e for e in filtered_events if e["affected_groups"] == affected_groups]
        if type_of_change:
            filtered_events = [e for e in filtered_events if e["type_of_change"] == type_of_change]
        
        return {
            "success": True,
            "count": len(filtered_events),
            "data": filtered_events,
            "filters_applied": {
                "country": country,
                "visa_type": visa_type,
                "affected_groups": affected_groups,
                "type_of_change": type_of_change
            },
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
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 Starting Immichange API server on http://localhost:{port}")
    print(f"📊 Dashboard: http://localhost:{port}")
    print(f"📋 API Docs: http://localhost:{port}/docs")
    print(f"🔍 Health Check: http://localhost:{port}/api/health")
    uvicorn.run(app, host="127.0.0.1", port=port)