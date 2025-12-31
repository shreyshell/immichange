#!/usr/bin/env python3
"""
Enhanced Kafka to BigQuery consumer for immigration policy events.
Features:
- Deduplication based on source, title, and published_at
- Historical backfill (50 unique records from earliest offset)
- Continuous RSS polling every 15 minutes
- Vertex AI enrichment for all new records
- Idempotent and safe to re-run
"""

import json
import os
import sys
import time
import hashlib
from datetime import datetime, timedelta
from typing import Set, Dict, Any, Optional
from confluent_kafka import Consumer, Producer, KafkaError
from google.cloud import bigquery
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel
import feedparser
from dotenv import load_dotenv

class ImmigrationPolicyProcessor:
    """Main processor class for immigration policy updates."""
    
    def __init__(self):
        """Initialize the processor with all required clients."""
        load_dotenv()
        
        # Configuration
        self.kafka_topic = os.getenv('KAFKA_TOPIC', 'immigration.raw_updates')
        self.dataset_id = 'Immichange'
        self.table_id = 'policy_events'
        self.rss_url = 'https://www.uscis.gov/rss/news-releases'
        self.target_backfill_count = 50
        self.polling_interval = 15 * 60  # 15 minutes in seconds
        
        # Initialize clients
        self.kafka_consumer = None
        self.kafka_producer = None
        self.bigquery_client = None
        self.vertex_ai_model = None
        
        # Tracking
        self.processed_hashes: Set[str] = set()
        self.backfill_complete = False
        self.unique_records_inserted = 0
        
        print("Initializing Immigration Policy Processor...")
        self._initialize_clients()
        
    def _initialize_clients(self):
        """Initialize all required clients."""
        try:
            self.kafka_consumer = self._create_kafka_consumer()
            self.kafka_producer = self._create_kafka_producer()
            self.bigquery_client = self._create_bigquery_client()
            self.vertex_ai_model = self._create_vertex_ai_client()
            
            # Ensure table exists and load existing hashes
            self._ensure_table_exists()
            self._load_existing_hashes()
            
            print("✓ All clients initialized successfully")
            
        except Exception as e:
            print(f"✗ Failed to initialize clients: {e}")
            sys.exit(1)
    
    def _create_kafka_consumer(self):
        """Create and configure Kafka consumer for backfill."""
        config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': 'SASL_SSL',
            'sasl.mechanisms': 'PLAIN',
            'sasl.username': os.getenv('KAFKA_API_KEY'),
            'sasl.password': os.getenv('KAFKA_API_SECRET'),
            'group.id': 'bigquery-consumer-backfill',
            'auto.offset.reset': 'earliest',  # Start from earliest for backfill
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 1000
        }
        
        # Validate required config
        required_configs = ['bootstrap.servers', 'sasl.username', 'sasl.password']
        for key in required_configs:
            if not config[key]:
                raise ValueError(f"Missing required Kafka configuration: {key}")
        
        return Consumer(config)
    
    def _create_kafka_producer(self):
        """Create and configure Kafka producer for RSS updates."""
        config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': 'SASL_SSL',
            'sasl.mechanisms': 'PLAIN',
            'sasl.username': os.getenv('KAFKA_API_KEY'),
            'sasl.password': os.getenv('KAFKA_API_SECRET'),
        }
        
        return Producer(config)
    
    def _create_bigquery_client(self):
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
    
    def _create_vertex_ai_client(self):
        """Initialize Vertex AI client."""
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
        
        if not project_id:
            raise ValueError("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
        
        vertexai.init(project=project_id, location=location)
        return GenerativeModel("gemini-1.5-flash")
    
    def _generate_record_hash(self, source: str, title: str, published_at: str) -> str:
        """Generate a unique hash for deduplication."""
        # Create a consistent string for hashing
        dedup_string = f"{source}|{title}|{published_at}"
        return hashlib.sha256(dedup_string.encode('utf-8')).hexdigest()
    
    def _load_existing_hashes(self):
        """Load existing record hashes from BigQuery for deduplication."""
        try:
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            query = f"""
            SELECT DISTINCT 
                SHA256(CONCAT(COALESCE(source, ''), '|', COALESCE(title, ''), '|', COALESCE(CAST(published_at AS STRING), ''))) as record_hash
            FROM `{project_id}.{self.dataset_id}.{self.table_id}`
            WHERE source IS NOT NULL AND title IS NOT NULL AND published_at IS NOT NULL
            """
            
            query_job = self.bigquery_client.query(query)
            results = query_job.result()
            
            for row in results:
                self.processed_hashes.add(row.record_hash)
            
            print(f"✓ Loaded {len(self.processed_hashes)} existing record hashes for deduplication")
            
        except Exception as e:
            print(f"⚠ Could not load existing hashes (table may be empty): {e}")
            self.processed_hashes = set()
    
    def _ensure_table_exists(self):
        """Ensure the BigQuery table exists with the correct schema."""
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        table_ref = f"{project_id}.{self.dataset_id}.{self.table_id}"
        
        try:
            self.bigquery_client.get_table(table_ref)
            print(f"✓ Table {self.dataset_id}.{self.table_id} exists")
            return
        except Exception:
            print(f"Creating table {self.dataset_id}.{self.table_id}")
        
        # Define table schema with AI-generated fields
        schema = [
            # Original fields
            bigquery.SchemaField("country", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("link", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("published_at", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
            
            # AI-generated fields
            bigquery.SchemaField("visa_type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("type_of_change", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("affected_groups", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("severity", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("summary", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("ai_processed", "BOOLEAN", mode="REQUIRED"),
            
            # Deduplication field
            bigquery.SchemaField("record_hash", "STRING", mode="REQUIRED"),
        ]
        
        table = bigquery.Table(table_ref, schema=schema)
        table = self.bigquery_client.create_table(table)
        print(f"✓ Created table {table.project}.{table.dataset_id}.{table.table_id}")
    
    def _is_duplicate(self, source: str, title: str, published_at: str) -> bool:
        """Check if a record already exists based on deduplication hash."""
        record_hash = self._generate_record_hash(source, title, published_at)
        return record_hash in self.processed_hashes
    def _process_with_vertex_ai(self, title: str, source_url: str) -> Optional[Dict[str, Any]]:
        """
        Process update with Vertex AI to extract structured information.
        
        Args:
            title: Update title
            source_url: Source URL
        
        Returns:
            dict: AI-generated fields or None if processing fails
        """
        try:
            # Create prompt for Vertex AI
            prompt = f"""
Analyze this immigration policy update and return a JSON object with the following fields:

Title: {title}
Source URL: {source_url}

Please extract and return ONLY a valid JSON object with these exact fields:
- visa_type: The type of visa or immigration category affected (e.g., "H-1B", "Green Card", "Asylum", "Student Visa", etc.)
- type_of_change: The nature of the change (e.g., "Policy Update", "Fee Change", "Processing Update", "New Requirement", etc.)
- affected_groups: Who is impacted (e.g., "Skilled Workers", "Students", "Asylum Seekers", "All Applicants", etc.)
- severity: Impact level - must be exactly "Low", "Medium", or "High"
- summary: A concise 1-2 sentence summary of the update

Return only the JSON object, no additional text or formatting.
"""

            # Generate response
            response = self.vertex_ai_model.generate_content(prompt)
            
            if not response or not response.text:
                print("Warning: Empty response from Vertex AI")
                return None
            
            # Parse JSON response
            try:
                ai_data = json.loads(response.text.strip())
                
                # Validate required fields
                required_fields = ['visa_type', 'type_of_change', 'affected_groups', 'severity', 'summary']
                for field in required_fields:
                    if field not in ai_data:
                        print(f"Warning: Missing field '{field}' in AI response")
                        return None
                
                # Validate severity values
                if ai_data['severity'] not in ['Low', 'Medium', 'High']:
                    print(f"Warning: Invalid severity value: {ai_data['severity']}")
                    ai_data['severity'] = 'Medium'  # Default fallback
                
                return ai_data
                
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse AI response as JSON: {e}")
                print(f"AI Response: {response.text[:200]}...")
                return None
                
        except Exception as e:
            print(f"Warning: Vertex AI processing failed: {e}")
            return None

    def _get_fallback_ai_data(self) -> Dict[str, Any]:
        """Return fallback data when AI processing fails."""
        return {
            'visa_type': 'General',
            'type_of_change': 'Policy Update',
            'affected_groups': 'General Public',
            'severity': 'Medium',
            'summary': 'Immigration policy update - details require manual review.'
        }
    
    def _insert_to_bigquery(self, message_data: Dict[str, Any], ai_data: Optional[Dict[str, Any]] = None) -> bool:
        """Insert a message with AI-generated data into BigQuery table."""
        try:
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            table_ref = f"{project_id}.{self.dataset_id}.{self.table_id}"
            table = self.bigquery_client.get_table(table_ref)
            
            # Generate record hash for deduplication
            record_hash = self._generate_record_hash(
                message_data.get('source', ''),
                message_data.get('title', ''),
                message_data.get('published_at', '')
            )
            
            # Prepare row data with original fields
            row_data = {
                'country': message_data.get('country'),
                'source': message_data.get('source'),
                'title': message_data.get('title'),
                'link': message_data.get('link'),
                'published_at': message_data.get('published_at'),
                'ingested_at': datetime.utcnow().isoformat(),
                'ai_processed': ai_data is not None,
                'record_hash': record_hash
            }
            
            # Add AI-generated fields if available
            if ai_data:
                row_data.update({
                    'visa_type': ai_data.get('visa_type'),
                    'type_of_change': ai_data.get('type_of_change'),
                    'affected_groups': ai_data.get('affected_groups'),
                    'severity': ai_data.get('severity'),
                    'summary': ai_data.get('summary')
                })
            
            # Insert row
            errors = self.bigquery_client.insert_rows_json(table, [row_data])
            
            if errors:
                print(f"BigQuery insert errors: {errors}")
                return False
            
            # Add hash to processed set
            self.processed_hashes.add(record_hash)
            return True
            
        except Exception as e:
            print(f"Error inserting to BigQuery: {e}")
            return False
    
    def _process_message(self, message_data: Dict[str, Any]) -> bool:
        """Process a single message through the complete pipeline."""
        try:
            # Check for deduplication
            source = message_data.get('source', '')
            title = message_data.get('title', '')
            published_at = message_data.get('published_at', '')
            
            if self._is_duplicate(source, title, published_at):
                print(f"  ⚠ Duplicate detected, skipping: {title[:60]}...")
                return False
            
            print(f"  Processing: {title[:60]}...")
            
            # Process with Vertex AI
            source_url = message_data.get('link', '')
            ai_data = self._process_with_vertex_ai(title, source_url)
            
            if ai_data:
                print(f"    ✓ AI Analysis: {ai_data['visa_type']} | {ai_data['severity']} severity")
            else:
                # Use fallback data if AI processing fails
                ai_data = self._get_fallback_ai_data()
                print(f"    ⚠ Using fallback data (AI processing failed)")
            
            # Insert to BigQuery
            success = self._insert_to_bigquery(message_data, ai_data)
            
            if success:
                self.unique_records_inserted += 1
                print(f"    ✓ Stored in BigQuery (Unique record #{self.unique_records_inserted})")
                print(f"    Summary: {ai_data['summary'][:80]}...")
                return True
            else:
                print(f"    ✗ Failed to store in BigQuery")
                return False
                
        except Exception as e:
            print(f"  ✗ Error processing message: {e}")
            return False
    
    def _backfill_from_kafka(self):
        """
        Perform historical backfill from Kafka topic.
        Consumes from earliest offset until 50 unique records are processed.
        """
        print(f"\n=== Starting Historical Backfill ===")
        print(f"Target: {self.target_backfill_count} unique records")
        print(f"Topic: {self.kafka_topic}")
        print("-" * 50)
        
        # Subscribe to topic
        self.kafka_consumer.subscribe([self.kafka_topic])
        
        processed_messages = 0
        start_time = time.time()
        
        try:
            while self.unique_records_inserted < self.target_backfill_count:
                msg = self.kafka_consumer.poll(timeout=5.0)
                
                if msg is None:
                    # No more messages available
                    print(f"No more messages available. Processed {processed_messages} total messages.")
                    break
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        print(f"Reached end of partition {msg.partition()}")
                        break
                    else:
                        print(f"Consumer error: {msg.error()}")
                        continue
                
                try:
                    # Parse JSON message
                    message_data = json.loads(msg.value().decode('utf-8'))
                    processed_messages += 1
                    
                    print(f"\nMessage {processed_messages}:")
                    
                    # Process through complete pipeline
                    success = self._process_message(message_data)
                    
                    if success:
                        print(f"Progress: {self.unique_records_inserted}/{self.target_backfill_count} unique records")
                    
                except json.JSONDecodeError as e:
                    print(f"✗ Failed to parse JSON: {e}")
                except Exception as e:
                    print(f"✗ Failed to process message: {e}")
        
        except KeyboardInterrupt:
            print(f"\nBackfill interrupted by user")
        
        finally:
            elapsed_time = time.time() - start_time
            print(f"\n=== Backfill Complete ===")
            print(f"Total messages processed: {processed_messages}")
            print(f"Unique records inserted: {self.unique_records_inserted}")
            print(f"Duplicates skipped: {processed_messages - self.unique_records_inserted}")
            print(f"Time elapsed: {elapsed_time:.1f} seconds")
            
            if self.unique_records_inserted >= self.target_backfill_count:
                print(f"✓ Target of {self.target_backfill_count} unique records reached!")
                self.backfill_complete = True
            else:
                print(f"⚠ Only {self.unique_records_inserted} unique records found in topic")
                self.backfill_complete = True  # Continue anyway
    
    def _fetch_rss_updates(self) -> list:
        """Fetch latest updates from USCIS RSS feed."""
        try:
            print(f"Fetching RSS updates from: {self.rss_url}")
            feed = feedparser.parse(self.rss_url)
            
            if feed.bozo:
                print(f"Warning: RSS feed parsing issues: {feed.bozo_exception}")
            
            updates = []
            for entry in feed.entries:
                # Convert RSS entry to our message format
                published_time = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_time = datetime(*entry.published_parsed[:6]).isoformat()
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_time = datetime(*entry.updated_parsed[:6]).isoformat()
                
                update = {
                    'country': 'United States',
                    'source': 'USCIS',
                    'title': entry.title,
                    'link': entry.link,
                    'published_at': published_time
                }
                updates.append(update)
            
            print(f"✓ Fetched {len(updates)} RSS entries")
            return updates
            
        except Exception as e:
            print(f"✗ Failed to fetch RSS updates: {e}")
            return []
    
    def _publish_to_kafka(self, update: Dict[str, Any]):
        """Publish an update to the Kafka topic."""
        try:
            message_json = json.dumps(update)
            
            def delivery_callback(err, msg):
                if err:
                    print(f"✗ Failed to publish message: {err}")
                else:
                    print(f"  ✓ Published to Kafka: {msg.topic()}[{msg.partition()}] @ {msg.offset()}")
            
            self.kafka_producer.produce(
                self.kafka_topic,
                value=message_json,
                callback=delivery_callback
            )
            
            # Wait for delivery
            self.kafka_producer.flush(timeout=10)
            
        except Exception as e:
            print(f"✗ Error publishing to Kafka: {e}")
    
    def _continuous_rss_polling(self):
        """
        Continuously poll RSS feed every 15 minutes for new updates.
        Process new updates through the complete pipeline.
        """
        print(f"\n=== Starting Continuous RSS Polling ===")
        print(f"Polling interval: {self.polling_interval // 60} minutes")
        print(f"RSS URL: {self.rss_url}")
        print("-" * 50)
        
        last_poll_time = time.time()
        
        try:
            while True:
                current_time = time.time()
                
                # Check if it's time to poll
                if current_time - last_poll_time >= self.polling_interval:
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Polling RSS feed...")
                    
                    # Fetch RSS updates
                    rss_updates = self._fetch_rss_updates()
                    
                    new_updates_count = 0
                    
                    for update in rss_updates:
                        # Check if this is a new update (not a duplicate)
                        source = update.get('source', '')
                        title = update.get('title', '')
                        published_at = update.get('published_at', '')
                        
                        if not self._is_duplicate(source, title, published_at):
                            print(f"\n  New update detected: {title[:60]}...")
                            
                            # Publish to Kafka
                            self._publish_to_kafka(update)
                            
                            # Process immediately through pipeline
                            success = self._process_message(update)
                            
                            if success:
                                new_updates_count += 1
                                self.unique_records_inserted += 1
                        else:
                            print(f"  ⚠ Duplicate RSS entry, skipping: {title[:60]}...")
                    
                    print(f"✓ RSS polling complete. New updates processed: {new_updates_count}")
                    last_poll_time = current_time
                
                # Sleep for a short interval before checking again
                time.sleep(30)  # Check every 30 seconds if it's time to poll
                
        except KeyboardInterrupt:
            print(f"\nContinuous polling stopped by user")
        except Exception as e:
            print(f"✗ Error in continuous polling: {e}")
            raise
    
    def run(self):
        """Main execution method."""
        print("=" * 60)
        print("IMMIGRATION POLICY PROCESSOR")
        print("=" * 60)
        print(f"Kafka Topic: {self.kafka_topic}")
        print(f"BigQuery Table: {self.dataset_id}.{self.table_id}")
        print(f"Target Backfill: {self.target_backfill_count} unique records")
        print(f"RSS Polling Interval: {self.polling_interval // 60} minutes")
        print("=" * 60)
        
        try:
            # Phase 1: Historical Backfill
            if not self.backfill_complete:
                self._backfill_from_kafka()
            
            # Close the consumer used for backfill
            if self.kafka_consumer:
                self.kafka_consumer.close()
                self.kafka_consumer = None
            
            # Phase 2: Continuous RSS Polling
            print(f"\nTransitioning to continuous RSS polling mode...")
            self._continuous_rss_polling()
            
        except KeyboardInterrupt:
            print(f"\n\nShutdown requested by user")
        except Exception as e:
            print(f"\n✗ Fatal error: {e}")
            raise
        finally:
            # Cleanup
            if self.kafka_consumer:
                self.kafka_consumer.close()
            if self.kafka_producer:
                self.kafka_producer.flush()
            
            print(f"\nFinal Statistics:")
            print(f"Total unique records processed: {self.unique_records_inserted}")
            print(f"Records in deduplication cache: {len(self.processed_hashes)}")
            print("Shutdown complete.")


def main():
    """Main entry point."""
    try:
        processor = ImmigrationPolicyProcessor()
        processor.run()
    except KeyboardInterrupt:
        print("\nShutdown requested")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
