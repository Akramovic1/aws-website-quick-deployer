"""
Tests for cleanup operations
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from moto import mock_aws

from awsup.config import DeploymentConfig
from awsup.production_deployer import CompleteProductionDeployer


class TestCleanupOperations:
    """Test cleanup operations"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com", environment="test")
    
    @patch('awsup.config.AWSCredentialValidator.get_account_id')
    @patch('awsup.config.AWSCredentialValidator.validate_credentials')
    def test_cleanup_phase1(self, mock_validate_creds, mock_get_account):
        """Test Phase 1 cleanup (Route53)"""
        mock_validate_creds.return_value = True
        mock_get_account.return_value = "123456789012"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                deployer = CompleteProductionDeployer(self.config)
                
                # Set up state with Phase 1 resources
                deployer.state = {
                    'hosted_zone_id': '/hostedzone/Z123456789',
                    'ns_records': ['ns1.example.com', 'ns2.example.com'],
                    'phase1_complete': True
                }
                deployer.state_manager.save_state(deployer.state)
                
                # Mock the Route53 deletion
                with patch.object(deployer.route53_manager, 'delete_hosted_zone') as mock_delete:
                    deployer.cleanup_phase1()
                    
                    # Verify deletion was called
                    mock_delete.assert_called_once_with('/hostedzone/Z123456789')
                    
                    # Verify state was cleared
                    assert 'hosted_zone_id' not in deployer.state
                    assert 'phase1_complete' not in deployer.state
                
            finally:
                os.chdir(original_cwd)
    
    @patch('awsup.config.AWSCredentialValidator.get_account_id')
    @patch('awsup.config.AWSCredentialValidator.validate_credentials')
    def test_cleanup_phase2(self, mock_validate_creds, mock_get_account):
        """Test Phase 2 cleanup (S3, CloudFront, ACM)"""
        mock_validate_creds.return_value = True
        mock_get_account.return_value = "123456789012"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                deployer = CompleteProductionDeployer(self.config)
                
                # Set up state with Phase 2 resources
                deployer.state = {
                    'hosted_zone_id': '/hostedzone/Z123456789',
                    'certificate_arn': 'arn:aws:acm:us-east-1:123456789012:certificate/abc123',
                    'bucket_name': 'example.com',
                    'distribution_id': 'E123456789ABCDEF',
                    'phase1_complete': True,
                    'phase2_complete': True
                }
                deployer.state_manager.save_state(deployer.state)
                
                # Mock all cleanup operations
                with patch.object(deployer.cloudfront_manager, 'delete_distribution') as mock_cf_delete, \
                     patch.object(deployer.s3_manager, 'delete_bucket_and_contents') as mock_s3_delete, \
                     patch.object(deployer.acm_manager, 'delete_certificate') as mock_acm_delete:
                    
                    deployer.cleanup_phase2()
                    
                    # Verify all deletions were called
                    mock_cf_delete.assert_called_once_with('E123456789ABCDEF')
                    mock_s3_delete.assert_called_once()
                    mock_acm_delete.assert_called_once_with('arn:aws:acm:us-east-1:123456789012:certificate/abc123')
                    
                    # Verify Phase 2 state was cleared
                    assert 'certificate_arn' not in deployer.state
                    assert 'bucket_name' not in deployer.state
                    assert 'distribution_id' not in deployer.state
                    assert 'phase2_complete' not in deployer.state
                
            finally:
                os.chdir(original_cwd)
    
    @patch('awsup.config.AWSCredentialValidator.get_account_id')
    @patch('awsup.config.AWSCredentialValidator.validate_credentials')
    def test_cleanup_all(self, mock_validate_creds, mock_get_account):
        """Test complete cleanup of all resources"""
        mock_validate_creds.return_value = True
        mock_get_account.return_value = "123456789012"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                deployer = CompleteProductionDeployer(self.config)
                
                # Set up complete deployment state
                deployer.state = {
                    'hosted_zone_id': '/hostedzone/Z123456789',
                    'certificate_arn': 'arn:aws:acm:us-east-1:123456789012:certificate/abc123',
                    'bucket_name': 'example.com',
                    'distribution_id': 'E123456789ABCDEF',
                    'phase1_complete': True,
                    'phase2_complete': True,
                    'deployment_complete': True
                }
                deployer.state_manager.save_state(deployer.state)
                
                # Verify state file exists
                assert deployer.state_manager.state_file.exists()
                
                # Mock all cleanup operations
                with patch.object(deployer, 'cleanup_phase1') as mock_phase1, \
                     patch.object(deployer, 'cleanup_phase2') as mock_phase2:
                    
                    deployer.cleanup_all()
                    
                    # Verify both phases were cleaned up
                    mock_phase2.assert_called_once()
                    mock_phase1.assert_called_once()
                    
                    # Verify state file was removed
                    assert not deployer.state_manager.state_file.exists()
                
            finally:
                os.chdir(original_cwd)
    
    def test_cache_invalidation(self):
        """Test CloudFront cache invalidation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                config = DeploymentConfig(domain="example.com")
                deployer = CompleteProductionDeployer(config)
                
                # Set up state with distribution
                deployer.state = {
                    'distribution_id': 'E123456789ABCDEF',
                    'phase2_complete': True
                }
                deployer.state_manager.save_state(deployer.state)
                
                # Mock cache invalidation
                with patch.object(deployer.cloudfront_manager, 'create_invalidation') as mock_invalidate:
                    mock_invalidate.return_value = "I123456789ABCDEF"
                    
                    deployer.invalidate_cache(['/index.html', '/css/*'])
                    
                    # Verify invalidation was called with correct parameters
                    mock_invalidate.assert_called_once_with('E123456789ABCDEF', ['/index.html', '/css/*'])
                
            finally:
                os.chdir(original_cwd)
    
    def test_cleanup_without_resources(self):
        """Test cleanup when no resources exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                config = DeploymentConfig(domain="example.com")
                deployer = CompleteProductionDeployer(config)
                
                # Empty state
                deployer.state = {}
                deployer.state_manager.save_state(deployer.state)
                
                # Cleanup should handle empty state gracefully
                deployer.cleanup_phase1()  # Should not raise
                deployer.cleanup_phase2()  # Should not raise
                
            finally:
                os.chdir(original_cwd)


