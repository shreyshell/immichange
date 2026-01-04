# Immichange - Immigration Policy Tracker

A real-time data pipeline that monitors USCIS immigration updates, analyzes them with AI, and provides intelligent categorization through a web dashboard.

## Architecture

```
USCIS RSS → Kafka → AI Analysis → BigQuery → REST API → Web Dashboard
```

## Key Features

- **Real-time monitoring** of USCIS policy updates
- **AI-powered analysis** using Google Gemini for intelligent categorization
- **Full article analysis** for comprehensive policy understanding
- **Smart fallback system** for reliable operation
- **Interactive web dashboard** for browsing updates

## Data Processing Strategy

### Backfill Data (High Quality)
Our initial dataset uses **full article analysis** where we fetch complete USCIS articles and analyze them with AI. This provides:
- Detailed policy summaries
- Accurate effective dates extracted from article content
- Comprehensive impact analysis
- Rich categorization based on full context

### Live Updates (Fallback Mode)
For continuous monitoring, we discovered that USCIS blocks article fetching requests from cloud providers (a common anti-scraping measure). Our system gracefully handles this by:
- Using RSS descriptions (which contain substantial policy details)
- Maintaining the same AI analysis quality
- Ensuring uninterrupted service for new updates

### Production Scaling Plan
As this service grows to monitor multiple government sources, we plan to implement:
- **Residential proxy networks** (Bright Data, Oxylabs) for reliable article access
- **Headless browser services** (ScrapingBee, Apify) for JavaScript-heavy sites
- **Multi-region deployment** to distribute requests across different IP ranges
- **API partnerships** with government agencies where available

## AI Analysis

Each policy update is analyzed to extract:
- **visa_type**: Specific visa category (H-1B, Green Card, Asylum, etc.)
- **type_of_change**: Nature of change (Policy Update, Fee Change, Process Change, etc.)
- **affected_groups**: Target immigrant populations (H-1B Workers, Students, etc.)
- **severity**: Impact level (High/Medium/Low)
- **summary**: Clear explanation of what changed
- **effective_date**: When changes take effect (when mentioned)

## Quick Start

### Prerequisites
- Python 3.9+
- Confluent Cloud Kafka cluster
- Google Cloud BigQuery
- Google Cloud credentials for Gemini AI

### Local Development
```bash
# Install dependencies
pip3 install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Run backfill (full article analysis)
python3 ai_processor.py

# Start API server
python3 api_server.py

# Open dashboard
open http://localhost:8080
```

### Deployment
- **Frontend**: Deployed on Vercel
- **Backend**: Deployed on Railway with automatic scaling
- **Data**: Google Cloud BigQuery for storage and querying

## Environment Variables

```env
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=your-cluster.confluent.cloud:9092
KAFKA_API_KEY=your-api-key
KAFKA_API_SECRET=your-api-secret
KAFKA_TOPIC=immigration.raw_updates

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}

# For local development
GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
```

## API Endpoints

- `GET /api/history` - Recent policy updates with AI analysis
- `GET /api/health` - System health check
- `GET /docs` - Interactive API documentation

## Technical Notes

**Article Fetching Limitation**: USCIS (like many government sites) blocks requests from cloud provider IP addresses as an anti-scraping measure. This is why our production deployment uses RSS descriptions for new updates while maintaining high-quality backfill data from full article analysis.

**Scaling Strategy**: For a production service monitoring multiple government sources, we would implement residential proxy networks and headless browser services to reliably access full article content from any source.

## Files

- `ai_processor.py` - Main data pipeline with AI analysis
- `api_server.py` - FastAPI REST API server  
- `start.py` - Combined startup script for deployment
- `index.html`, `script.js`, `styles.css` - Web dashboard
- `requirements.txt` - Python dependencies
- `Procfile`, `railway.json` - Deployment configuration