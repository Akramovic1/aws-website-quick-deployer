"""
Tests for validation modules
"""
import pytest
import tempfile
from pathlib import Path
from awsup.validators import DomainValidator, FileValidator, AWSValidator


class TestDomainValidator:
    """Test domain validation"""
    
    def test_valid_domains(self):
        """Test valid domain formats"""
        valid_domains = [
            "example.com",
            "test-site.org",
            "my.domain.net",
            "sub.example.co.uk"
        ]
        
        for domain in valid_domains:
            is_valid, error = DomainValidator.validate_domain(domain)
            assert is_valid, f"Domain {domain} should be valid, got error: {error}"
    
    def test_invalid_domains(self):
        """Test invalid domain formats"""
        invalid_domains = [
            "",                    # Empty
            ".",                   # Just dot
            "a",                   # Too short
            "ab",                  # Too short
            "www.example.com",     # WWW prefix
            "example",             # No TLD
            "-example.com",        # Starts with hyphen
            "example-.com",        # Ends with hyphen
            "exam..ple.com",       # Double dots
            "localhost",           # Reserved
            "example.com.",        # Trailing dot (should be normalized)
        ]
        
        for domain in invalid_domains:
            is_valid, error = DomainValidator.validate_domain(domain)
            assert not is_valid, f"Domain {domain} should be invalid"
            assert error is not None
    
    def test_domain_normalization(self):
        """Test domain normalization"""
        test_cases = [
            ("Example.COM", "example.com"),
            ("  test.org  ", "test.org"),
            ("domain.net.", "domain.net"),
        ]
        
        for input_domain, expected in test_cases:
            normalized = DomainValidator.normalize_domain(input_domain)
            assert normalized == expected


class TestFileValidator:
    """Test file validation"""
    
    def test_validate_html_file(self):
        """Test HTML file validation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello World</h1></body>
</html>""")
            temp_file = f.name
        
        try:
            is_valid, error = FileValidator.validate_file(temp_file)
            assert is_valid, f"Valid HTML file should pass validation: {error}"
        finally:
            Path(temp_file).unlink()
    
    def test_validate_large_file(self):
        """Test large file rejection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write a file larger than 100MB (simplified test)
            f.write("x" * (101 * 1024 * 1024))  # 101MB
            temp_file = f.name
        
        try:
            is_valid, error = FileValidator.validate_file(temp_file)
            assert not is_valid
            assert "too large" in error.lower()
        finally:
            Path(temp_file).unlink()
    
    def test_validate_directory_with_index(self):
        """Test directory validation with index.html"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create index.html
            index_file = Path(temp_dir) / 'index.html'
            index_file.write_text("<!DOCTYPE html><html><body>Test</body></html>")
            
            # Create CSS file
            css_file = Path(temp_dir) / 'style.css'
            css_file.write_text("body { margin: 0; }")
            
            is_valid, error = FileValidator.validate_directory(temp_dir)
            assert is_valid, f"Valid directory should pass: {error}"
    
    def test_validate_directory_without_index(self):
        """Test directory validation without index.html"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create only CSS file, no index.html
            css_file = Path(temp_dir) / 'style.css'
            css_file.write_text("body { margin: 0; }")
            
            is_valid, error = FileValidator.validate_directory(temp_dir)
            assert not is_valid
            assert "index.html" in error


class TestAWSValidator:
    """Test AWS validation"""
    
    def test_valid_regions(self):
        """Test region validation"""
        valid_regions = ['us-east-1', 'us-west-2', 'eu-west-1']
        for region in valid_regions:
            assert AWSValidator.validate_region(region)
    
    def test_bucket_name_validation(self):
        """Test S3 bucket name validation"""
        valid_names = [
            "example.com",
            "my-bucket-123",
            "test.bucket.name"
        ]
        
        for name in valid_names:
            is_valid, error = AWSValidator.validate_bucket_name(name)
            assert is_valid, f"Bucket name {name} should be valid: {error}"
        
        invalid_names = [
            "Example.COM",         # Uppercase
            "my_bucket",           # Underscore
            ".example.com",        # Starts with dot
            "example.com.",        # Ends with dot
            "ex",                  # Too short
            "192.168.1.1",         # IP address
        ]
        
        for name in invalid_names:
            is_valid, error = AWSValidator.validate_bucket_name(name)
            assert not is_valid, f"Bucket name {name} should be invalid"


if __name__ == "__main__":
    pytest.main([__file__])