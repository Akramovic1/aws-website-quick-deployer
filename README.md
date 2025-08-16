# AWS Website Quick Deployer

A production-grade Python toolkit for deploying static websites to AWS using S3, CloudFront, Route53, and ACM. Now featuring modular architecture, comprehensive validation, and Infrastructure as Code support.

## 🆕 Version 2.0 - Production Grade

### New Features
- **Modular Architecture** - Separated concerns with dedicated service managers
- **Configuration Management** - Environment-based configs with validation
- **Enhanced Security** - Input validation, secret detection, secure defaults
- **Infrastructure as Code** - AWS CDK templates included
- **Rich CLI Experience** - Beautiful terminal UI with progress indicators
- **Comprehensive Testing** - Unit tests with pytest framework
- **Monitoring Ready** - CloudWatch dashboard templates

## 🚀 Quick Start

### Production Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize configuration
python deploy_production.py init yourdomain.com --region us-east-1

# Deploy with validation and monitoring
python deploy_production.py phase1 yourdomain.com
python deploy_production.py phase2 yourdomain.com --website-path ./dist

# OR: Complete deployment in one command
python deploy_production.py deploy yourdomain.com --website-path ./dist

# Check status
python deploy_production.py status yourdomain.com
```

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Route53       │    │   ACM           │    │   CloudFront    │
│   DNS Records   │───▶│   SSL Cert      │───▶│   CDN           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │   S3 Bucket     │
                                              │   Static Files  │
                                              └─────────────────┘
```

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Python 3.8+** installed  
3. **AWS CLI** configured with credentials
4. **Domain name** (registered with any registrar)

### Required AWS Permissions

Create an IAM policy with these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:*",
        "s3:*", 
        "cloudfront:*",
        "acm:*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Installation

### Production Setup
```bash
git clone https://github.com/Akramovic1/aws-website-quick-deployer.git
cd aws-website-quick-deployer
pip install -r requirements.txt
```

### Quick Setup
```bash
# Clone and install
git clone https://github.com/Akramovic1/aws-website-quick-deployer.git
cd aws-website-quick-deployer
pip install boto3 botocore rich click
```

## Quick Start

### Default Behavior (Recommended)

Simply run the script with your domain name - it will handle both phases with a pause for NS configuration:

```bash
# Run complete deployment with automatic pause for NS configuration
python aws_deploy.py yourdomain.com

# With website files
python aws_deploy.py yourdomain.com --website-path ./dist

# Without website files (uses default Coming Soon page)
python aws_deploy.py yourdomain.com
```

The script will:
1. Create Route53 hosted zone
2. Display NS records
3. **Wait for you to configure nameservers at your registrar**
4. Continue with full deployment after confirmation
5. Deploy your website or default Coming Soon page

## Usage Guide

### Method 1: Automatic Two-Phase Deployment (Default)

```bash
python aws_deploy.py yourdomain.com
```

This will:
- Run Phase 1 (Route53 setup)
- Display NS records for you to configure
- **Pause and wait for your confirmation**
- Run Phase 2 (complete deployment)

### Method 2: Manual Phase Control

#### Phase 1: Setup Route53 (Get NS Records)

```bash
python aws_deploy.py yourdomain.com --phase1
```

**Example output:**
```
============================================================
IMPORTANT: Configure your domain registrar
============================================================

Domain: yourdomain.com

Nameservers to configure at your registrar (e.g., GoDaddy):

  NS1: ns-123.awsdns-12.com
  NS2: ns-456.awsdns-34.net
  NS3: ns-789.awsdns-56.org
  NS4: ns-012.awsdns-78.co.uk

============================================================
Copy these nameservers to your domain registrar's DNS settings
Wait 5-30 minutes for DNS propagation before running Phase 2
============================================================
```

#### Configure Domain Registrar

1. Log into your domain registrar (GoDaddy, Namecheap, etc.)
2. Go to DNS settings for your domain
3. Change nameservers from default to custom
4. Enter the 4 NS records provided by the script
5. Save changes and wait 5-30 minutes for propagation

#### Phase 2: Complete Deployment

```bash
python aws_deploy.py yourdomain.com --phase2 --website-path ./dist
```

### Method 3: One-Command Deployment (NS Already Configured)

If NS records are already configured or you're re-deploying:

```bash
python aws_deploy.py yourdomain.com --deploy --website-path ./dist
```

## Command Options

### Deployment Commands

