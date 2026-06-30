# Code Review Notes

Date: 2026-06-30

## 1) Missing gas analyzer module breaks test collection
- **Location:** [tests/test_gas_analyzer.py](tests/test_gas_analyzer.py), [backend/app/analysis/static_analyzer.py](backend/app/analysis/static_analyzer.py)
- **Issue:** The test suite imports `app.analysis.gas_analyzer`, but no such module exists in the backend package.
- **Evidence:** Running `pytest -q` fails during collection with `ModuleNotFoundError: No module named 'app.analysis.gas_analyzer'`.
- **Recommendation:** Implement the missing module or remove/update the tests to match the current analyzer architecture.

## 2) Upload handling can crash the API with a 500 error
- **Location:** [backend/app/main.py](backend/app/main.py)
- **Issue:** File uploads are decoded with `content.decode("utf-8")` without error handling. Invalid or non-UTF-8 uploads will raise an exception and break the request.
- **Recommendation:** Wrap the decode in a `try/except` block and return a clear 400-style validation error.

## 3) Report payloads store full source code in memory
- **Location:** [backend/app/main.py](backend/app/main.py), [backend/app/db/store.py](backend/app/db/store.py)
- **Issue:** Each analysis report stores the full source code string in memory, and the API returns it in the response. This can lead to unnecessary data retention and accidental exposure if the service is used with sensitive contracts.
- **Recommendation:** Consider storing only a hash or metadata by default, and make source-code persistence configurable.

## 4) No input-size or content-type validation on analysis requests
- **Location:** [backend/app/main.py](backend/app/main.py)
- **Issue:** The API accepts arbitrary file uploads and source strings without basic validation, which can open the door to oversized payloads or malformed input.
- **Recommendation:** Add limits for maximum file size and verify the uploaded content type before analysis.
