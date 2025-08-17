"""
Performance tests for Sleep Consultation AI API endpoints.
Tests response times and basic load handling.
"""

import requests
import time
import statistics
from typing import Dict, List, Tuple

# Base URL for the API
BASE_URL = "http://localhost:8010"

class TestPerformance:
    """Performance test class for API endpoints."""
    
    def measure_endpoint_performance(self, endpoint: str, method: str = "GET", 
                                   data: dict = None, files: dict = None, 
                                   iterations: int = 5) -> Dict[str, float]:
        """Measure performance metrics for an endpoint."""
        response_times = []
        successful_requests = 0
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                if method.upper() == "GET":
                    response = requests.get(f"{BASE_URL}{endpoint}")
                elif method.upper() == "POST":
                    if files:
                        response = requests.post(f"{BASE_URL}{endpoint}", files=files)
                    else:
                        response = requests.post(f"{BASE_URL}{endpoint}", json=data)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status_code < 500:  # Count non-server-error responses as successful
                    response_times.append(response_time)
                    successful_requests += 1
                
            except Exception as e:
                print(f"Request {i+1} failed: {e}")
                continue
        
        if not response_times:
            return {
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "median_response_time": 0,
                "success_rate": 0
            }
        
        return {
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "median_response_time": statistics.median(response_times),
            "success_rate": (successful_requests / iterations) * 100
        }
    
    def test_health_endpoint_performance(self) -> Dict[str, float]:
        """Test health endpoint performance."""
        print("\n=== Testing Health Endpoint Performance ===")
        
        metrics = self.measure_endpoint_performance("/api/health", iterations=10)
        
        print(f"Average Response Time: {metrics['avg_response_time']:.3f}s")
        print(f"Min Response Time: {metrics['min_response_time']:.3f}s")
        print(f"Max Response Time: {metrics['max_response_time']:.3f}s")
        print(f"Median Response Time: {metrics['median_response_time']:.3f}s")
        print(f"Success Rate: {metrics['success_rate']:.1f}%")
        
        # Health endpoint should be fast (< 1 second)
        if metrics['avg_response_time'] < 1.0 and metrics['success_rate'] >= 90:
            print("✅ Health endpoint performance is good")
            return True
        else:
            print("❌ Health endpoint performance needs improvement")
            return False
    
    def test_statistics_endpoint_performance(self) -> Dict[str, float]:
        """Test statistics endpoint performance."""
        print("\n=== Testing Statistics Endpoint Performance ===")
        
        metrics = self.measure_endpoint_performance("/api/statistics", iterations=5)
        
        print(f"Average Response Time: {metrics['avg_response_time']:.3f}s")
        print(f"Min Response Time: {metrics['min_response_time']:.3f}s")
        print(f"Max Response Time: {metrics['max_response_time']:.3f}s")
        print(f"Median Response Time: {metrics['median_response_time']:.3f}s")
        print(f"Success Rate: {metrics['success_rate']:.1f}%")
        
        # Statistics endpoint should be reasonably fast (< 3 seconds)
        if metrics['avg_response_time'] < 3.0 and metrics['success_rate'] >= 90:
            print("✅ Statistics endpoint performance is good")
            return True
        else:
            print("❌ Statistics endpoint performance needs improvement")
            return False
    
    def test_search_endpoint_performance(self) -> Dict[str, float]:
        """Test search endpoint performance."""
        print("\n=== Testing Search Endpoint Performance ===")
        
        metrics = self.measure_endpoint_performance("/api/consultations/search", iterations=5)
        
        print(f"Average Response Time: {metrics['avg_response_time']:.3f}s")
        print(f"Min Response Time: {metrics['min_response_time']:.3f}s")
        print(f"Max Response Time: {metrics['max_response_time']:.3f}s")
        print(f"Median Response Time: {metrics['median_response_time']:.3f}s")
        print(f"Success Rate: {metrics['success_rate']:.1f}%")
        
        # Search endpoint should be reasonably fast (< 5 seconds)
        if metrics['avg_response_time'] < 5.0 and metrics['success_rate'] >= 90:
            print("✅ Search endpoint performance is good")
            return True
        else:
            print("❌ Search endpoint performance needs improvement")
            return False
    
    def test_concurrent_health_requests(self) -> bool:
        """Test concurrent requests to health endpoint."""
        print("\n=== Testing Concurrent Health Requests ===")
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        num_threads = 5
        requests_per_thread = 3
        
        def make_requests():
            thread_results = []
            for _ in range(requests_per_thread):
                start_time = time.time()
                try:
                    response = requests.get(f"{BASE_URL}/api/health", timeout=10)
                    end_time = time.time()
                    thread_results.append({
                        "success": response.status_code == 200,
                        "response_time": end_time - start_time
                    })
                except Exception as e:
                    thread_results.append({
                        "success": False,
                        "response_time": 0,
                        "error": str(e)
                    })
            results_queue.put(thread_results)
        
        # Start threads
        threads = []
        start_time = time.time()
        
        for _ in range(num_threads):
            thread = threading.Thread(target=make_requests)
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Collect results
        all_results = []
        while not results_queue.empty():
            all_results.extend(results_queue.get())
        
        successful_requests = sum(1 for r in all_results if r["success"])
        total_requests = len(all_results)
        avg_response_time = statistics.mean([r["response_time"] for r in all_results if r["success"]])
        
        print(f"Total concurrent requests: {total_requests}")
        print(f"Successful requests: {successful_requests}")
        print(f"Success rate: {(successful_requests/total_requests)*100:.1f}%")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Total test time: {total_time:.3f}s")
        
        # Should handle concurrent requests well
        if successful_requests >= total_requests * 0.8:  # 80% success rate
            print("✅ Concurrent request handling is good")
            return True
        else:
            print("❌ Concurrent request handling needs improvement")
            return False
    
    def run_all_performance_tests(self) -> Dict[str, bool]:
        """Run all performance tests."""
        print("⚡ Starting performance tests...")
        print(f"Testing API at: {BASE_URL}")
        
        results = {}
        
        # Run performance tests
        results["health_performance"] = self.test_health_endpoint_performance()
        results["statistics_performance"] = self.test_statistics_endpoint_performance()
        results["search_performance"] = self.test_search_endpoint_performance()
        results["concurrent_requests"] = self.test_concurrent_health_requests()
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print performance test results summary."""
        print("\n" + "="*60)
        print("⚡ PERFORMANCE TEST RESULTS SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<30} {status}")
        
        print("-"*60)
        print(f"Total Performance Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🚀 All performance tests passed! API is performing well.")
        else:
            print(f"\n⚠️  {total - passed} performance test(s) failed. Consider optimization.")


def main():
    """Main function to run performance tests."""
    tester = TestPerformance()
    results = tester.run_all_performance_tests()
    tester.print_summary(results)
    
    return results


if __name__ == "__main__":
    main()