```bash
# DEFAULT: Run both phases with pause for NS configuration
python aws_deploy.py yourdomain.com
python aws_deploy.py yourdomain.com --website-path ./website

# Phase 1 only - Get NS records
python aws_deploy.py yourdomain.com --phase1

# Phase 2 only - Complete deployment
python aws_deploy.py yourdomain.com --phase2 --website-path ./website

# Both phases without pause (if NS already configured)
python aws_deploy.py yourdomain.com --deploy --website-path ./website

# Deploy without uploading files (uses default Coming Soon page)
python aws_deploy.py yourdomain.com --phase2
```

### Cleanup Commands

```bash
# Remove Phase 1 resources (Route53 hosted zone)
python aws_deploy.py yourdomain.com --cleanup-phase1

# Remove Phase 2 resources (S3, CloudFront, ACM)
python aws_deploy.py yourdomain.com --cleanup-phase2

# Remove all resources
python aws_deploy.py yourdomain.com --cleanup-all
```

### Utility Commands

```bash
# Invalidate CloudFront cache
python aws_deploy.py yourdomain.com --invalidate-cache

# Show current deployment state
python aws_deploy.py yourdomain.com --show-state

# Specify AWS region (default: us-east-1)
python aws_deploy.py yourdomain.com --region us-west-2
```

## Website File Structure

Your website files should be organized like:

```
website/
├── index.html          # Required - default page
├── 404.html           # Optional - error page
├── css/
│   └── styles.css
├── js/
│   └── script.js
├── images/
│   └── logo.png
└── favicon.ico
```

## Default Coming Soon Page

If no website files are provided, the script automatically deploys a professional "Coming Soon" landing page featuring:
- Responsive modern design
- Animated gradient background
- Progress indicator
- Email collection form
- Social media links
- Mobile-optimized layout

To customize the default page, place `default-index.html` in the same directory as the script.

## State Management

The script maintains state in a hidden JSON file (`.yourdomain.com_deployment_state.json`) to track:
- Hosted Zone ID
- NS Records
- Certificate ARN
- S3 Bucket Name
- CloudFront Distribution ID
- Distribution Domain

This allows the script to:
- Resume interrupted deployments
- Reuse existing resources
- Perform intelligent updates
- Clean up resources properly

## Error Handling

The script includes comprehensive error handling for:

- **Existing Resources**: Automatically detects and reuses existing resources
- **Conflicting Records**: Removes conflicting DNS records automatically
- **Certificate Validation**: Handles DNS validation with automatic record creation
- **Bucket Naming**: Handles bucket name conflicts
- **CloudFront State**: Properly disables distributions before deletion
- **Partial Deployments**: Can resume from any point using state file

## Best Practices Implemented

1. **Security**
   - S3 buckets are private (no public access)
   - CloudFront uses Origin Access Control (OAC)
   - TLS 1.2+ enforced
   - Bucket encryption enabled

2. **Performance**
   - CloudFront CDN for global distribution
   - HTTP/2 and HTTP/3 support
   - Compression enabled
   - Optimized cache policies

3. **Reliability**
   - Versioning enabled on S3 buckets
   - Custom error pages configured
   - IPv6 support enabled

4. **Cost Optimization**
   - Reuses existing resources
   - Proper resource tagging
   - Efficient CloudFront price class

## Troubleshooting

### Common Issues

**DNS Not Resolving**
- Ensure NS records are correctly configured at registrar
- Wait up to 48 hours for full propagation
- Use `nslookup` or `dig` to verify: `dig yourdomain.com NS`

**Access Denied Errors**
- Check S3 bucket policy has correct account ID and distribution ID
- Ensure CloudFront OAC is properly configured
- Verify bucket name matches domain exactly

**Certificate Validation Failed**
- Check DNS validation records were created
- Ensure Route53 hosted zone is authoritative
- May take up to 30 minutes for validation

**CloudFront Not Updating**
- Create cache invalidation: `python aws_deploy.py yourdomain.com --invalidate-cache`
- Wait 15-20 minutes for distribution changes to deploy

### Verification Steps

After deployment, verify:

1. **HTTPS Access**: `https://yourdomain.com`
2. **WWW Redirect**: `https://www.yourdomain.com`
3. **SSL Certificate**: Check browser padlock icon
4. **CloudFront Cache**: Check response headers for `x-cache: Hit from CloudFront`

## Cost Estimates

Monthly costs (approximate):
- **Route53**: $0.50 per hosted zone + $0.40 per million queries
- **S3**: ~$0.023 per GB stored + $0.0004 per 1,000 requests
- **CloudFront**: ~$0.085 per GB transferred (varies by region)
- **ACM**: Free for certificates used with CloudFront

