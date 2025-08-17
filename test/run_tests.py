#!/usr/bin/env python3
"""
Simple test runner for API endpoint tests.
Run this script to test all API endpoints.
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

def main():
    """Main function to run tests."""
    print("🧪 API Endpoint Test Runner")
    print("="*50)
    
    # Check if API server is running
    if not check_api_server():
        print("❌ API server is not running on http://localhost:8010")
        print("Please start the API server first:")
        print("  python3 -m app.main")
        print("  or")
        print("  . venv/bin/activate && python3 -m app.main")
        return 1
    
    print("✅ API server is running")
    
    # Install dependencies if needed
    if not install_test_dependencies():
        return 1
    
    # Run the tests
    print("\n🚀 Running API endpoint tests...")
    try:
        from test_api_endpoints import main as run_tests
        results = run_tests()
        
        # Return appropriate exit code
        failed_tests = sum(1 for result in results.values() if not result)
        return 1 if failed_tests > 0 else 0
        
    except ImportError as e:
        print(f"❌ Failed to import test module: {e}")
        return 1
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)