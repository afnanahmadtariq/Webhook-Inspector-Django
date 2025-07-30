#!/usr/bin/env python
"""Test different URL parameters"""

import requests

BASE_URL = 'http://127.0.0.1:8000/api/v1'

def test_url_variations():
    # Login first
    login_data = {'username': 'admin', 'password': 'admin123'}
    login_response = requests.post(f'{BASE_URL}/auth/login/', json=login_data)
    token = login_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create webhook
    webhook_data = {'name': 'URL Test Webhook', 'description': 'Test webhook', 'max_requests': 100}
    webhook_response = requests.post(f'{BASE_URL}/webhooks/endpoints/', json=webhook_data, headers=headers)
    webhook_uuid = webhook_response.json()['uuid']
    
    # Test different URL variations
    test_urls = [
        f'{BASE_URL}/webhooks/requests/export/?format=json&endpoint_uuid={webhook_uuid}',
        f'{BASE_URL}/webhooks/requests/export/?format=csv&endpoint_uuid={webhook_uuid}',
        f'{BASE_URL}/webhooks/requests/export/?export_format=csv&endpoint_uuid={webhook_uuid}',
        f'{BASE_URL}/webhooks/requests/export/?type=csv&endpoint_uuid={webhook_uuid}',
        f'{BASE_URL}/webhooks/requests/export/?endpoint_uuid={webhook_uuid}&format=csv',
    ]
    
    for url in test_urls:
        print(f"\n🧪 Testing: {url}")
        try:
            response = requests.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == '__main__':
    test_url_variations()