For a small website (<1GB, <100GB transfer/month): **~$5-10/month**

## Advanced Configuration

### Custom Error Pages

The script automatically configures:
- 404 errors → `/404.html` (if exists)
- 403 errors → `/index.html` (for SPA routing)

### Cache Invalidation

To update content immediately:
```bash
python aws_deploy.py yourdomain.com --invalidate-cache
```

### Multiple Environments

For staging/production:
```bash
# Staging
python aws_deploy.py staging.yourdomain.com --website-path ./dist-staging

# Production
python aws_deploy.py yourdomain.com --website-path ./dist-production
```

## Security Considerations

1. **AWS Credentials**: Never commit AWS credentials. Use AWS CLI configuration or environment variables
2. **State Files**: Add `.*_deployment_state.json` to `.gitignore`
3. **Bucket Policies**: Script automatically configures secure policies
4. **HTTPS Only**: HTTP automatically redirects to HTTPS

## 🏗️ Production Features

### Modular Architecture
```
src/
├── deployer/
│   ├── config.py          # Configuration management
│   ├── validators.py      # Input & security validation
│   └── managers/          # AWS service managers
│       ├── route53.py     # DNS operations
│       ├── s3.py          # Storage operations  
│       ├── acm.py         # Certificate operations
│       └── cloudfront.py  # CDN operations
├── infrastructure/cdk/    # Infrastructure as Code
└── tests/                 # Unit tests
```

### Configuration Management
Create environment-specific configurations:
```bash
# Development
python deploy_production.py init dev.yourdomain.com --environment dev

# Production  
python deploy_production.py init yourdomain.com --environment prod
```

### Infrastructure as Code
Deploy using AWS CDK for reproducible infrastructure:
```bash
cd src/infrastructure/cdk
cdk deploy WebsiteStack --context domain=yourdomain.com
```

### Security Features
- **Input validation** for domains, files, and configurations
- **Secret detection** in files and environment variables
- **Secure defaults** with minimal privileges
- **Security scanning** of uploaded content

### Monitoring & Observability
- **CloudWatch dashboards** for traffic and performance metrics
- **Structured logging** with rich terminal output
- **Resource tagging** for cost tracking and management
- **State tracking** for deployment visibility

## 🧪 Testing

### Quick Test Run
```bash
# Install dependencies and run tests
pip install -r requirements.txt
python -m pytest tests/ -v
```

### Comprehensive Testing
```bash
# Run all tests with coverage
make test-cov

# Run specific test types
make test-unit           # Unit tests only
make test-security       # Security tests + bandit scan

# Code quality checks
make lint               # Linting with flake8 and mypy
make format             # Format code with black and isort
make security           # Security scanning with bandit
```

### Using Makefile
```bash
# See all available commands
make help

# Development setup
make dev-setup

# Quick development testing
make dev-test

# Full validation
make validate test lint security
```

### Test Results
All tests should pass:
```
============================= test session starts =============================
collected 9 items

tests/test_validators.py::TestDomainValidator::test_valid_domains PASSED
tests/test_validators.py::TestDomainValidator::test_invalid_domains PASSED  
tests/test_validators.py::TestDomainValidator::test_domain_normalization PASSED
tests/test_validators.py::TestFileValidator::test_validate_html_file PASSED
tests/test_validators.py::TestFileValidator::test_validate_large_file PASSED
tests/test_validators.py::TestFileValidator::test_validate_directory_with_index PASSED
tests/test_validators.py::TestFileValidator::test_validate_directory_without_index PASSED
tests/test_validators.py::TestAWSValidator::test_valid_regions PASSED
tests/test_validators.py::TestAWSValidator::test_bucket_name_validation PASSED

============================== 9 passed in 0.82s ==============================
```

## 📊 Monitoring

Deploy CloudWatch dashboard:
```bash
aws cloudwatch put-dashboard \
  --dashboard-name "Website-${DOMAIN}" \
  --dashboard-body file://monitoring/cloudwatch_dashboard.json
```

Monitor key metrics:
- **CloudFront**: Requests, errors, cache hit ratio
- **S3**: Storage usage, request counts
- **Route53**: DNS query volume
- **ACM**: Certificate status

## Support and Contributing

For issues, feature requests, or contributions:
1. Check existing issues in the GitHub repository
2. Provide detailed error messages and logs
3. Include AWS region, domain, and deployment mode
4. Use the issue templates provided

## License

MIT License - Feel free to use and modify for your needs.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.