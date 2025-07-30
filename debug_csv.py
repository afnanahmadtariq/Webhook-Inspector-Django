#!/usr/bin/env python
"""Debug CSV export endpoint"""

import os
import sys
import requests
import json

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webhook_inspector.settings')

# Test script
BASE_URL = 'http://127.0.0.1:8000/api/v1'

def test_csv_debug():
    print("🔍 Debug CSV Export Test")
    print("=" * 50)
    
    # Login first
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    login_response = requests.post(f'{BASE_URL}/auth/login/', json=login_data)
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    token = login_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create webhook
    webhook_data = {
        'name': 'Debug Test Webhook',
        'description': 'Test webhook for CSV debug',
        'max_requests': 100
    }
    
    webhook_response = requests.post(f'{BASE_URL}/webhooks/endpoints/', json=webhook_data, headers=headers)
    if webhook_response.status_code != 201:
        print(f"❌ Webhook creation failed: {webhook_response.status_code}")
        return
    
    webhook_uuid = webhook_response.json()['uuid']
    print(f"✅ Created webhook: {webhook_uuid}")
    
    # Test different export formats
    formats_to_test = ['json', 'csv']
    
    for format_type in formats_to_test:
        print(f"\n🧪 Testing {format_type.upper()} export...")
        export_url = f'{BASE_URL}/webhooks/requests/export/?format={format_type}&endpoint_uuid={webhook_uuid}'
        print(f"URL: {export_url}")
        
        try:
            export_response = requests.get(export_url, headers=headers)
            print(f"Status Code: {export_response.status_code}")
            print(f"Content Type: {export_response.headers.get('content-type', 'N/A')}")
            
            if export_response.status_code == 200:
                print(f"✅ {format_type.upper()} export successful")
                if format_type == 'json':
                    content = export_response.json()
                    print(f"Response keys: {list(content.keys())}")
                else:
                    content = export_response.text[:200]  # First 200 chars
                    print(f"Response preview: {content}")
            else:
                print(f"❌ {format_type.upper()} export failed")
                print(f"Response: {export_response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_csv_debug()
