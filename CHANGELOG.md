# Changelog

All notable changes to the AWS Website Quick Deployer will be documented in this file.

## [2.0.0] - 2025-8-15

### 🚀 Major Release - Production Grade Architecture

#### ✨ New Features

- **Modular Architecture**: Complete restructure with separate service managers
- **Production CLI**: Rich terminal UI with `deploy_production.py` using Click and Rich
- **Configuration Management**: Environment-based configs with JSON validation
- **Infrastructure as Code**: AWS CDK templates for reproducible deployments
- **Comprehensive Testing**: Unit tests with pytest, coverage, and security scanning
- **Enhanced Security**: Input validation, secret detection, secure defaults
- **Monitoring Ready**: CloudWatch dashboard templates and structured logging
- **State Management**: Enhanced state tracking with environment separation

#### 🔧 Technical Improvements

- **Service Managers**: Route53Manager, S3Manager, ACMManager, CloudFrontManager
- **Error Handling**: Exponential backoff retries with configurable limits
- **Validation System**: Domain, file, AWS permission, and security validation
- **Rich CLI**: Progress bars, colored output, tables, and panels
- **Type Safety**: Full type hints and validation with Pydantic support

#### 📁 New File Structure
```
src/
├── deployer/              # Core deployment logic
│   ├── config.py         # Configuration management
│   ├── validators.py     # Validation & security
│   └── managers/         # AWS service managers
├── infrastructure/cdk/   # Infrastructure as Code
├── tests/               # Unit tests
└── monitoring/          # CloudWatch templates
```

#### 🛠️ Enhanced CLI Commands

- `deploy_production.py init domain` - Initialize configuration
- `deploy_production.py phase1 domain` - Route53 setup with validation
- `deploy_production.py phase2 domain` - Full deployment with checks
- `deploy_production.py status domain` - Rich status display

#### 🔒 Security Enhancements

- Pre-deployment security scanning
- Secret detection in files and environment
- Input validation for all user inputs
- AWS permission verification before deployment
- Secure file upload validation

#### 📊 Monitoring & Observability

- CloudWatch dashboard templates
- Structured logging with timestamps
- Resource tagging for cost tracking
- Deployment state visibility
- Performance metrics tracking

#### 🧪 Testing & Quality

- Unit tests for all validators and core logic
- Security scanning with Bandit
- Code formatting with Black
- Type checking with MyPy
- Coverage reporting

### 📦 Dependencies Updated

- Upgraded boto3/botocore to latest versions
- Added development dependencies (pytest, black, mypy)
- Added rich CLI libraries (click, rich)
- Added optional CDK dependencies

### 🔄 Migration Guide

Existing users can:
1. Continue using `aws_deploy.py` (legacy mode)
2. Migrate to production CLI: `python deploy_production.py init yourdomain.com`
3. Use CDK templates for new deployments

### 🐛 Bug Fixes

- Fixed truncated HTML template in create_default_landing_page()
- Added missing shutil import
- Corrected upload_website_files method implementation
- Fixed syntax errors and validation issues

## [1.1.0] - 2025-8-15

### Added

- Default behavior now runs both phases sequentially with pause for NS configuration
- Automatic DNS propagation checking during deployment
- Interactive confirmation prompts for NS configuration
- Better user guidance during deployment process

### Changed

- Running script without flags now executes complete deployment workflow
- Improved console output with clear action requirements
- Enhanced progress indicators during deployment

## [1.0.0] - 2025-5-16

### Initial Release

#### Features

- Two-phase deployment system for flexible domain configuration
- Automatic SSL certificate provisioning via ACM
- CloudFront CDN setup with Origin Access Control (OAC)
- Intelligent resource reuse and conflict resolution
- Comprehensive state management
- Full cleanup functionality for all resources
- Cache invalidation support
- Default "Coming Soon" page when no website provided

#### Security

- Private S3 buckets with CloudFront-only access
- TLS 1.2+ enforcement
- Bucket encryption enabled by default
- Secure bucket policies with proper IAM conditions

#### Error Handling

- Automatic detection of existing resources
- Conflict resolution for DNS records
- Graceful handling of partial deployments
- State recovery from interrupted operations

#### Best Practices

- IPv6 support enabled
- HTTP/2 and HTTP/3 support
- Compression enabled for all text content
- Optimized CloudFront cache policies
- Proper resource tagging for cost tracking
