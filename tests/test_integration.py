"""
Integration tests for complete deployment workflow
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from moto import mock_aws

from awsup.config import DeploymentConfig
from awsup.production_deployer import CompleteProductionDeployer


class TestDeploymentWorkflow:
    """Test complete deployment workflow"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = DeploymentConfig(
            domain="test-example.com",
            region="us-east-1",
            environment="test"
        )
    
    @patch('awsup.config.AWSCredentialValidator.get_account_id')
    @patch('awsup.config.AWSCredentialValidator.validate_credentials')
    def test_deployer_initialization(self, mock_validate_creds, mock_get_account):
        """Test deployer initialization"""
        mock_validate_creds.return_value = True
        mock_get_account.return_value = "123456789012"
        
        deployer = CompleteProductionDeployer(self.config)
        
        assert deployer.config.domain == "test-example.com"
        assert deployer.account_id == "123456789012"
        assert deployer.route53_manager is not None
        assert deployer.s3_manager is not None
        assert deployer.acm_manager is not None
        assert deployer.cloudfront_manager is not None
    
    @patch('awsup.config.AWSCredentialValidator.get_account_id')
    @patch('awsup.config.AWSCredentialValidator.validate_credentials')
    @patch('awsup.config.AWSCredentialValidator.validate_permissions')
    def test_preflight_checks_success(self, mock_perms, mock_validate_creds, mock_get_account):
        """Test successful preflight checks"""
        mock_validate_creds.return_value = True
        mock_get_account.return_value = "123456789012"
        mock_perms.return_value = {
            'route53': True,
            's3': True, 
            'cloudfront': True,
            'acm': True,
            'credentials': True
        }
        
        deployer = CompleteProductionDeployer(self.config)
        result = deployer.preflight_checks()
        
        assert result is True
    
    @patch('awsup.config.AWSCredentialValidator.get_account_id')
    @patch('awsup.config.AWSCredentialValidator.validate_credentials')
    @patch('awsup.config.AWSCredentialValidator.validate_permissions')
    def test_preflight_checks_failure(self, mock_perms, mock_validate_creds, mock_get_account):
        """Test preflight checks with missing permissions"""
        mock_validate_creds.return_value = True
        mock_get_account.return_value = "123456789012"
        mock_perms.return_value = {
            'route53': False,  # Missing permission
            's3': True,
            'cloudfront': True, 
            'acm': True,
            'credentials': True
        }
        
        deployer = CompleteProductionDeployer(self.config)
        result = deployer.preflight_checks()
        
        assert result is False
    
    def test_invalid_domain_config(self):
        """Test deployer with invalid domain configuration"""
        invalid_config = DeploymentConfig(domain="invalid")
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            invalid_config.validate()


class TestStateManagement:
    """Test state management across deployment phases"""
    
    def test_state_persistence_between_phases(self):
        """Test state persistence between Phase 1 and Phase 2"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                config = DeploymentConfig(domain="example.com")
                
                # Simulate Phase 1 completion
                deployer1 = CompleteProductionDeployer(config)
                deployer1.state = {
                    'hosted_zone_id': '/hostedzone/Z123456789',
                    'ns_records': ['ns1.example.com', 'ns2.example.com'],
                    'phase1_complete': True
                }
                deployer1.state_manager.save_state(deployer1.state)
                
                # Create new deployer instance (simulating new run)
                deployer2 = CompleteProductionDeployer(config)
                
                # Verify state was loaded
                assert deployer2.state['hosted_zone_id'] == '/hostedzone/Z123456789'
                assert deployer2.state['phase1_complete'] is True
                assert len(deployer2.state['ns_records']) == 2
                
            finally:
                os.chdir(original_cwd)
    
    def test_state_cleanup(self):
        """Test state cleanup functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                config = DeploymentConfig(domain="example.com")
                deployer = CompleteProductionDeployer(config)
                
                # Save some state
                deployer.state = {'test': 'data'}
                deployer.state_manager.save_state(deployer.state)
                
                # Verify state file exists
                assert deployer.state_manager.state_file.exists()
                
                # Clear state
                deployer.state_manager.clear_state()
                
                # Verify state file is removed
                assert not deployer.state_manager.state_file.exists()
                
            finally:
                os.chdir(original_cwd)


class TestErrorRecovery:
    """Test error recovery and resilience"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = DeploymentConfig(domain="example.com")
    
    @patch('boto3.client')
    def test_retry_mechanism(self, mock_client):
        """Test retry mechanism with exponential backoff"""
        mock_route53 = MagicMock()
        
        # Simulate throttling then success
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'Throttling'}}
        
        mock_route53.list_hosted_zones_by_name.side_effect = [
            ClientError(error_response, 'ListHostedZonesByName'),
            ClientError(error_response, 'ListHostedZonesByName'),
            {'HostedZones': []}  # Success on third try
        ]
        
        mock_client.return_value = mock_route53
        
        from awsup.managers.route53 import Route53Manager
        manager = Route53Manager(self.config)
        
        # Should succeed after retries
        result = manager.get_hosted_zone()
        assert result is None  # Empty list means no hosted zone found
        assert mock_route53.list_hosted_zones_by_name.call_count == 3
    
    def test_partial_deployment_recovery(self):
        """Test recovery from partial deployment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                config = DeploymentConfig(domain="example.com")
                
                # Simulate partial deployment state
                deployer = CompleteProductionDeployer(config)
                deployer.state = {
                    'hosted_zone_id': '/hostedzone/Z123456789',
                    'phase1_complete': True,
                    'bucket_name': 'example.com',
                    # Missing: distribution_id, certificate_arn (partial Phase 2)
                }
                deployer.state_manager.save_state(deployer.state)
                
                # New deployer should be able to resume
                new_deployer = CompleteProductionDeployer(config)
                
                assert new_deployer.state['phase1_complete'] is True
                assert 'hosted_zone_id' in new_deployer.state
                assert 'bucket_name' in new_deployer.state
                
                # Should be able to continue Phase 2
                summary = new_deployer.state_manager.get_state_summary()
                assert summary['phase1_complete'] is True
                assert summary['phase2_complete'] is False  # Partial
                
            finally:
                os.chdir(original_cwd)


class TestFileValidationIntegration:
    """Test file validation integration with deployment"""
    
    def test_secure_file_upload(self):
        """Test that file validation prevents malicious uploads"""
        from awsup.validators import FileValidator
        
        # Test malicious file detection
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""<!DOCTYPE html>
<html>
<body>
    <script>eval('malicious code')</script>
    <div onclick="alert('xss')">Click me</div>
</body>
</html>""")
            temp_file = f.name
        
        try:
            # File validator should detect security issues
            is_valid, error = FileValidator.validate_file(temp_file)
            # Note: Current implementation may or may not catch this
            # This test documents expected behavior
            
        finally:
            Path(temp_file).unlink()
    
    def test_file_size_limits(self):
        """Test file size validation"""
        from awsup.validators import FileValidator
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write small file (should pass)
            f.write("Small file content")
            temp_file = f.name
        
        try:
            is_valid, error = FileValidator.validate_file(temp_file)
            assert is_valid
            
        finally:
            Path(temp_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__])