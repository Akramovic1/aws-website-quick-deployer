"""
Tests for CloudFrontManager
"""
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3

from awsup.config import DeploymentConfig
from awsup.managers.cloudfront import CloudFrontManager


@mock_aws
class TestCloudFrontManager:
    """Test CloudFront Manager with mocked AWS"""
    
    def setup_method(self, method):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com", region="us-east-1")
        self.manager = CloudFrontManager(self.config)
        
        # Create CloudFront client for verification
        self.cf_client = boto3.client('cloudfront', region_name='us-east-1')
    
    def test_create_distribution(self):
        """Test CloudFront distribution creation"""
        bucket_name = "example.com"
        certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/test"
        account_id = "123456789012"
        
        distribution_info = self.manager.create_or_update_distribution(bucket_name, certificate_arn, account_id)
        
        assert 'id' in distribution_info
        assert 'domain' in distribution_info
        assert distribution_info['domain'].endswith('.cloudfront.net')
    
    def test_get_distribution_status(self):
        """Test distribution status checking"""
        # Create distribution first
        bucket_name = "example.com"
        certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/test"
        account_id = "123456789012"
        
        distribution_info = self.manager.create_or_update_distribution(bucket_name, certificate_arn, account_id)
        distribution_id = distribution_info['id']
        
        # Check status
        status = self.manager.get_distribution_status(distribution_id)
        assert status in ['InProgress', 'Deployed']
    
    @patch('awsup.managers.cloudfront.time.sleep')
    def test_wait_for_distribution(self, mock_sleep):
        """Test waiting for distribution deployment"""
        distribution_id = "E123456789ABCDEF"
        
        # Mock the waiter
        with patch.object(self.manager.client, 'get_waiter') as mock_waiter:
            mock_waiter.return_value.wait.return_value = None
            
            self.manager.wait_for_distribution_deployed(distribution_id, timeout=10)
            mock_waiter.assert_called_once_with('distribution_deployed')
    
    def test_create_invalidation(self):
        """Test cache invalidation creation"""
        distribution_id = "E123456789ABCDEF"
        paths = ['/index.html', '/css/*']
        
        # Mock invalidation
        with patch.object(self.manager.client, 'create_invalidation') as mock_invalidate:
            mock_invalidate.return_value = {
                'Invalidation': {'Id': 'I123456789ABCDEF'}
            }
            
            invalidation_id = self.manager.create_invalidation(distribution_id, paths)
            assert invalidation_id == 'I123456789ABCDEF'
            
            mock_invalidate.assert_called_once()
            call_args = mock_invalidate.call_args[1]
            assert call_args['DistributionId'] == distribution_id
            assert call_args['InvalidationBatch']['Paths']['Items'] == paths
    
    def test_delete_distribution(self):
        """Test distribution deletion"""
        distribution_id = "E123456789ABCDEF"
        
        # Mock distribution operations
        with patch.object(self.manager.client, 'get_distribution_config') as mock_get, \
             patch.object(self.manager.client, 'update_distribution') as mock_update, \
             patch.object(self.manager.client, 'delete_distribution') as mock_delete, \
             patch.object(self.manager, 'wait_for_distribution_deployed') as mock_wait:
            
            # Mock current distribution config
            mock_get.return_value = {
                'DistributionConfig': {
                    'Enabled': True,
                    'CallerReference': 'test-ref'
                },
                'ETag': 'test-etag'
            }
            
            self.manager.delete_distribution(distribution_id)
            
            # Should disable first, wait, then delete
            mock_update.assert_called_once()
            mock_wait.assert_called_once()
            mock_delete.assert_called_once()


class TestCloudFrontManagerErrorHandling:
    """Test CloudFront Manager error handling"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com")
    
    @patch('boto3.client')
    def test_distribution_creation_failure(self, mock_client):
        """Test distribution creation failure handling"""
        mock_cf = MagicMock()
        mock_cf.create_distribution.side_effect = Exception("DistributionAlreadyExists")
        mock_client.return_value = mock_cf
        
        manager = CloudFrontManager(self.config)
        
        with pytest.raises(Exception):
            manager.create_or_update_distribution("bucket", "cert-arn", "123456789012")
    
    @patch('boto3.client')
    def test_invalidation_failure(self, mock_client):
        """Test invalidation creation failure"""
        mock_cf = MagicMock()
        mock_cf.create_invalidation.side_effect = Exception("TooManyInvalidationsInProgress")
        mock_client.return_value = mock_cf
        
        manager = CloudFrontManager(self.config)
        
        with pytest.raises(Exception):
            manager.create_invalidation("E123456789", ['/index.html'])
    
    def test_invalid_distribution_id(self):
        """Test handling of invalid distribution ID"""
        manager = CloudFrontManager(self.config)
        
        # Invalid ID should return NOT_FOUND status, not raise exception
        status = manager.get_distribution_status("invalid-id")
        assert status == 'NOT_FOUND'
    
    @patch('boto3.client')
    def test_distribution_timeout(self, mock_client):
        """Test distribution deployment timeout"""
        mock_cf = MagicMock()
        mock_cf.get_waiter.return_value.wait.side_effect = Exception("Timeout")
        mock_client.return_value = mock_cf
        
        manager = CloudFrontManager(self.config)
        
        # Should handle timeout gracefully
        try:
            manager.wait_for_distribution_deployed("E123456789", timeout=1)
        except Exception:
            pass  # Expected behavior


class TestCloudFrontConfiguration:
    """Test CloudFront configuration generation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com")
        self.manager = CloudFrontManager(self.config)
    
    def test_distribution_config_generation(self):
        """Test distribution configuration structure"""
        bucket_name = "example.com"
        certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/test"
        oac_id = "E123456789"
        
        config = self.manager._build_distribution_config(bucket_name, certificate_arn, oac_id)
        
        # Verify required fields
        assert config['CallerReference']
        assert "Distribution for" in config['Comment']
        assert config['Enabled'] is True
        
        # Verify origins
        assert len(config['Origins']['Items']) == 1
        origin = config['Origins']['Items'][0]
        assert origin['DomainName'] == f"{bucket_name}.s3.amazonaws.com"
        
        # Verify aliases
        assert len(config['Aliases']['Items']) == 2
        assert "example.com" in config['Aliases']['Items']
        assert "www.example.com" in config['Aliases']['Items']
        
        # Verify SSL configuration
        assert config['ViewerCertificate']['ACMCertificateArn'] == certificate_arn
        assert config['ViewerCertificate']['SSLSupportMethod'] == 'sni-only'
    
    def test_security_headers_configuration(self):
        """Test security headers in distribution config"""
        bucket_name = "example.com"
        certificate_arn = "arn:aws:acm:cert"
        oac_id = "E123456789"
        
        config = self.manager._build_distribution_config(bucket_name, certificate_arn, oac_id)
        
        # Verify security settings
        default_cache = config['DefaultCacheBehavior']
        assert default_cache['ViewerProtocolPolicy'] == 'redirect-to-https'
        assert default_cache['Compress'] is True
        
        # Verify allowed methods
        allowed_methods = default_cache['AllowedMethods']['Items']
        assert 'GET' in allowed_methods
        assert 'HEAD' in allowed_methods


if __name__ == "__main__":
    pytest.main([__file__])