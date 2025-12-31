#!/usr/bin/env python3
"""
Test script for Vertex AI integration.
Tests the AI processing functionality before running the full consumer.
"""

import os
import json
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

def test_vertex_ai():
    """Test Vertex AI processing with sample data."""
    # Load environment variables
    load_dotenv()
    
    # Initialize Vertex AI
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
    
    if not project_id:
        print("Error: Missing GOOGLE_CLOUD_PROJECT environment variable")
        return
    
    print(f"Initializing Vertex AI...")
    print(f"Project: {project_id}")
    print(f"Location: {location}")
    
    try:
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel("gemini-1.5-flash")
        print("✓ Vertex AI initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Vertex AI: {e}")
        return
    
    # Test with sample USCIS update
    test_cases = [
        {
            "title": "DHS, DOJ Announce Rule to Bar Asylum for Aliens Who Pose Security Threats and Public Health Risks",
            "url": "https://www.uscis.gov/newsroom/alerts/dhs-doj-announce-rule-to-bar-asylum"
        },
        {
            "title": "USCIS Increases H-1B Registration Fee for Fiscal Year 2025",
            "url": "https://www.uscis.gov/newsroom/news-releases/uscis-increases-h-1b-registration-fee"
        },
        {
            "title": "New Processing Times for Form I-485 Applications",
            "url": "https://www.uscis.gov/forms/form-i-485"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Title: {test_case['title']}")
        print(f"URL: {test_case['url']}")
        
        try:
            # Create prompt
            prompt = f"""
Analyze this immigration policy update and return a JSON object with the following fields:

Title: {test_case['title']}
Source URL: {test_case['url']}

Please extract and return ONLY a valid JSON object with these exact fields:
- visa_type: The type of visa or immigration category affected (e.g., "H-1B", "Green Card", "Asylum", "Student Visa", etc.)
- type_of_change: The nature of the change (e.g., "Policy Update", "Fee Change", "Processing Update", "New Requirement", etc.)
- affected_groups: Who is impacted (e.g., "Skilled Workers", "Students", "Asylum Seekers", "All Applicants", etc.)
- severity: Impact level - must be exactly "Low", "Medium", or "High"
- summary: A concise 1-2 sentence summary of the update

Return only the JSON object, no additional text or formatting.
"""
            
            # Generate response
            response = model.generate_content(prompt)
            
            if response and response.text:
                print("Raw AI Response:")
                print(response.text)
                
                # Try to parse JSON
                try:
                    ai_data = json.loads(response.text.strip())
                    print("\n✓ Parsed JSON successfully:")
                    print(json.dumps(ai_data, indent=2))
                    
                    # Validate fields
                    required_fields = ['visa_type', 'type_of_change', 'affected_groups', 'severity', 'summary']
                    missing_fields = [field for field in required_fields if field not in ai_data]
                    
                    if missing_fields:
                        print(f"⚠ Missing fields: {missing_fields}")
                    else:
                        print("✓ All required fields present")
                    
                    # Validate severity
                    if ai_data.get('severity') not in ['Low', 'Medium', 'High']:
                        print(f"⚠ Invalid severity: {ai_data.get('severity')}")
                    else:
                        print("✓ Valid severity level")
                        
                except json.JSONDecodeError as e:
                    print(f"✗ Failed to parse JSON: {e}")
                    
            else:
                print("✗ Empty response from Vertex AI")
                
        except Exception as e:
            print(f"✗ Error processing with Vertex AI: {e}")

if __name__ == "__main__":
    test_vertex_ai()