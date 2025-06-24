# AWS Website Quick Deployer 🚀

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![AWS](https://img.shields.io/badge/AWS-orange.svg)
![Bash](https://img.shields.io/badge/bash-4.0+-green.svg)
![Python](https://img.shields.io/badge/python-3.6+-blue.svg)

> **Deploy static websites to AWS in under 5 minutes with SSL, CDN, and custom domain - all automated!**

A comprehensive, production-ready deployment toolkit that automates the entire process of hosting static websites on AWS. Features multiple deployment methods, interactive CLI, and complete infrastructure management.

## ✨ Features

- **🎯 One-Command Deployment** - Deploy complete websites with a single command
- **🔒 Automatic SSL** - Free, auto-renewing SSL certificates via AWS Certificate Manager
- **🌐 Global CDN** - CloudFront distribution for lightning-fast global delivery
- **📱 Custom Domains** - Full DNS management with Route53
- **🔄 Multiple Methods** - Bash scripts, Python tools, and credential-based options
- **🧹 Easy Cleanup** - Complete resource removal with confirmation safeguards
- **📊 Status Monitoring** - Real-time deployment status and health checks
- **🎨 Sample Templates** - Built-in website templates for quick testing

## 🏗️ AWS Infrastructure Created

This tool automatically provisions and configures:

| Service | Purpose | Monthly Cost (Est.) |
|---------|---------|-------------------|
| **S3 Buckets** | Website hosting + www redirect | ~$0.023/GB |
| **CloudFront** | Global CDN distribution | ~$0.085/GB + $0.0075/10k requests |
| **Route53** | DNS hosting and management | $0.50/hosted zone |
| **Certificate Manager** | SSL/TLS certificates | **FREE** |
| **IAM Roles** | Security policies and permissions | **FREE** |

**💰 Total estimated cost for small websites: $1-5/month**

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have:

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
- [jq](https://stedolan.github.io/jq/) command-line JSON processor
- A registered domain name
- Basic knowledge of AWS services

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Akramovic1/aws-website-quick-deployer.git
   cd aws-website-quick-deployer
   ```

2. **Make scripts executable:**
   ```bash
   chmod +x *.sh
   ```

3. **Run the interactive deployer:**
   ```bash
   ./main-deployer.sh
   ```

### First Deployment

The interactive menu will guide you through:

1. **Prerequisites Check** - Verify all required tools are installed
2. **Choose Deployment Method** - Select from multiple options
3. **Enter Domain Information** - Your custom domain (e.g., `example.com`)
4. **Select Website Source** - Use your files or auto-generate a sample site
5. **Deploy & Monitor** - Watch real-time deployment progress

## 📖 Usage

### Interactive CLI Menu

```
╔══════════════════════════════════════════════════════════════╗
║            AWS Static Website Deployer Control              ║
╚══════════════════════════════════════════════════════════════╝

                    Choose Your Deployment Method:

1. 🚀 Standard Deployment (Bash Script)
2. 🔑 Deploy with Credentials (Inline)
3. 🐍 Python Deployment (Full Featured)

                      Management Options:

4. 🗑️ Cleanup Resources (Standard)
5. 🔑🗑️ Cleanup with Credentials
6. 🐍🗑️ Python Cleanup
7. 🐍ℹ️ Check Deployment Status

                         Utilities:

8. ⚙️ Prerequisites Check
9. ℹ️ View Documentation
0. ✅ Exit
```

### Command Line Usage

#### Standard Deployment (Using AWS CLI Profile)
```bash
./deploy-website.sh example.com
./deploy-website.sh example.com /path/to/website/folder
```

#### Deployment with Inline Credentials
```bash
./deploy-with-credentials.sh ACCESS_KEY SECRET_KEY example.com /path/to/website us-east-1
```

#### Python Deployment (Advanced Features)
```bash
# Deploy with existing website folder
python3 aws-website-deployer.py deploy example.com --website-folder /path/to/site --region us-east-1

# Deploy with auto-generated sample site
python3 aws-website-deployer.py deploy example.com --region us-east-1

# Check deployment status
python3 aws-website-deployer.py status example.com --region us-east-1

# Cleanup all resources
python3 aws-website-deployer.py cleanup example.com --region us-east-1
```

## 🛠️ Deployment Methods

### 1. Standard Deployment
- **Best for:** Users with AWS CLI already configured
- **Security:** Uses your existing AWS profile
- **Features:** Full automation, sample site generation

### 2. Credentials-Based Deployment
- **Best for:** CI/CD pipelines, automated environments
- **Security:** ⚠️ Credentials passed as arguments (use carefully)
- **Features:** Self-contained, no AWS CLI config needed

### 3. Python Deployment
- **Best for:** Advanced users, programmatic integration
- **Requirements:** Python 3 + boto3
- **Features:** Status monitoring, detailed logging, error handling

## 📁 Project Structure

```
aws-website-quick-deployer/
├── main-deployer.sh              # Interactive main control script
├── deploy-website.sh             # Standard bash deployment
├── deploy-with-credentials.sh    # Deployment with inline credentials
├── cleanup-website.sh            # Resource cleanup (standard)
├── cleanup-with-credentials.sh   # Cleanup with inline credentials
├── aws-website-deployer.py       # Python deployment tool
├── website-template.yaml         # CloudFormation template
└── README.md                     # This documentation
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | Target AWS region | `us-east-1` |
| `AWS_PROFILE` | AWS CLI profile to use | `default` |

### AWS Permissions Required

The tool requires the following AWS permissions:
- S3: Bucket creation, object management, static website hosting
- CloudFront: Distribution creation and management
- Route53: Hosted zone and record management
- Certificate Manager: Certificate request and validation
- IAM: Role and policy management

## 🧹 Cleanup

### Complete Resource Removal

**⚠️ WARNING: Cleanup permanently deletes ALL AWS resources for the specified domain**

```bash
# Interactive cleanup (recommended)
./main-deployer.sh
# Choose option 4, 5, or 6

# Direct cleanup
./cleanup-website.sh example.com

# Python cleanup with status
python3 aws-website-deployer.py cleanup example.com --region us-east-1
```

### Safety Features
- Double confirmation required (`DELETE` must be typed)
- Lists all resources before deletion
- Graceful handling of dependencies
- Rollback on partial failures

## 🔧 Troubleshooting

### Common Issues

**AWS CLI Not Configured**
```bash
aws configure
# Enter your Access Key ID, Secret Key, Region, and Output format
```

**Domain Already Exists in Route53**
```bash
# Check existing hosted zones
aws route53 list-hosted-zones
# Cleanup existing resources first
./cleanup-website.sh your-domain.com
```

**Python Dependencies Missing**
```bash
pip3 install boto3
```

**Permission Denied Errors**
```bash
# Make scripts executable
chmod +x *.sh
```

### Validation Checks

The tool includes comprehensive validation for:
- Domain name format
- AWS credential format
- Directory existence
- Prerequisites installation
- AWS service availability

## 🔒 Security Considerations

- **Credentials**: Never commit AWS credentials to version control
- **IAM Policies**: Tool creates minimal required permissions only
- **SSL/TLS**: Automatic HTTPS enforcement via CloudFront
- **Access Logs**: Optional S3 access logging available
- **Environment Isolation**: Separate resources per domain

## 🌟 Advanced Features

### Custom SSL Certificates
```bash
# The tool automatically requests and validates SSL certificates
# No manual intervention required for domains you control
```

### Multi-Region Deployment
```bash
# Deploy to different regions
python3 aws-website-deployer.py deploy example.com --region eu-west-1
```

### Status Monitoring
```bash
# Comprehensive status check
python3 aws-website-deployer.py status example.com --region us-east-1
```

## 📈 Monitoring & Logs

### CloudWatch Integration
- CloudFront access logs
- S3 request metrics
- Certificate renewal notifications
- Lambda edge function logs (if used)

### Health Checks
- DNS resolution verification
- SSL certificate validation
- CloudFront distribution status
- S3 bucket accessibility

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
```bash
git clone https://github.com/Akramovic1/aws-website-quick-deployer.git
cd aws-website-quick-deployer
chmod +x *.sh
```

### Testing
```bash
# Run with a test domain
./deploy-website.sh test-domain.example.com
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Support

- **Issues**: [GitHub Issues](https://github.com/Akramovic1/aws-website-quick-deployer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Akramovic1/aws-website-quick-deployer/discussions)
- **Documentation**: [Wiki](https://github.com/Akramovic1/aws-website-quick-deployer/wiki)

## 🎯 Roadmap

- [ ] Terraform deployment option
- [ ] Multi-site management dashboard
- [ ] Automated backup and restore
- [ ] Integration with popular static site generators
- [ ] Custom domain SSL for non-Route53 domains
- [ ] Blue-green deployment support

## 💡 Use Cases

### Perfect For:
- **Personal websites** and portfolios
- **Small business** landing pages
- **Documentation sites** and blogs
- **MVP applications** and prototypes
- **Marketing campaigns** and landing pages

### Not Suitable For:
- Dynamic applications requiring server-side processing
- Database-driven websites
- Applications requiring persistent sessions
- High-traffic enterprise applications

---

**🚀 Ready to deploy? Run `./main-deployer.sh` and get your website online in minutes!**

---

Made with ❤️ by [Akramovic1](https://github.com/Akramovic1) | ⭐ Star this repo if you find it useful!
