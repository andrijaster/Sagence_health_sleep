"""
Edge case and error handling tests for Sleep Consultation AI API.
Tests specific scenarios and error conditions.
"""

import requests
import json
import io
import os
from typing import Dict, Any

# Base URL for the API
BASE_URL = "http://localhost:8010"

class TestEdgeCases:
    """Test class for edge cases and error scenarios."""
    
    def test_file_validation_edge_cases(self) -> Dict[str, bool]:
        """Test various file validation scenarios."""
        print("\n=== Testing File Validation Edge Cases ===")
        
        results = {}
        
        # Test 1: Empty file
        try:
            empty_content = b""
            files = {'file': ('empty.pdf', io.BytesIO(empty_content), 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/referral-letter", files=files)
            
            if response.status_code in [400, 422]:
                print("✅ Empty file correctly rejected")
                results["empty_file"] = True
            else:
                print(f"❌ Empty file should be rejected but got: {response.status_code}")
                results["empty_file"] = False
        except Exception as e:
            print(f"❌ Empty file test failed: {e}")
            results["empty_file"] = False
        
        # Test 2: Very large file name
        try:
            test_content = b"Not a real PDF"
            long_filename = "a" * 300 + ".pdf"
            files = {'file': (long_filename, io.BytesIO(test_content), 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/referral-letter", files=files)
            
            # Should handle gracefully (either accept or reject properly)
            if response.status_code in [200, 400, 413, 422]:
                print("✅ Long filename handled gracefully")
                results["long_filename"] = True
            else:
                print(f"❌ Long filename not handled properly: {response.status_code}")
                results["long_filename"] = False
        except Exception as e:
            print(f"❌ Long filename test failed: {e}")
            results["long_filename"] = False
        
        # Test 3: File with PDF extension but wrong content
        try:
            fake_pdf_content = b"This is not a PDF file but has .pdf extension"
            files = {'file': ('fake.pdf', io.BytesIO(fake_pdf_content), 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/referral-letter", files=files)
            
            # Should either process or reject gracefully
            if response.status_code in [200, 400, 422]:
                data = response.json()
                if not data.get("success", True):  # If it fails, that's also acceptable
                    print("✅ Fake PDF content handled gracefully")
                    results["fake_pdf"] = True
                else:
                    print("✅ Fake PDF processed (extraction may have failed gracefully)")
                    results["fake_pdf"] = True
            else:
                print(f"❌ Fake PDF not handled properly: {response.status_code}")
                results["fake_pdf"] = False
        except Exception as e:
            print(f"❌ Fake PDF test failed: {e}")
            results["fake_pdf"] = False
        
        return results
    
    def test_chat_edge_cases(self) -> Dict[str, bool]:
        """Test chat endpoint edge cases."""
        print("\n=== Testing Chat Edge Cases ===")
        
        results = {}
        
        # Test 1: Empty message
        try:
            payload = {
                "auth_token": "invalid_token",
                "message": ""
            }
            response = requests.post(f"{BASE_URL}/api/chat", json=payload)
            
            # Should handle empty message gracefully
            if response.status_code in [400, 401, 422]:
                print("✅ Empty message handled appropriately")
                results["empty_message"] = True
            else:
                print(f"❌ Empty message handling unclear: {response.status_code}")
                results["empty_message"] = False
        except Exception as e:
            print(f"❌ Empty message test failed: {e}")
            results["empty_message"] = False
        
        # Test 2: Very long message
        try:
            long_message = "A" * 10000  # 10KB message
            payload = {
                "auth_token": "invalid_token",
                "message": long_message
            }
            response = requests.post(f"{BASE_URL}/api/chat", json=payload)
            
            # Should handle long message gracefully
            if response.status_code in [400, 401, 413, 422]:
                print("✅ Long message handled appropriately")
                results["long_message"] = True
            else:
                print(f"❌ Long message handling unclear: {response.status_code}")
                results["long_message"] = False
        except Exception as e:
            print(f"❌ Long message test failed: {e}")
            results["long_message"] = False
        
        # Test 3: Special characters in message
        try:
            special_message = "Hello! 🌟 Testing with émojis and spëcial chars: <script>alert('xss')</script>"
            payload = {
                "auth_token": "invalid_token",
                "message": special_message
            }
            response = requests.post(f"{BASE_URL}/api/chat", json=payload)
            
            # Should handle special characters gracefully
            if response.status_code in [400, 401, 422]:
                print("✅ Special characters handled appropriately")
                results["special_chars"] = True
            else:
                print(f"❌ Special characters handling unclear: {response.status_code}")
                results["special_chars"] = False
        except Exception as e:
            print(f"❌ Special characters test failed: {e}")
            results["special_chars"] = False
        
        return results
    
    def test_search_edge_cases(self) -> Dict[str, bool]:
        """Test search endpoint edge cases."""
        print("\n=== Testing Search Edge Cases ===")
        
        results = {}
        
        # Test 1: Invalid date format
        try:
            params = {
                "start_date": "invalid-date",
                "end_date": "2024-12-31"
            }
            response = requests.get(f"{BASE_URL}/api/consultations/search", params=params)
            
            # Should handle invalid date gracefully
            if response.status_code in [200, 400, 422]:
                print("✅ Invalid date format handled gracefully")
                results["invalid_date"] = True
            else:
                print(f"❌ Invalid date not handled properly: {response.status_code}")
                results["invalid_date"] = False
        except Exception as e:
            print(f"❌ Invalid date test failed: {e}")
            results["invalid_date"] = False
        
        # Test 2: Invalid sort parameters
        try:
            params = {
                "sort_by": "invalid_field",
                "sort_order": "invalid_order"
            }
            response = requests.get(f"{BASE_URL}/api/consultations/search", params=params)
            
            # Should handle invalid sort parameters gracefully
            if response.status_code in [200, 400, 422]:
                print("✅ Invalid sort parameters handled gracefully")
                results["invalid_sort"] = True
            else:
                print(f"❌ Invalid sort parameters not handled properly: {response.status_code}")
                results["invalid_sort"] = False
        except Exception as e:
            print(f"❌ Invalid sort test failed: {e}")
            results["invalid_sort"] = False
        
        # Test 3: SQL injection attempt
        try:
            params = {
                "patient_name": "'; DROP TABLE consultations; --"
            }
            response = requests.get(f"{BASE_URL}/api/consultations/search", params=params)
            
            # Should handle SQL injection attempt safely
            if response.status_code in [200, 400, 422]:
                print("✅ SQL injection attempt handled safely")
                results["sql_injection"] = True
            else:
                print(f"❌ SQL injection not handled properly: {response.status_code}")
                results["sql_injection"] = False
        except Exception as e:
            print(f"❌ SQL injection test failed: {e}")
            results["sql_injection"] = False
        
        return results
    
    def test_consultation_details_edge_cases(self) -> Dict[str, bool]:
        """Test consultation details endpoint edge cases."""
        print("\n=== Testing Consultation Details Edge Cases ===")
        
        results = {}
        
        # Test 1: Non-existent consultation ID
        try:
            response = requests.get(f"{BASE_URL}/api/consultations/99999")
            
            if response.status_code == 404:
                print("✅ Non-existent consultation correctly returns 404")
                results["non_existent_id"] = True
            else:
                print(f"❌ Non-existent consultation should return 404 but got: {response.status_code}")
                results["non_existent_id"] = False
        except Exception as e:
            print(f"❌ Non-existent consultation test failed: {e}")
            results["non_existent_id"] = False
        
        # Test 2: Invalid consultation ID format
        try:
            response = requests.get(f"{BASE_URL}/api/consultations/invalid_id")
            
            if response.status_code in [400, 404, 422]:
                print("✅ Invalid consultation ID format handled appropriately")
                results["invalid_id_format"] = True
            else:
                print(f"❌ Invalid ID format not handled properly: {response.status_code}")
                results["invalid_id_format"] = False
        except Exception as e:
            print(f"❌ Invalid ID format test failed: {e}")
            results["invalid_id_format"] = False
        
        # Test 3: Negative consultation ID
        try:
            response = requests.get(f"{BASE_URL}/api/consultations/-1")
            
            if response.status_code in [400, 404, 422]:
                print("✅ Negative consultation ID handled appropriately")
                results["negative_id"] = True
            else:
                print(f"❌ Negative ID not handled properly: {response.status_code}")
                results["negative_id"] = False
        except Exception as e:
            print(f"❌ Negative ID test failed: {e}")
            results["negative_id"] = False
        
        return results
    
    def run_all_edge_case_tests(self) -> Dict[str, bool]:
        """Run all edge case tests."""
        print("🔍 Starting edge case and error handling tests...")
        print(f"Testing API at: {BASE_URL}")
        
        all_results = {}
        
        # Run all test categories
        file_results = self.test_file_validation_edge_cases()
        chat_results = self.test_chat_edge_cases()
        search_results = self.test_search_edge_cases()
        details_results = self.test_consultation_details_edge_cases()
        
        # Combine all results
        all_results.update(file_results)
        all_results.update(chat_results)
        all_results.update(search_results)
        all_results.update(details_results)
        
        return all_results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print edge case test results summary."""
        print("\n" + "="*60)
        print("🔍 EDGE CASE TEST RESULTS SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<30} {status}")
        
        print("-"*60)
        print(f"Total Edge Case Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All edge case tests passed! API handles errors well.")
        else:
            print(f"\n⚠️  {total - passed} edge case test(s) failed. Consider improving error handling.")


def main():
    """Main function to run edge case tests."""
    tester = TestEdgeCases()
    results = tester.run_all_edge_case_tests()
    tester.print_summary(results)
    
    return results


if __name__ == "__main__":
    main()