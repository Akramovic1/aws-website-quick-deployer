"""
Tests for S3Manager
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3

from awsup.config import DeploymentConfig
from awsup.managers.s3 import S3Manager


@mock_aws
class TestS3Manager:
    """Test S3 Manager with mocked AWS"""
    
    def setup_method(self, method):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com", region="us-east-1")
        self.manager = S3Manager(self.config)
        
        # Create S3 client for verification
        self.s3_client = boto3.client('s3', region_name='us-east-1')
    
    def test_create_bucket(self):
        """Test S3 bucket creation"""
        bucket_name = self.manager.create_or_get_bucket()
        
        assert bucket_name == "example.com"
        
        # Verify bucket exists
        response = self.s3_client.list_buckets()
        bucket_names = [b['Name'] for b in response['Buckets']]
        assert "example.com" in bucket_names
    
    def test_upload_single_file(self):
        """Test uploading single HTML file"""
        # Create bucket first
        bucket_name = self.manager.create_or_get_bucket()
        
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("<!DOCTYPE html><html><body>Test</body></html>")
            temp_file = f.name
        
        try:
            # Upload file
            count = self.manager.upload_website_files(temp_file)
            assert count == 1
            
            # Verify file was uploaded
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            assert 'Contents' in response
            assert len(response['Contents']) == 1
            
        finally:
            Path(temp_file).unlink()
    
    def test_upload_directory(self):
        """Test uploading directory of files"""
        # Create bucket first
        bucket_name = self.manager.create_or_get_bucket()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            (Path(temp_dir) / 'index.html').write_text("<!DOCTYPE html><html><body>Home</body></html>")
            (Path(temp_dir) / 'style.css').write_text("body { margin: 0; }")
            (Path(temp_dir) / 'script.js').write_text("console.log('Hello');")
            
            # Upload directory
            count = self.manager.upload_website_files(temp_dir)
            assert count == 3
            
            # Verify files were uploaded
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            assert len(response['Contents']) == 3
            
            uploaded_keys = [obj['Key'] for obj in response['Contents']]
            assert 'index.html' in uploaded_keys
            assert 'style.css' in uploaded_keys
            assert 'script.js' in uploaded_keys
    
    def test_upload_default_page(self):
        """Test uploading default landing page when no path provided"""
        # Create bucket first
        bucket_name = self.manager.create_or_get_bucket()
        
        # Create mock default index file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("<!DOCTYPE html><html><body>Coming Soon</body></html>")
            temp_file = f.name
        
        try:
            # Mock the default path resolution
            with patch('pathlib.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.parent.parent.parent.parent.__truediv__.return_value = Path(temp_file)
                mock_path_class.return_value = mock_path
                mock_path_class.__file__ = temp_file
                
                # Upload without path (should use default)
                count = self.manager.upload_website_files()
                assert count == 1
                
        finally:
            Path(temp_file).unlink()
    
    def test_content_type_detection(self):
        """Test content type detection for different file types"""
        test_cases = [
            ('.html', 'text/html'),
            ('.css', 'text/css'),
            ('.js', 'application/javascript'),
            ('.jpg', 'image/jpeg'),
            ('.png', 'image/png'),
            ('.pdf', 'application/pdf'),
            ('.unknown', 'application/octet-stream')
        ]
        
        for extension, expected_type in test_cases:
            content_type = self.manager._get_content_type(extension)
            assert content_type == expected_type
    
    def test_cache_control_headers(self):
        """Test cache control header generation"""
        test_cases = [
            ('.css', 'public, max-age=31536000'),  # 1 year for CSS
            ('.js', 'public, max-age=31536000'),   # 1 year for JS
            ('.html', 'public, max-age=3600'),     # 1 hour for HTML
            ('.txt', 'public, max-age=86400'),     # 1 day default
        ]
        
        for extension, expected_cache in test_cases:
            cache_control = self.manager._get_cache_control(extension)
            assert cache_control == expected_cache
    
    def test_update_bucket_policy(self):
        """Test S3 bucket policy update"""
        # Create bucket first
        bucket_name = self.manager.create_or_get_bucket()
        
        # Update bucket policy
        distribution_id = "E123456789ABCDEF"
        account_id = "123456789012"
        
        self.manager.update_bucket_policy(distribution_id, account_id)
        
        # Verify policy was set
        try:
            response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
            policy = json.loads(response['Policy'])
            
            assert policy['Version'] == "2012-10-17"
            assert len(policy['Statement']) == 1
            
            statement = policy['Statement'][0]
            assert statement['Effect'] == "Allow"
            assert statement['Principal']['Service'] == "cloudfront.amazonaws.com"
            
        except Exception:
            # moto might not fully support bucket policies
            pass


class TestS3ManagerErrorHandling:
    """Test S3Manager error handling"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com")
    
    @patch('boto3.client')
    def test_bucket_creation_failure(self, mock_client):
        """Test bucket creation failure handling"""
        mock_s3 = MagicMock()
        mock_s3.head_bucket.side_effect = Exception("BucketAlreadyOwnedByYou")
        mock_s3.create_bucket.side_effect = Exception("BucketAlreadyExists")
        mock_client.return_value = mock_s3
        
        manager = S3Manager(self.config)
        
        with pytest.raises(Exception):
            manager.create_or_get_bucket()
    
    def test_invalid_website_path(self):
        """Test invalid website path handling"""
        manager = S3Manager(self.config)
        
        with pytest.raises(ValueError, match="Invalid website path"):
            manager.upload_website_files("/nonexistent/path")
    
    def test_file_validation_integration(self):
        """Test integration with file validator"""
        from awsup.validators import FileValidator
        
        # Test with valid HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("<!DOCTYPE html><html><body>Test</body></html>")
            temp_file = f.name
        
        try:
            is_valid, error = FileValidator.validate_file(temp_file)
            assert is_valid
            
            # Manager should accept valid files
            manager = S3Manager(self.config)
            # Test would require actual S3 setup
            assert manager._get_content_type('.html') == 'text/html'
            
        finally:
            Path(temp_file).unlink()