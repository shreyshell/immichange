#!/usr/bin/env python3
"""
AI Processor for Immigration Policy Updates
Consumes messages from Kafka, fetches full article content, analyzes with Gemini AI,
and stores relevant ones in BigQuery.
"""

import json
import os
import time
import requests
import feedparser
from datetime import datetime
from time import mktime
from confluent_kafka import Consumer, Producer, KafkaError
from google.cloud import bigquery
from google.oauth2 import service_account
import google.generativeai as genai
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

def create_kafka_consumer():
    """Create Kafka consumer."""
    config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'sasl.mechanisms': 'PLAIN',
        'security.protocol': 'SASL_SSL',
        'sasl.username': os.getenv('KAFKA_API_KEY'),
        'sasl.password': os.getenv('KAFKA_API_SECRET'),
        'group.id': f'ai-processor-{int(time.time())}',
        'auto.offset.reset': 'earliest'
    }
    return Consumer(config)

def create_bigquery_client():
    """Create BigQuery client."""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    # Try JSON credentials first (for Railway/Vercel)
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if credentials_json:
        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        return bigquery.Client(credentials=credentials, project=project_id)
    
    # Fallback to file-based credentials (for local development)
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google-credentials.json')
    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        return bigquery.Client(credentials=credentials, project=project_id)
    
    raise Exception("No credentials found")

def setup_gemini_ai():
    """Setup Google Generative AI."""
    # Try JSON credentials first (for Railway/Vercel)
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if credentials_json:
        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        genai.configure(credentials=credentials)
        return genai.GenerativeModel('gemini-2.0-flash')
    
    # Fallback to file-based credentials (for local development)
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google-credentials.json')
    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        genai.configure(credentials=credentials)
        return genai.GenerativeModel('gemini-2.0-flash')
    
    raise Exception("No Google credentials found")

def fetch_article_content(url):
    """Fetch and extract article text from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # Try to find main content area (USCIS specific selectors)
        content = None
        for selector in ['article', '.main-content', '#main-content', '.content', 'main']:
            content = soup.select_one(selector)
            if content:
                break
        
        if not content:
            content = soup.body
        
        if content:
            text = content.get_text(separator='\n', strip=True)
            # Limit to ~8000 chars to stay within token limits
            return text[:8000] if len(text) > 8000 else text
        
        return None
    except Exception as e:
        print(f"⚠️  Failed to fetch article: {e}")
        return None


def analyze_with_ai(title, article_content, model):
    """Analyze immigration policy update with full article content."""
    
    content_section = f'Article Content:\n"""\n{article_content}\n"""' if article_content else f'Title only (article not available): "{title}"'
    
    prompt = f"""You are analyzing a USCIS immigration policy update FOR IMMIGRANTS. Your audience is immigrants and visa applicants who want to know how policy changes affect THEM.

Title: "{title}"

{content_section}

RELEVANCE CRITERIA - BE STRICT:
✅ RELEVANT: Direct policy changes, fee changes, form updates, processing changes, deadline changes, requirement changes that DIRECTLY AFFECT immigrants/applicants
❌ NOT RELEVANT:
  - Agency organizational changes (new offices, new directors, restructuring)
  - Fraud cases, criminal prosecutions, arrests, sentencings
  - General announcements without actionable changes
  - Press releases about agency achievements
  - Investigations or enforcement actions against individuals
  - Celebrations, ceremonies, recognition events

CATEGORIZATION RULES - PICK EXACTLY ONE, from the IMMIGRANT'S perspective:
- visa_type: The visa/status type affected. Examples: H-1B, Green Card, Asylum, F-1, TPS, DACA, EB-5, L-1, O-1, Naturalization, H-2B, All Visas
- type_of_change: Be SPECIFIC about what changed:
  * "Fee Change" - fees increased/decreased/new fees added
  * "Form Update" - new form version, form changes, filing changes
  * "Deadline Change" - new deadlines, extended deadlines, registration periods
  * "Process Change" - how applications are processed, lottery changes, selection changes
  * "Eligibility Change" - who qualifies, new requirements, restrictions added/removed
  * "Program Ended" - TPS terminated, program cancelled, benefits ended
  * "Program Extended" - TPS extended, deadlines extended, validity extended
  * "New Guidance" - clarification of existing rules, policy manual updates
  * "Cap Reached" - visa cap reached, no more applications accepted
- affected_groups: WHO among immigrants is affected (NOT employers, NOT agencies). Examples: H-1B Workers, Students, Asylum Seekers, Green Card Applicants, TPS Holders, All Applicants, Skilled Workers, Family Sponsors

Respond ONLY with valid JSON:

{{
    "relevant": true/false,
    "visa_type": "One category (2 words max)",
    "type_of_change": "One type (2 words max)", 
    "affected_groups": "The immigrant group affected (2 words max)",
    "severity": "High/Medium/Low",
    "summary": "2-3 sentences explaining what changed and what immigrants need to know or do",
    "effective_date": "YYYY-MM-DD if mentioned, otherwise null"
}}

