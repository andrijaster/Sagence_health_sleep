"""
Comprehensive test suite for Sleep Consultation AI API endpoints.
Tests all endpoints to ensure they are working properly.
"""

import pytest
import requests
import json
import io
import os
import time
from typing import Dict, Any
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Base URL for the API
BASE_URL = "http://localhost:8010"

class TestAPIEndpoints:
    """Test class for all API endpoints."""
    
    def __init__(self):
        self.auth_token = None
        self.consultation_id = None
        
    def create_test_pdf(self, filename: str = "test_referral.pdf") -> str:
        """Create a test PDF file for referral letter testing."""
        pdf_path = os.path.join("test", filename)
        
        # Create a simple PDF with patient information
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "REFERRAL LETTER")
        c.drawString(100, 700, "Patient Name: John Doe")
        c.drawString(100, 680, "Doctor Name: Dr. Smith")
        c.drawString(100, 660, "Referral Date: 2024-01-15")
        c.drawString(100, 640, "Referred to: Sleep Clinic")
        c.drawString(100, 620, "Referral Reason: Sleep disorders evaluation")
        c.drawString(100, 600, "Patient has been experiencing insomnia and sleep apnea symptoms.")
        c.save()
        
        return pdf_path
    
    def test_health_endpoint(self) -> bool:
        """Test the health check endpoint."""
        print("\n=== Testing Health Endpoint ===")
        
        try:
            response = requests.get(f"{BASE_URL}/api/health")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                # Validate required fields
                required_fields = ["status", "service", "version", "database_status", 
                                 "active_sessions", "total_consultations"]
                
                for field in required_fields:
                    if field not in data:
                        print(f"❌ Missing required field: {field}")
                        return False
                
                if data["status"] == "healthy":
                    print("✅ Health endpoint working correctly")
                    return True
                else:
                    print(f"❌ Service status is not healthy: {data['status']}")
                    return False
            else:
                print(f"❌ Health endpoint failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Health endpoint test failed: {str(e)}")
            return False
    
    def test_referral_letter_endpoint(self) -> bool:
        """Test the referral letter upload endpoint."""
        print("\n=== Testing Referral Letter Endpoint ===")
        
        try:
            # Create test PDF
            pdf_path = self.create_test_pdf()
            
            # Test with valid PDF
            with open(pdf_path, 'rb') as f:
                files = {'file': ('test_referral.pdf', f, 'application/pdf')}
                response = requests.post(f"{BASE_URL}/api/referral-letter", files=files)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data.get("success") and data.get("auth_token"):
                    self.auth_token = data["auth_token"]
                    print(f"✅ Referral letter upload successful. Auth token: {self.auth_token}")
                    
                    # Clean up test file
                    os.remove(pdf_path)
                    return True
                else:
                    print(f"❌ Referral letter upload failed: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Referral letter endpoint failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Referral letter endpoint test failed: {str(e)}")
            return False
    
    def test_referral_letter_invalid_file(self) -> bool:
        """Test referral letter endpoint with invalid file."""
        print("\n=== Testing Referral Letter with Invalid File ===")
        
        try:
            # Create a text file instead of PDF
            test_content = b"This is not a PDF file"
            files = {'file': ('test.txt', io.BytesIO(test_content), 'text/plain')}
            
            response = requests.post(f"{BASE_URL}/api/referral-letter", files=files)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 400:
                print("✅ Correctly rejected non-PDF file")
                return True
            else:
                print(f"❌ Should have rejected non-PDF file but got status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Invalid file test failed: {str(e)}")
            return False
    
    def test_chat_endpoint_initial(self) -> bool:
        """Test the chat endpoint with initial message."""
        print("\n=== Testing Chat Endpoint (Initial) ===")
        
        if not self.auth_token:
            print("❌ No auth token available for chat test")
            return False
        
        try:
            payload = {
                "auth_token": self.auth_token,
                "message": "Hello, I'm having trouble sleeping."
            }
            
            response = requests.post(f"{BASE_URL}/api/chat", json=payload)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data.get("success") and data.get("bot_response"):
                    print("✅ Chat endpoint working correctly")
                    return True
                else:
                    print(f"❌ Chat failed: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Chat endpoint failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Chat endpoint test failed: {str(e)}")
            return False
    
    def test_chat_endpoint_invalid_token(self) -> bool:
        """Test chat endpoint with invalid auth token."""
        print("\n=== Testing Chat Endpoint with Invalid Token ===")
        
        try:
            payload = {
                "auth_token": "invalid_token_12345",
                "message": "Hello"
            }
            
            response = requests.post(f"{BASE_URL}/api/chat", json=payload)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 401:
                print("✅ Correctly rejected invalid auth token")
                return True
            else:
                print(f"❌ Should have rejected invalid token but got status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Invalid token test failed: {str(e)}")
            return False
    
    def test_consultations_search_endpoint(self) -> bool:
        """Test the consultations search endpoint."""
        print("\n=== Testing Consultations Search Endpoint ===")
        
        try:
            # Test basic search
            response = requests.get(f"{BASE_URL}/api/consultations/search")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data.get("success") is not False:  # Allow True or None
                    print("✅ Consultations search endpoint working")
                    
                    # Store consultation ID if available
                    if data.get("consultations") and len(data["consultations"]) > 0:
                        self.consultation_id = data["consultations"][0].get("id")
                    
                    return True
                else:
                    print(f"❌ Consultations search failed: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Consultations search failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Consultations search test failed: {str(e)}")
            return False
    
    def test_consultations_search_with_params(self) -> bool:
        """Test consultations search with parameters."""
        print("\n=== Testing Consultations Search with Parameters ===")
        
        try:
            params = {
                "patient_name": "John",
                "sort_by": "started_at",
                "sort_order": "desc"
            }
            
            response = requests.get(f"{BASE_URL}/api/consultations/search", params=params)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                print("✅ Consultations search with parameters working")
                return True
            else:
                print(f"❌ Consultations search with params failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Consultations search with params test failed: {str(e)}")
            return False
    
    def test_consultation_details_endpoint(self) -> bool:
        """Test the consultation details endpoint."""
        print("\n=== Testing Consultation Details Endpoint ===")
        
        # Try with a test consultation ID
        test_consultation_id = self.consultation_id or 1
        
        try:
            response = requests.get(f"{BASE_URL}/api/consultations/{test_consultation_id}")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                print("✅ Consultation details endpoint working")
                return True
            elif response.status_code == 404:
                print("✅ Consultation details endpoint correctly returns 404 for non-existent consultation")
                return True
            else:
                print(f"❌ Consultation details failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Consultation details test failed: {str(e)}")
            return False
    
    def test_statistics_endpoint(self) -> bool:
        """Test the statistics endpoint."""
        print("\n=== Testing Statistics Endpoint ===")
        
        try:
            response = requests.get(f"{BASE_URL}/api/statistics")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data.get("success"):
                    print("✅ Statistics endpoint working correctly")
                    return True
                else:
                    print(f"❌ Statistics failed: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Statistics endpoint failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Statistics endpoint test failed: {str(e)}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all endpoint tests and return results."""
        print("🚀 Starting comprehensive API endpoint tests...")
        print(f"Testing API at: {BASE_URL}")
        
        results = {}
        
        # Test all endpoints
        results["health"] = self.test_health_endpoint()
        results["referral_letter"] = self.test_referral_letter_endpoint()
        results["referral_letter_invalid"] = self.test_referral_letter_invalid_file()
        results["chat_initial"] = self.test_chat_endpoint_initial()
        results["chat_invalid_token"] = self.test_chat_endpoint_invalid_token()
        results["consultations_search"] = self.test_consultations_search_endpoint()
        results["consultations_search_params"] = self.test_consultations_search_with_params()
        results["consultation_details"] = self.test_consultation_details_endpoint()
        results["statistics"] = self.test_statistics_endpoint()
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test results summary."""
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<30} {status}")
        
        print("-"*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All tests passed! API is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Please check the API.")


def main():
    """Main function to run all tests."""
    tester = TestAPIEndpoints()
    results = tester.run_all_tests()
    tester.print_summary(results)
    
    return results


if __name__ == "__main__":
    main()