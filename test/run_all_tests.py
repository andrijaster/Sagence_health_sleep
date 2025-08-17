#!/usr/bin/env python3
"""
Comprehensive test runner for all API tests.
Runs both main endpoint tests and edge case tests.
"""

import sys
import os
import subprocess
import time

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_api_server():
    """Check if the API server is running."""
    import requests
    try:
        response = requests.get("http://localhost:8010/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def install_test_dependencies():
    """Install test dependencies."""
    print("📦 Installing test dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "test/requirements_test.txt"
        ], check=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        print("✅ Test dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install test dependencies")
        return False

def run_main_tests():
    """Run the main endpoint tests."""
    print("\n" + "="*60)
    print("🚀 RUNNING MAIN ENDPOINT TESTS")
    print("="*60)
    
    try:
        from test_api_endpoints import main as run_main_tests
        return run_main_tests()
    except ImportError as e:
        print(f"❌ Failed to import main test module: {e}")
        return {}
    except Exception as e:
        print(f"❌ Main test execution failed: {e}")
        return {}

def run_edge_case_tests():
    """Run the edge case tests."""
    print("\n" + "="*60)
    print("🔍 RUNNING EDGE CASE TESTS")
    print("="*60)
    
    try:
        from test_edge_cases import main as run_edge_tests
        return run_edge_tests()
    except ImportError as e:
        print(f"❌ Failed to import edge case test module: {e}")
        return {}
    except Exception as e:
        print(f"❌ Edge case test execution failed: {e}")
        return {}

def run_performance_tests():
    """Run the performance tests."""
    print("\n" + "="*60)
    print("⚡ RUNNING PERFORMANCE TESTS")
    print("="*60)
    
    try:
        from test_performance import main as run_perf_tests
        return run_perf_tests()
    except ImportError as e:
        print(f"❌ Failed to import performance test module: {e}")
        return {}
    except Exception as e:
        print(f"❌ Performance test execution failed: {e}")
        return {}

def print_combined_summary(main_results, edge_results, perf_results):
    """Print combined test results summary."""
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print("="*80)
    
    print("\n🚀 Main Endpoint Tests:")
    print("-" * 40)
    main_passed = sum(1 for result in main_results.values() if result)
    main_total = len(main_results)
    
    for test_name, result in main_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name.replace('_', ' ').title():<30} {status}")
    
    print(f"\n  Main Tests: {main_passed}/{main_total} passed ({(main_passed/main_total)*100:.1f}%)")
    
    print("\n🔍 Edge Case Tests:")
    print("-" * 40)
    edge_passed = sum(1 for result in edge_results.values() if result)
    edge_total = len(edge_results)
    
    for test_name, result in edge_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name.replace('_', ' ').title():<30} {status}")
    
    print(f"\n  Edge Case Tests: {edge_passed}/{edge_total} passed ({(edge_passed/edge_total)*100:.1f}%)")
    
    print("\n⚡ Performance Tests:")
    print("-" * 40)
    perf_passed = sum(1 for result in perf_results.values() if result)
    perf_total = len(perf_results)
    
    for test_name, result in perf_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name.replace('_', ' ').title():<30} {status}")
    
    print(f"\n  Performance Tests: {perf_passed}/{perf_total} passed ({(perf_passed/perf_total)*100:.1f}%)")
    
    # Overall summary
    total_passed = main_passed + edge_passed + perf_passed
    total_tests = main_total + edge_total + perf_total
    
    print("\n" + "="*80)
    print("🎯 OVERALL SUMMARY")
    print("="*80)
    print(f"Total Tests Run: {total_tests}")
    print(f"Total Passed: {total_passed}")
    print(f"Total Failed: {total_tests - total_passed}")
    print(f"Overall Success Rate: {(total_passed/total_tests)*100:.1f}%")
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("The API is working correctly, handles edge cases well, and performs efficiently.")
    elif main_passed == main_total:
        print("\n✅ All main endpoint tests passed!")
        failed_edge = edge_total - edge_passed
        failed_perf = perf_total - perf_passed
        if failed_edge > 0:
            print(f"⚠️  {failed_edge} edge case test(s) failed - consider improving error handling.")
        if failed_perf > 0:
            print(f"⚠️  {failed_perf} performance test(s) failed - consider optimization.")
    else:
        failed_main = main_total - main_passed
        failed_edge = edge_total - edge_passed
        failed_perf = perf_total - perf_passed
        print(f"\n⚠️  {failed_main} main test(s), {failed_edge} edge case test(s), and {failed_perf} performance test(s) failed.")
        print("Please check the API implementation.")
    
    return total_passed == total_tests

def main():
    """Main function to run all tests."""
    print("🧪 COMPREHENSIVE API TEST SUITE")
    print("="*80)
    print("This will run main endpoint tests, edge case tests, and performance tests")
    print("="*80)
    
    # Check if API server is running
    if not check_api_server():
        print("❌ API server is not running on http://localhost:8010")
        print("\nTo start the API server:")
        print("  . venv/bin/activate && python3 -m app.main")
        print("\nThen run this test suite again.")
        return 1
    
    print("✅ API server is running")
    
    # Install dependencies if needed
    if not install_test_dependencies():
        return 1
    
    # Run main tests
    main_results = run_main_tests()
    
    # Run edge case tests
    edge_results = run_edge_case_tests()
    
    # Run performance tests
    perf_results = run_performance_tests()
    
    # Print combined summary
    all_passed = print_combined_summary(main_results, edge_results, perf_results)
    
    # Return appropriate exit code
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)