CRITICAL: affected_groups must be the IMMIGRANT population affected (e.g., "H-1B Workers" not "Employers")."""
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean markdown formatting
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        ai_data = json.loads(response_text)
        
        # Handle if AI returns a list instead of dict
        if isinstance(ai_data, list):
            ai_data = ai_data[0] if ai_data else {}
        
        # Validate required fields
        for field in ['relevant', 'visa_type', 'type_of_change', 'affected_groups', 'severity', 'summary']:
            if field not in ai_data:
                ai_data[field] = None
        
        if ai_data.get('severity') not in ['High', 'Medium', 'Low']:
            ai_data['severity'] = 'Medium'
        
        return ai_data
        
    except Exception as e:
        print(f"❌ AI analysis failed: {e}")
        return {
            "relevant": False,
            "visa_type": "Unknown",
            "type_of_change": "Unknown", 
            "affected_groups": "Unknown",
            "severity": "Low",
            "summary": "Analysis failed",
            "effective_date": None
        }

def insert_to_bigquery(client, record):
    """Insert record to BigQuery."""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    table_id = f"{project_id}.Immichange.policy_events"
    
    record_copy = record.copy()
    
    # Handle datetime fields
    for field in ['published_at', 'ingested_at']:
        val = record_copy.get(field)
        if val:
            if isinstance(val, str):
                try:
                    if 'T' in val:
                        dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                        record_copy[field] = dt.isoformat()
                except:
                    record_copy[field] = None
        else:
            record_copy[field] = None
    
    # Handle effective_date - convert YYYY-MM-DD to full timestamp
    effective = record_copy.get('effective_date')
    if effective:
        if isinstance(effective, str):
            try:
                # If it's just a date, add time component
                if len(effective) == 10:  # YYYY-MM-DD format
                    record_copy['effective_date'] = f"{effective}T00:00:00"
                elif 'T' in effective:
                    record_copy['effective_date'] = effective
                else:
                    record_copy['effective_date'] = None
            except:
                record_copy['effective_date'] = None
    else:
        record_copy['effective_date'] = None
    
    errors = client.insert_rows_json(table_id, [record_copy])
    if errors:
        raise Exception(f"BigQuery insert errors: {errors}")
    return True

def process_message(message, bigquery_client, ai_model):
    """Process a single Kafka message with full article fetch."""
    try:
        data = json.loads(message.value().decode('utf-8'))
        title = data.get('title', '')
        link = data.get('link', '')
        
        print(f"🔍 Processing: {title[:60]}...")
        
        # Fetch full article content
        print(f"📄 Fetching article from {link[:50]}...")
        article_content = fetch_article_content(link)
        
        if article_content:
            print(f"✅ Fetched {len(article_content)} chars of content")
        else:
            print(f"⚠️  Could not fetch article, using title only")
        
        # AI Analysis with full content
        ai_analysis = analyze_with_ai(title, article_content, ai_model)
        
        if not ai_analysis.get('relevant', False):
            print(f"⏭️  Skipped (not relevant)")
            return False
        
        # Merge data
        enriched_data = {**data, **ai_analysis}
        enriched_data['ai_processed'] = True
        
        # Insert to BigQuery
        insert_to_bigquery(bigquery_client, enriched_data)
        
        print(f"✅ Stored: {ai_analysis['visa_type']} | {ai_analysis['severity']} severity")
        return True
        
    except Exception as e:
        print(f"❌ Failed to process: {e}")
        return False


def main():
    """Main processing loop - process newest first, stop at 50 relevant."""
    print("=== AI Processor for Immigration Policy Updates ===")
    print("🎯 Mode: Newest first, stop at 50 relevant")
    print("🤖 AI: Gemini 2.0 Flash (analyzing FULL articles)")
    print("📊 Storage: BigQuery")
    print("-" * 60)
    
    consumer = create_kafka_consumer()
    bigquery_client = create_bigquery_client()
    ai_model = setup_gemini_ai()
    
    topic = os.getenv('KAFKA_TOPIC', 'immigration.raw_updates')
    consumer.subscribe([topic])
    
    # First, consume all messages and sort by published_at
    print("📥 Loading all messages from Kafka...")
    all_messages = []
    empty_polls = 0
    
    while True:
        msg = consumer.poll(timeout=5.0)
        
        if msg is None:
            empty_polls += 1
            if empty_polls >= 3:
                break
            continue
        
        empty_polls = 0
        
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                break
            continue
        
        try:
            data = json.loads(msg.value().decode('utf-8'))
            all_messages.append(data)
        except:
            continue
    
    print(f"📊 Loaded {len(all_messages)} messages")
    
    # Sort by published_at descending (newest first)
    all_messages.sort(key=lambda x: x.get('published_at') or '', reverse=True)
    print("📅 Sorted by publication date (newest first)")
    
    consumer.close()
    
    # Process until we have 50 relevant
    relevant_count = 0
    processed_count = 0
    target_count = 50
    start_time = time.time()
    
    try:
        for data in all_messages:
            if relevant_count >= target_count:
                break
            
            title = data.get('title', '')
            link = data.get('link', '')
            
            print(f"\n🔍 Processing: {title[:60]}...")
            
            # Fetch full article
            print(f"📄 Fetching article...")
            article_content = fetch_article_content(link)
            
            if article_content:
                print(f"✅ Fetched {len(article_content)} chars")
            else:
                print(f"⚠️  Could not fetch article, using title only")
            
            # AI Analysis
            ai_analysis = analyze_with_ai(title, article_content, ai_model)
            
            processed_count += 1
            
            if not ai_analysis.get('relevant', False):
                print(f"⏭️  Skipped (not relevant)")
                continue
            
            # Merge and insert
            enriched_data = {**data, **ai_analysis}
            enriched_data['ai_processed'] = True
            
            try:
                insert_to_bigquery(bigquery_client, enriched_data)
                relevant_count += 1
                print(f"✅ Stored: {ai_analysis['visa_type']} | {ai_analysis['type_of_change']} | {ai_analysis['severity']}")
                print(f"📈 Progress: {relevant_count}/{target_count} relevant")
            except Exception as e:
                print(f"❌ BigQuery error: {e}")
            
            time.sleep(0.3)
            
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted")
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("📊 BACKFILL COMPLETE")
    print("=" * 60)
    print(f"✅ Relevant records stored: {relevant_count}/{target_count}")
    print(f"📝 Total processed: {processed_count}")
    print(f"⏱️  Time: {elapsed:.1f}s")
    
    # Transition to continuous polling
    print("\n" + "=" * 60)
    print("🔄 TRANSITIONING TO CONTINUOUS POLLING")
    print("=" * 60)
    continuous_polling(bigquery_client, ai_model)


def create_kafka_producer():
    """Create Kafka producer."""
    config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'sasl.mechanisms': 'PLAIN',
        'security.protocol': 'SASL_SSL',
        'sasl.username': os.getenv('KAFKA_API_KEY'),
        'sasl.password': os.getenv('KAFKA_API_SECRET'),
    }
    return Producer(config)


def get_existing_links(bigquery_client):
    """Get all existing links from BigQuery to avoid duplicates."""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    query = f"SELECT link FROM `{project_id}.Immichange.policy_events`"
    try:
        results = bigquery_client.query(query).result()
        return {row.link for row in results}
    except:
        return set()


def continuous_polling(bigquery_client, ai_model):
    """Continuous RSS polling mode - fetch new updates every 15 minutes."""
    print("📡 RSS URL: https://www.uscis.gov/news/rss-feed/59144")
    print("⏰ Polling interval: 15 minutes")
    print("-" * 60)
    
    poll_count = 0
    total_new = 0
    
    try:
        while True:
            poll_count += 1
            print(f"\n📡 Poll #{poll_count} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Get existing links to avoid duplicates
            existing_links = get_existing_links(bigquery_client)
            print(f"📊 {len(existing_links)} existing records in database")
            
            # Fetch RSS feed
            rss_url = "https://www.uscis.gov/news/rss-feed/59144"
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                print("❌ No entries in RSS feed")
            else:
                print(f"📰 Found {len(feed.entries)} entries in RSS feed")
                
                new_count = 0
                for entry in feed.entries:
                    # Skip if already processed
                    if entry.link in existing_links:
                        continue
                    
                    # Parse published date
                    published_at = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_at = datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat()
                    
                    # Create data record
                    data = {
                        'country': 'United States',
                        'source': 'USCIS',
                        'title': entry.title,
                        'link': entry.link,
                        'published_at': published_at,
                        'ingested_at': datetime.utcnow().isoformat(),
                    }
                    
                    print(f"\n🆕 New: {entry.title[:60]}...")
                    
                    # Fetch and analyze
                    article_content = fetch_article_content(entry.link)
                    if article_content:
                        print(f"✅ Fetched {len(article_content)} chars")
                    
                    ai_analysis = analyze_with_ai(entry.title, article_content, ai_model)
                    
                    if not ai_analysis.get('relevant', False):
                        print(f"⏭️  Skipped (not relevant)")
                        continue
                    
                    # Merge and insert
                    enriched_data = {**data, **ai_analysis}
                    enriched_data['ai_processed'] = True
                    
                    try:
                        insert_to_bigquery(bigquery_client, enriched_data)
                        new_count += 1
                        total_new += 1
                        print(f"✅ Stored: {ai_analysis['visa_type']} | {ai_analysis['type_of_change']}")
                    except Exception as e:
                        print(f"❌ BigQuery error: {e}")
                    
                    time.sleep(0.3)
                
                if new_count > 0:
                    print(f"\n🎉 Added {new_count} new updates this poll (Total new: {total_new})")
                else:
                    print(f"✅ No new updates this poll")
            
            # Wait 15 minutes
            print(f"\n⏰ Next poll in 15 minutes...")
            time.sleep(900)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Polling stopped")
        print(f"📊 Total new updates added: {total_new}")

if __name__ == "__main__":
    main()