class TestResourceValidation:
    """Test resource validation and health checks"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com")
    
    @patch('awsup.config.AWSCredentialValidator.get_account_id')
    @patch('awsup.config.AWSCredentialValidator.validate_credentials')
    def test_resource_health_check(self, mock_validate_creds, mock_get_account):
        """Test resource health checking"""
        mock_validate_creds.return_value = True
        mock_get_account.return_value = "123456789012"
        
        deployer = CompleteProductionDeployer(self.config)
        
        # Mock resource validation
        with patch.object(deployer.route53_manager, 'validate_resource_exists') as mock_r53, \
             patch.object(deployer.s3_manager, 'validate_resource_exists') as mock_s3, \
             patch.object(deployer.acm_manager, 'validate_resource_exists') as mock_acm, \
             patch.object(deployer.cloudfront_manager, 'validate_resource_exists') as mock_cf:
            
            mock_r53.return_value = True
            mock_s3.return_value = True
            mock_acm.return_value = True
            mock_cf.return_value = True
            
            # Set up state with resources
            deployer.state = {
                'hosted_zone_id': '/hostedzone/Z123456789',
                'bucket_name': 'example.com',
                'certificate_arn': 'arn:aws:acm:cert',
                'distribution_id': 'E123456789'
            }
            
            # Test status display (should not raise exceptions)
            summary = deployer.show_detailed_status()
            assert summary is not None


if __name__ == "__main__":
    pytest.main([__file__])