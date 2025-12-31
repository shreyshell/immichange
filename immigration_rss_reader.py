#!/usr/bin/env python3
"""
USCIS immigration RSS feed reader with Kafka publishing.
Fetches USCIS updates and publishes each as a JSON message to Confluent Cloud Kafka.
"""

import feedparser
import sys
import os
import json
from datetime import datetime
from confluent_kafka import Producer
from dotenv import load_dotenv

def delivery_report(err, msg):
    """Callback for Kafka message delivery reports."""
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

def create_kafka_producer():
    """Create and configure Kafka producer."""
    config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'PLAIN',
        'sasl.username': os.getenv('KAFKA_API_KEY'),
        'sasl.password': os.getenv('KAFKA_API_SECRET'),
        'client.id': 'uscis-rss-reader'
    }
    
    # Validate required config
    required_configs = ['bootstrap.servers', 'sasl.username', 'sasl.password']
    for key in required_configs:
        if not config[key]:
            raise ValueError(f"Missing required Kafka configuration: {key}")
    
    return Producer(config)

def publish_to_kafka(producer, topic, message_data):
    """Publish a message to Kafka topic."""
    try:
        # Convert message to JSON
        message_json = json.dumps(message_data, default=str)
        
        # Publish message
        producer.produce(
            topic,
            key=message_data.get('title', '').encode('utf-8'),
            value=message_json.encode('utf-8'),
            callback=delivery_report
        )
        
        # Trigger delivery report callbacks
        producer.poll(0)
        
    except Exception as e:
        print(f"Error publishing message to Kafka: {e}")

def main():
    # Load environment variables
    load_dotenv()
    
    # USCIS RSS feed URL
    rss_url = "https://www.uscis.gov/news/rss-feed/59144"
    kafka_topic = os.getenv('KAFKA_TOPIC', 'immigration-updates')
    
    print("Fetching USCIS immigration updates...")
    print("-" * 50)
    
    # Initialize Kafka producer
    try:
        producer = create_kafka_producer()
        print(f"Connected to Kafka. Publishing to topic: {kafka_topic}")
    except Exception as e:
        print(f"Failed to initialize Kafka producer: {e}")
        sys.exit(1)
    
    try:
        # Parse the RSS feed
        feed = feedparser.parse(rss_url)
        
        # Check if feed was parsed successfully
        if feed.bozo:
            print(f"Warning: Feed may have issues - {feed.bozo_exception}")
        
        if not feed.entries:
            print("No entries found in the RSS feed.")
            return
        
        # Get the latest 5 entries
        latest_entries = feed.entries[:5]
        
        print(f"Latest {len(latest_entries)} USCIS updates:\n")
        
        # Process and publish each entry
        published_count = 0
        
        for i, entry in enumerate(latest_entries, 1):
            title = entry.get('title', 'No title available')
            link = entry.get('link', 'No link available')
            
            # Parse published date
            published_at = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6]).isoformat()
                except:
                    published_at = entry.get('published', None)
            elif hasattr(entry, 'published'):
                published_at = entry.published
            
            # Create message data
            message_data = {
                'country': 'United States',
                'source': 'USCIS',
                'title': title,
                'link': link,
                'published_at': published_at
            }
            
            # Display update info
            print(f"{i}. {title}")
            print(f"   Published: {published_at or 'No date available'}")
            print(f"   Link: {link}")
            
            # Publish to Kafka
            try:
                publish_to_kafka(producer, kafka_topic, message_data)
                published_count += 1
                print(f"   ✓ Published to Kafka")
            except Exception as e:
                print(f"   ✗ Failed to publish to Kafka: {e}")
            
            print()
        
        # Wait for all messages to be delivered
        producer.flush()
        print(f"Successfully published {published_count}/{len(latest_entries)} messages to Kafka topic '{kafka_topic}'")
        
    except Exception as e:
        print(f"Error fetching RSS feed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()