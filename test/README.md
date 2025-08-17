# API Endpoint Tests

This folder contains comprehensive tests for all Sleep Consultation AI API endpoints.

## Overview

The test suite validates the following endpoints:

1. **Health Check** (`GET /api/health`) - System health and status
2. **Referral Letter Upload** (`POST /api/referral-letter`) - PDF upload and processing
3. **Chat** (`POST /api/chat`) - Conversation with AI bot
4. **Consultations Search** (`GET /api/consultations/search`) - Search and filter consultations
5. **Consultation Details** (`GET /api/consultations/{id}`) - Get specific consultation details
6. **Statistics** (`GET /api/statistics`) - System statistics

## Files

- `test_api_endpoints.py` - Main test suite with comprehensive endpoint testing
- `test_edge_cases.py` - Edge case and error handling tests
- `test_performance.py` - Performance and load testing
- `run_tests.py` - Test runner script for main endpoint tests
- `run_all_tests.py` - Comprehensive test runner for all test suites
- `requirements_test.txt` - Test-specific dependencies
- `README.md` - This documentation file

## Prerequisites

1. **API Server Running**: The API server must be running on `http://localhost:8010`
2. **Virtual Environment**: Recommended to use the project's virtual environment

## Running Tests

### Method 1: Using the Comprehensive Test Runner (Recommended)

```bash
# Make sure the API server is running first
. venv/bin/activate && python3 -m app.main

# In another terminal, run ALL tests (main + edge cases + performance)
cd /path/to/project
python3 test/run_all_tests.py
```

### Method 2: Using Individual Test Runners

```bash
# Run only main endpoint tests
python3 test/run_tests.py

# Run only edge case tests
python3 test/test_edge_cases.py

# Run only performance tests
python3 test/test_performance.py
```

### Method 2: Manual Execution

```bash
# Install test dependencies
. venv/bin/activate
pip install -r test/requirements_test.txt

# Run tests directly
cd test
python3 test_api_endpoints.py
```

### Method 3: Using pytest

```bash
# Install test dependencies
. venv/bin/activate
pip install -r test/requirements_test.txt

# Run with pytest
pytest test/test_api_endpoints.py -v
```

## Test Coverage

### 1. Health Check Tests
- ✅ Basic health endpoint functionality
- ✅ Response structure validation
- ✅ Database connectivity check

### 2. Referral Letter Tests
- ✅ Valid PDF upload and processing
- ✅ Invalid file type rejection
- ✅ Auth token generation
- ✅ Patient information extraction

### 3. Chat Tests
- ✅ Initial conversation start
- ✅ Message exchange functionality
- ✅ Invalid auth token handling
- ✅ Response structure validation

### 4. Consultation Management Tests
- ✅ Search consultations (basic)
- ✅ Search with parameters (filtering, sorting)
- ✅ Consultation details retrieval
- ✅ Non-existent consultation handling

### 5. Statistics Tests
- ✅ System statistics retrieval
- ✅ Data structure validation

### 6. Edge Case Tests
- ✅ File validation edge cases (empty files, fake PDFs, long filenames)
- ✅ Chat message edge cases (empty messages, very long messages, special characters)
- ✅ Search parameter validation (invalid dates, SQL injection attempts)
- ✅ Invalid consultation ID handling

### 7. Performance Tests
- ✅ Response time measurement for all endpoints
- ✅ Concurrent request handling
- ✅ Load testing with multiple simultaneous requests
- ✅ Performance benchmarking and thresholds

## Test Output

The test suite provides detailed output including:

- Individual test results with ✅/❌ indicators
- Response data for successful tests
- Error messages for failed tests
- Summary statistics (pass/fail counts, success rate)

Example output:
```
🚀 Starting comprehensive API endpoint tests...
Testing API at: http://localhost:8010

=== Testing Health Endpoint ===
Status Code: 200
Response: {
  "status": "healthy",
  "service": "Sleep Consultation AI API",
  "version": "2.0.0",
  ...
}
✅ Health endpoint working correctly

...

📊 TEST RESULTS SUMMARY
============================================================
Health                         ✅ PASS
Referral Letter               ✅ PASS
Referral Letter Invalid       ✅ PASS
Chat Initial                  ✅ PASS
Chat Invalid Token            ✅ PASS
Consultations Search          ✅ PASS
Consultations Search Params   ✅ PASS
Consultation Details          ✅ PASS
Statistics                    ✅ PASS
------------------------------------------------------------
Total Tests: 9
Passed: 9
Failed: 0
Success Rate: 100.0%

🎉 All tests passed! API is working correctly.
```

## Troubleshooting

### Common Issues

1. **API Server Not Running**
   ```
   ❌ API server is not running on http://localhost:8010
   ```
   **Solution**: Start the API server first:
   ```bash
   . venv/bin/activate && python3 -m app.main
   ```

2. **Missing Dependencies**
   ```
   ModuleNotFoundError: No module named 'requests'
   ```
   **Solution**: Install test dependencies:
   ```bash
   pip install -r test/requirements_test.txt
   ```

3. **Permission Errors**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   **Solution**: Make sure you have write permissions in the test directory

4. **Database Connection Issues**
   ```
   database_status: "error: ..."
   ```
   **Solution**: Check database configuration and ensure the database is accessible

### Test Data

The tests create temporary files:
- Test PDF files for referral letter testing
- These are automatically cleaned up after tests complete

### Extending Tests

To add new tests:

1. Add a new test method to the `TestAPIEndpoints` class
2. Follow the naming convention: `test_<endpoint_name>_<scenario>()`
3. Add the test to the `run_all_tests()` method
4. Update the summary in this README

## Notes

- Tests are designed to be non-destructive and use temporary data
- Each test is independent and can be run separately
- The test suite validates both success and error scenarios
- Response data is logged for debugging purposes