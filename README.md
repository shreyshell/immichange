# Immigration Policy Events Pipeline with AI Analysis

A complete data pipeline that fetches USCIS immigration updates, processes them with AI, streams through Kafka, stores in BigQuery, and serves via a REST API with intelligent categorization.

## Architecture

```
RSS Feed → Kafka Producer → Kafka Topic → Kafka Consumer + Google Generative AI → BigQuery → REST API
```

## New AI Integration

The system now uses **Google Generative AI (Gemini)** to automatically analyze each USCIS update and extract:

- **visa_type**: Type of visa affected (H-1B, Green Card, Asylum, etc.)
- **type_of_change**: Nature of change (Policy Update, Fee Change, etc.)
- **affected_groups**: Who is impacted (Skilled Workers, Students, etc.)
- **severity**: Impact level (Low, Medium, High)
- **summary**: Concise 1-2 sentence summary

## Components

### 1. RSS Publisher (`immigration_rss_reader.py`)
- Fetches latest USCIS immigration updates from RSS feed
- Publishes each update as JSON message to Kafka topic
- Runs once and exits

### 2. AI-Enhanced Kafka Consumer (`kafka_bigquery_consumer.py`)
- Background process consuming from Kafka topic `immigration.raw_updates`
- **NEW**: Calls Google Generative AI to analyze each update before storage
- Extracts structured information (visa type, severity, summary, etc.)
- Merges AI-generated fields with original message
- Inserts enriched data into BigQuery table `Immichange.policy_events`
- Includes fallback data if AI processing fails

### 3. REST API (`api_server.py`)
- FastAPI backend serving immigration policy data with AI analysis
- Endpoint: `GET /api/history` - Returns recent 50 policy events with AI fields
- Interactive docs at `/docs`

## Setup

### Prerequisites
- Python 3.9+
- Confluent Cloud Kafka cluster
- Google Cloud BigQuery dataset
- **NEW**: Google Generative AI API key
- Service account with BigQuery permissions

### Installation
```bash
pip3 install -r requirements.txt
```

### Environment Variables
Create `.env` file with:
```env
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=your-cluster.region.aws.confluent.cloud:9092
KAFKA_API_KEY=your-api-key
KAFKA_API_SECRET=your-api-secret
KAFKA_TOPIC=immigration.raw_updates

# Google Cloud Configuration (for BigQuery)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json

# Google Generative AI Configuration
GOOGLE_API_KEY=your-google-api-key
```

## Usage

### 1. Test AI Integration (Optional)
```bash
python3 test_generative_ai.py
```

### 2. Start the Consumer (Background Process)
```bash
python3 kafka_bigquery_consumer.py
```

### 3. Publish RSS Updates
```bash
python3 immigration_rss_reader.py
```

### 4. Start the API Server
```bash
python3 api_server.py
```

### 5. Access the API
- Health check: `GET http://localhost:8000/api/health`
- Policy history: `GET http://localhost:8000/api/history`
- API docs: `http://localhost:8000/docs`

## Enhanced Data Schema

Each policy event now contains:

**Original Fields:**
- `country`: "United States"
- `source`: "USCIS"
- `title`: Policy update title
- `link`: Direct link to USCIS page
- `published_at`: Original publication timestamp
- `ingested_at`: When the record was inserted into BigQuery

**AI-Generated Fields:**
- `visa_type`: Visa category affected (e.g., "H-1B", "Asylum")
- `type_of_change`: Type of policy change (e.g., "Policy Update", "Fee Change")
- `affected_groups`: Impacted populations (e.g., "Skilled Workers", "Students")
- `severity`: Impact level ("Low", "Medium", or "High")
- `summary`: AI-generated concise summary
- `ai_processed`: Boolean indicating if AI processing succeeded

## Enhanced API Response Format

```json
{
  "success": true,
  "count": 5,
  "data": [
    {
      "country": "United States",
      "visa_type": "Asylum",
      "type_of_change": "Policy Update",
      "affected_groups": "Asylum Seekers",
      "severity": "High",
      "summary": "New rule bars asylum for individuals who pose security threats and public health risks.",
      "source": "https://www.uscis.gov/...",
      "timestamp": "2025-12-29T15:58:15",
      "effective_date": "2025-12-29T15:58:15",
      "title": "DHS, DOJ Announce Rule to Bar Asylum...",
      "link": "https://www.uscis.gov/...",
      "published_at": "2025-12-29T15:58:15",
      "ingested_at": "2025-12-31T08:36:38.261537",
      "ai_processed": true
    }
  ]
}
```

## Current Status

✅ **RSS Publisher**: Working - fetches and publishes to Kafka
✅ **AI-Enhanced Kafka Consumer**: Working - AI analysis + BigQuery storage
✅ **Google Generative AI Integration**: Working - automatic categorization and summarization
✅ **REST API**: Working - serving enriched policy data via HTTP endpoints
⚠️ **BigQuery Queries**: Limited by service account permissions

The data pipeline is fully operational with AI enhancement. Each USCIS update is automatically analyzed and categorized before storage.

## Monitoring

- Consumer logs show AI processing success rate
- BigQuery table includes `ai_processed` flag for monitoring
- Fallback data ensures system continues if AI processing fails
- API health endpoint checks BigQuery connectivity

## Files

- `immigration_rss_reader.py` - RSS to Kafka publisher
- `kafka_bigquery_consumer.py` - **Enhanced** Kafka to BigQuery consumer with AI
- `api_server.py` - **Enhanced** FastAPI REST API server with AI fields
- `test_generative_ai.py` - **NEW** Test script for AI integration
- `requirements.txt` - Python dependencies (includes Google Generative AI)
- `.env` - Environment variables (not in git)
- `google-credentials.json` - Service account key (not in git)