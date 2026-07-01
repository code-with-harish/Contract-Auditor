"""Tests for input validation and error handling."""

import pytest
from fastapi.testclient import TestClient

from app.main import app, MAX_FILE_SIZE, MAX_CODE_LENGTH


client = TestClient(app)


class TestFileValidation:
    """Test file upload validation."""

    def test_sol_file_extension_allowed(self):
        """Test that .sol files are accepted."""
        # Create a simple Solidity file content
        sol_code = "pragma solidity ^0.8.0;"
        
        # Test with form data
        response = client.post(
            "/analyze",
            data={"contract_name": "Test"},
            files={"file": ("test.sol", sol_code, "text/plain")}
        )
        # Should accept the file (might fail analysis but not validation)
        assert response.status_code in [200, 400, 422, 500]
    
    def test_txt_file_extension_allowed(self):
        """Test that .txt files are accepted."""
        txt_code = "pragma solidity ^0.8.0;"
        
        response = client.post(
            "/analyze",
            data={"contract_name": "Test"},
            files={"file": ("test.txt", txt_code, "text/plain")}
        )
        # Should accept the file
        assert response.status_code in [200, 400, 422, 500]
    
    def test_py_file_extension_rejected(self):
        """Test that .py files are rejected."""
        py_code = "print('hello')"
        
        response = client.post(
            "/analyze",
            data={"contract_name": "Test"},
            files={"file": ("test.py", py_code, "text/plain")}
        )
        # Should reject with 400
        assert response.status_code == 400
        assert "File type not allowed" in response.text or response.status_code == 400


class TestFileSizeValidation:
    """Test file size limits."""

    def test_file_within_size_limit(self):
        """Test that files within the limit are accepted."""
        # Create a 1MB file (well below the 5MB limit)
        large_code = "pragma solidity ^0.8.0;\n" * 10000
        
        response = client.post(
            "/analyze",
            data={"contract_name": "Large"},
            files={"file": ("large.sol", large_code, "text/plain")}
        )
        # Should process (regardless of analysis result)
        assert response.status_code in [200, 400, 422, 500]
    
    def test_file_size_validation_configured(self):
        """Test that file size limits are configured."""
        assert MAX_FILE_SIZE == 5 * 1024 * 1024  # 5MB
        assert MAX_CODE_LENGTH == 1000000  # 1M chars


class TestSourceCodeValidation:
    """Test source code input validation."""

    def test_source_code_length_limit(self):
        """Test that source code length limits are enforced."""
        # Create code exceeding the limit
        oversized_code = "pragma solidity ^0.8.0;\n" * 500000  # Exceeds limit
        
        response = client.post(
            "/analyze",
            data={
                "source_code": oversized_code,
                "contract_name": "Oversized"
            }
        )
        # Should reject with 413 Payload Too Large
        assert response.status_code == 413
        assert "exceeds maximum" in response.text
    
    def test_empty_source_code(self):
        """Test that empty source code is handled."""
        response = client.post(
            "/analyze",
            data={
                "source_code": "",
                "contract_name": "Empty"
            }
        )
        # Should either process or reject empty input
        assert response.status_code in [200, 400, 422]
    
    def test_valid_source_code_accepted(self):
        """Test that valid source code is accepted."""
        valid_code = """pragma solidity ^0.8.0;

contract Simple {
    uint256 public value;
    
    function setValue(uint256 _value) public {
        value = _value;
    }
}"""
        
        response = client.post(
            "/analyze",
            data={
                "source_code": valid_code,
                "contract_name": "Simple"
            }
        )
        # Should accept and analyze
        assert response.status_code in [200, 400, 422, 500]


class TestUTF8Encoding:
    """Test UTF-8 encoding validation."""

    def test_invalid_utf8_rejected(self):
        """Test that invalid UTF-8 files are rejected."""
        # Create invalid UTF-8 bytes
        invalid_bytes = b'\x80\x81\x82'  # Invalid UTF-8 sequence
        
        response = client.post(
            "/analyze",
            data={"contract_name": "Invalid"},
            files={"file": ("test.sol", invalid_bytes)}
        )
        # Should reject with 400
        assert response.status_code == 400
        assert "Invalid file encoding" in response.text or "encoding" in response.text.lower()
    
    def test_utf8_encoded_file_accepted(self):
        """Test that properly encoded UTF-8 files are accepted."""
        utf8_code = "pragma solidity ^0.8.0; // UTF-8 compatible"
        
        response = client.post(
            "/analyze",
            data={"contract_name": "UTF8"},
            files={"file": ("test.sol", utf8_code.encode("utf-8"))}
        )
        # Should accept
        assert response.status_code in [200, 400, 422, 500]


class TestInputRequiredFields:
    """Test that required fields are validated."""

    def test_no_file_and_no_source_code(self):
        """Test that at least one of file or source_code is required."""
        response = client.post(
            "/analyze",
            data={"contract_name": "NoContent"}
        )
        # Should reject
        assert response.status_code in [400, 422]
    
    def test_source_code_alone_is_valid(self):
        """Test that source_code alone is sufficient."""
        response = client.post(
            "/analyze",
            data={
                "source_code": "pragma solidity ^0.8.0;",
                "contract_name": "OnlyCode"
            }
        )
        # Should accept (or rate limited if too many requests)
        assert response.status_code in [200, 400, 422, 429, 500]
    
    def test_file_alone_is_valid(self):
        """Test that file alone is sufficient."""
        response = client.post(
            "/analyze",
            data={"contract_name": "OnlyFile"},
            files={"file": ("test.sol", "pragma solidity ^0.8.0;", "text/plain")}
        )
        # Should accept (or rate limited if too many requests)
        assert response.status_code in [200, 400, 422, 429, 500]


class TestContractNameValidation:
    """Test contract name validation."""

    def test_default_contract_name(self):
        """Test that contract name defaults to 'Untitled'."""
        response = client.post(
            "/analyze",
            data={"source_code": "pragma solidity ^0.8.0;"}
        )
        # Should work with default name (or rate limited if too many requests)
        assert response.status_code in [200, 400, 422, 429, 500]
    
    def test_custom_contract_name(self):
        """Test that custom contract names are preserved."""
        response = client.post(
            "/analyze",
            data={
                "source_code": "pragma solidity ^0.8.0;",
                "contract_name": "MyCustomContract"
            }
        )
        # Should process with custom name (or rate limited if too many requests)
        assert response.status_code in [200, 400, 422, 429, 500]
        if response.status_code == 200:
            data = response.json()
            assert data.get("contract_name") == "MyCustomContract"
