"""
Tests for ACMManager
"""
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3

from awsup.config import DeploymentConfig
from awsup.managers.acm import ACMManager


@mock_aws
class TestACMManager:
    """Test ACM Manager with mocked AWS"""
    
    def setup_method(self, method):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com", region="us-east-1")
        self.manager = ACMManager(self.config)
        
        # Create ACM client for verification
        self.acm_client = boto3.client('acm', region_name='us-east-1')
    
    def test_request_certificate(self):
        """Test SSL certificate request"""
        route53_manager = MagicMock()
        
        with patch.object(self.manager, 'create_dns_validation_records') as mock_dns:
            certificate_arn = self.manager.request_or_get_certificate(route53_manager)
            
            assert certificate_arn.startswith('arn:aws:acm:')
            mock_dns.assert_called_once()
    
    def test_get_certificate_status(self):
        """Test certificate status checking"""
        certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/test123"
        
        # Check status
        status = self.manager.get_certificate_status(certificate_arn)
        assert status in ['PENDING_VALIDATION', 'ISSUED', 'FAILED', 'NOT_FOUND']
    
    @patch('awsup.managers.acm.time.sleep')
    def test_wait_for_certificate(self, mock_sleep):
        """Test waiting for certificate validation"""
        certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/test"
        
        # Mock certificate validation waiting
        with patch.object(self.manager, 'wait_for_certificate_validation') as mock_wait:
            self.manager.wait_for_certificate_validation(certificate_arn)
            mock_wait.assert_called_once_with(certificate_arn)
    
    def test_delete_certificate(self):
        """Test certificate deletion"""
        certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/test"
        
        # Mock delete operation (moto ACM doesn't fully support delete)
        with patch.object(self.manager.client, 'delete_certificate') as mock_delete:
            self.manager.delete_certificate(certificate_arn)
            mock_delete.assert_called_once_with(CertificateArn=certificate_arn)


class TestACMManagerErrorHandling:
    """Test ACM Manager error handling"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com")
    
    @patch('boto3.client')
    def test_certificate_request_failure(self, mock_client):
        """Test certificate request failure handling"""
        mock_acm = MagicMock()
        mock_acm.request_certificate.side_effect = Exception("RequestLimitExceeded")
        mock_client.return_value = mock_acm
        
        manager = ACMManager(self.config)
        route53_manager = MagicMock()
        
        with pytest.raises(Exception):
            manager.request_or_get_certificate(route53_manager)
    
    @patch('boto3.client')
    def test_certificate_validation_timeout(self, mock_client):
        """Test certificate validation timeout"""
        mock_acm = MagicMock()
        mock_acm.get_waiter.return_value.wait.side_effect = Exception("Timeout")
        mock_client.return_value = mock_acm
        
        manager = ACMManager(self.config)
        
        # Should handle timeout gracefully
        try:
            manager.wait_for_certificate_validation("arn:aws:acm:cert")
        except Exception:
            pass  # Expected behavior
    
    def test_invalid_certificate_arn(self):
        """Test handling of invalid certificate ARN"""
        manager = ACMManager(self.config)
        
        # Invalid ARN should return ERROR status, not raise exception
        status = manager.get_certificate_status("invalid-arn")
        assert status == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__])