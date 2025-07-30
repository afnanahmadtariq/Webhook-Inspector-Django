"""
Comprehensive test script for Django Webhook Inspector
Tests all implemented features and API endpoints
"""

import requests
import json
import time
import uuid
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

class WebhookInspectorTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.test_webhook_uuid = None
        
    def test_user_registration(self):
        """Test user registration"""
        print("🔐 Testing User Registration...")
        
        user_data = {
            "username": f"testuser_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123"
        }
        
        try:
            response = self.session.post(f"{API_BASE}/auth/register/", json=user_data)
            if response.status_code == 201:
                print("✅ User registration successful")
                data = response.json()
                self.access_token = data.get('access_token')
                if self.access_token:
                    self.session.headers.update({'Authorization': f'Bearer {self.access_token}'})
                return True
            else:
                print(f"❌ Registration failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def test_user_login(self):
        """Test user login with admin credentials"""
        print("🔐 Testing User Login...")
        
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        try:
            response = self.session.post(f"{API_BASE}/auth/login/", json=login_data)
            if response.status_code == 200:
                print("✅ User login successful")
                data = response.json()
                self.access_token = data.get('access')
                if self.access_token:
                    self.session.headers.update({'Authorization': f'Bearer {self.access_token}'})
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_webhook_creation(self):
        """Test webhook endpoint creation"""
        print("🎯 Testing Webhook Creation...")
        
        webhook_data = {
            "name": "Test Webhook",
            "description": "Test webhook for API validation",
            "ttl_hours": 24
        }
        
        try:
            response = self.session.post(f"{API_BASE}/webhooks/endpoints/", json=webhook_data)
            if response.status_code == 201:
                print("✅ Webhook creation successful")
                data = response.json()
                print(f"   Response data: {data}")
                self.test_webhook_uuid = data.get('uuid') or data.get('id')
                if self.test_webhook_uuid:
                    print(f"   Webhook UUID: {self.test_webhook_uuid}")
                    webhook_url = data.get('url') or f"{BASE_URL}/api/v1/webhooks/capture/{self.test_webhook_uuid}/"
                    print(f"   Webhook URL: {webhook_url}")
                return True
            else:
                print(f"❌ Webhook creation failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Webhook creation error: {e}")
            return False
    
    def test_webhook_capture(self):
        """Test webhook request capture"""
        if not self.test_webhook_uuid:
            print("❌ No webhook UUID available for testing")
            return False
            
        print("📡 Testing Webhook Capture...")
        
        test_payload = {
            "event": "test_event",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "user_id": 12345,
                "action": "login",
                "metadata": {
                    "ip": "192.168.1.1",
                    "user_agent": "Test Agent"
                }
            }
        }
        
        try:
            # Test webhook capture endpoint
            response = self.session.post(
                f"{API_BASE}/webhooks/capture/{self.test_webhook_uuid}/",
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Custom-Header": "test-value",
                    "User-Agent": "WebhookTester/1.0"
                }
            )
            
            if response.status_code in [200, 201]:
                print("✅ Webhook capture successful")
                try:
                    response_data = response.json()
                    print(f"   Response: {response_data}")
                except:
                    print(f"   Response: {response.text}")
                return True
            else:
                print(f"❌ Webhook capture failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Webhook capture error: {e}")
            return False
    
    def test_webhook_requests_listing(self):
        """Test listing webhook requests"""
        if not self.test_webhook_uuid:
            print("❌ No webhook UUID available for testing")
            return False
            
        print("📋 Testing Webhook Requests Listing...")
        
        try:
            response = self.session.get(f"{API_BASE}/webhooks/requests/?endpoint_uuid={self.test_webhook_uuid}")
            if response.status_code == 200:
                print("✅ Webhook requests listing successful")
                data = response.json()
                print(f"   Found {data.get('count', 0)} requests")
                return True
            else:
                print(f"❌ Requests listing failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Requests listing error: {e}")
            return False
    
    def test_webhook_analytics(self):
        """Test webhook analytics"""
        if not self.test_webhook_uuid:
            print("❌ No webhook UUID available for testing")
            return False
            
        print("📊 Testing Webhook Analytics...")
        
        try:
            response = self.session.get(f"{API_BASE}/webhooks/analytics/?endpoint_uuid={self.test_webhook_uuid}")
            if response.status_code == 200:
                print("✅ Webhook analytics successful")
                data = response.json()
                print(f"   Analytics data: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Analytics failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Analytics error: {e}")
            return False
    
    def test_data_export(self):
        """Test data export functionality"""
        if not self.test_webhook_uuid:
            print("❌ No webhook UUID available for testing")
            return False
            
        print("📤 Testing Data Export...")
        
        try:
            # Test JSON export
            response = self.session.get(f"{API_BASE}/webhooks/requests/export/?export_format=json&endpoint_uuid={self.test_webhook_uuid}")
            if response.status_code == 200:
                print("✅ JSON export successful")
                
                # Test CSV export
                response = self.session.get(f"{API_BASE}/webhooks/requests/export/?export_format=csv&endpoint_uuid={self.test_webhook_uuid}")
                if response.status_code == 200:
                    print("✅ CSV export successful")
                    return True
                else:
                    print(f"❌ CSV export failed: {response.status_code}")
                    return False
            else:
                print(f"❌ JSON export failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Export error: {e}")
            return False
    
    def test_user_profile(self):
        """Test user profile endpoints"""
        print("👤 Testing User Profile...")
        
        try:
            response = self.session.get(f"{API_BASE}/auth/profile/")
            if response.status_code == 200:
                print("✅ User profile retrieval successful")
                data = response.json()
                print(f"   Username: {data.get('username')}")
                return True
            else:
                print(f"❌ Profile retrieval failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Profile error: {e}")
            return False
    
    def test_api_key_generation(self):
        """Test API key generation"""
        print("🔑 Testing API Key Generation...")
        
        try:
            response = self.session.post(f"{API_BASE}/auth/profile/api-key/")
            if response.status_code == 201 or response.status_code == 200:
                print("✅ API key generation successful")
                data = response.json()
                print(f"   API Key: {data.get('api_key', 'Not found')}")
                return True
            else:
                print(f"❌ API key generation failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ API key error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Comprehensive Webhook Inspector Tests")
        print("=" * 60)
        
        tests = [
            ("User Login", self.test_user_login),
            ("Webhook Creation", self.test_webhook_creation),
            ("Webhook Capture", self.test_webhook_capture),
            ("Webhook Requests Listing", self.test_webhook_requests_listing),
            ("Webhook Analytics", self.test_webhook_analytics),
            ("Data Export", self.test_data_export),
            ("User Profile", self.test_user_profile),
            ("API Key Generation", self.test_api_key_generation),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            print("-" * 40)
            if test_func():
                passed += 1
            time.sleep(1)  # Small delay between tests
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Webhook Inspector is working correctly!")
        else:
            print(f"⚠️  {total - passed} test(s) failed. Check the output above for details.")
        
        return passed == total

if __name__ == "__main__":
    tester = WebhookInspectorTester()
    tester.run_all_tests()
