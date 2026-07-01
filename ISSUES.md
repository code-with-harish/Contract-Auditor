# GitHub Issues

These issues track improvements and bugs found in the Smart Contract Auditor project.

## Issue #1: Missing GasAnalyzer Module Breaks Test Suite
**Status:** OPEN  
**Severity:** HIGH  
**Type:** Bug

### Description
The test suite references `app.analysis.gas_analyzer.GasAnalyzer` but this module does not exist in the codebase. This causes pytest to fail during collection.

### Steps to Reproduce
1. Run `pytest tests/test_gas_analyzer.py`
2. Observe `ModuleNotFoundError: No module named 'app.analysis.gas_analyzer'`

### Expected Behavior
Tests should run and pass without import errors.

### Solution
Implement the `GasAnalyzer` class that detects gas optimization opportunities in Solidity contracts.

**Related Files:**
- [tests/test_gas_analyzer.py](tests/test_gas_analyzer.py)
- [backend/app/analysis/gas_analyzer.py](backend/app/analysis/gas_analyzer.py) (to be created)

---

## Issue #2: File Upload Error Handling
**Status:** OPEN  
**Severity:** MEDIUM  
**Type:** Bug

### Description
The `/analyze` endpoint crashes with a 500 error when uploading files with invalid UTF-8 encoding. The `content.decode("utf-8")` call is not wrapped in error handling.

### Expected Behavior
Return a clear 400 Bad Request error with a descriptive message.

### Steps to Reproduce
1. Upload a binary file or non-UTF-8 encoded file
2. Observe server error instead of validation error

### Solution
Wrap the decode call in a try/except block and return appropriate HTTP 400 error.

**Related Files:**
- [backend/app/main.py](backend/app/main.py) - `/analyze` endpoint (lines 74-78)

---

## Issue #3: Missing Input Validation
**Status:** OPEN  
**Severity:** MEDIUM  
**Type:** Feature Request

### Description
The `/analyze` endpoint lacks:
- Maximum file size validation
- File type validation
- Maximum source code length validation
- Content-type checks

This can lead to:
- Denial of service via oversized payloads
- Processing of non-Solidity files
- Memory exhaustion

### Solution
Add validation for:
- File size (recommend max 5MB)
- File extension (only .sol and .txt)
- Source code length (recommend max 1M characters)
- Proper error responses with clear messages

**Related Files:**
- [backend/app/main.py](backend/app/main.py) - All endpoints that accept code

---

## Issue #4: Source Code Privacy in API Responses
**Status:** OPEN  
**Severity:** LOW  
**Type:** Enhancement

### Description
Analysis reports currently include the full source code in API responses and in-memory storage. This is a privacy concern for sensitive contracts.

### Recommendation
- Option 1: Don't store full source code in memory (only hash or metadata)
- Option 2: Make source code storage optional via configuration
- Option 3: Implement a separate endpoint to retrieve full source code

**Related Files:**
- [backend/app/main.py](backend/app/main.py) - Report building logic
- [backend/app/db/store.py](backend/app/db/store.py) - Storage implementation

---

## Issue #5: Add Rate Limiting
**Status:** OPEN  
**Severity:** LOW  
**Type:** Feature Request

### Description
The API currently has no rate limiting, which can lead to abuse and resource exhaustion.

### Solution
Implement rate limiting using:
- `slowapi` library
- Per-IP limits (e.g., 10 requests per minute)
- Per-endpoint configuration

**Related Files:**
- [backend/app/main.py](backend/app/main.py)

---

## Issue #6: Add Request/Response Logging
**Status:** OPEN  
**Severity:** LOW  
**Type:** Feature Request

### Description
Add structured logging for audit trails and debugging.

### Solution
Implement logging for:
- Incoming requests (timestamp, endpoint, file size)
- Analysis results (findings count, processing time)
- Errors and exceptions

**Related Files:**
- [backend/app/main.py](backend/app/main.py)

---
