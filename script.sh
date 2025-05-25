#!/bin/bash

# AWS Website Automation - File Collection Script
# This script helps you collect all the files from the conversation

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Create project directory
PROJECT_DIR="aws-website-automation"
print_status "Creating project directory: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create directories
mkdir -p websites examples

print_status "Files you need to collect from the conversation:"
echo ""
echo "CORE FILES (Required):"
echo "1. website-template.yaml - CloudFormation template"
echo "2. deploy-website.sh - Main deployment script"  
echo "3. cleanup-website.sh - Cleanup script"
echo ""
echo "OPTIONAL FILES:"
echo "4. deploy-with-credentials.sh - Direct credential wrapper"
echo "5. cleanup-with-credentials.sh - Direct credential cleanup"
echo "6. aws-website-deployer.py - Python alternative"
echo ""

# Create file collection checklist
cat > FILE_COLLECTION_CHECKLIST.md << 'EOF'
# File Collection Checklist

Copy and paste each file from the Claude conversation:

## Core Files (Required):
- [ ] `website-template.yaml` - CloudFormation infrastructure template
- [ ] `deploy-website.sh` - Main deployment script
- [ ] `cleanup-website.sh` - Cleanup script

## Optional Files:
- [ ] `deploy-with-credentials.sh` - Deploy with direct credentials
- [ ] `cleanup-with-credentials.sh` - Cleanup with direct credentials  
- [ ] `aws-website-deployer.py` - Python version

## After collecting files:
```bash
# Make scripts executable
chmod +x *.sh

# Test AWS credentials
aws sts get-caller-identity

# Deploy your first site
./deploy-website.sh example.com
```

## Example website structure:
```
websites/
├── my-site/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── another-site/
    ├── index.html
    └── assets/
```
EOF

# Create a simple example website
cat > examples/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My AWS Website</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            text-align: center;
            background: white;
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            max-width: 600px;
            margin: 2rem;
        }
        
        h1 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        p {
            font-size: 1.1rem;
            margin-bottom: 1.5rem;
            color: #666;
        }
        
        .highlight {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-weight: 600;
            display: inline-block;
            margin: 0.5rem;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }
        
        .feature {
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        
        .feature h3 {
            color: #667eea;
            margin-bottom: 0.5rem;
        }
        
        @media (max-width: 768px) {
            .container {
                margin: 1rem;
                padding: 2rem;
            }
            
            h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Website is Live!</h1>
        <p>Congratulations! Your website is now running on AWS with:</p>
        
        <div class="features">
            <div class="feature">
                <h3>⚡ CloudFront</h3>
                <p>Global CDN for fast loading</p>
            </div>
            <div class="feature">
                <h3>🔒 SSL/TLS</h3>
                <p>Secure HTTPS encryption</p>
            </div>
            <div class="feature">
                <h3>🌐 Route53</h3>
                <p>Reliable DNS management</p>
            </div>
            <div class="feature">
                <h3>📦 S3</h3>
                <p>Scalable file storage</p>
            </div>
        </div>
        
        <p>Replace this file with your actual website content.</p>
        <div class="highlight">Built with AWS Website Automation</div>
    </div>
</body>
</html>
EOF

# Create README
cat > README.md << 'EOF'
# AWS Website Automation

Automated deployment of websites using AWS Route53, S3, CloudFront, and ACM.

## Quick Start

1. **Collect files from conversation** (see FILE_COLLECTION_CHECKLIST.md)
2. **Make scripts executable**: `chmod +x *.sh`
3. **Set AWS credentials** (environment variables or `aws configure`)
4. **Deploy**: `./deploy-website.sh example.com`

## Usage

```bash
# Infrastructure only
./deploy-website.sh example.com

# Infrastructure + upload files  
./deploy-website.sh example.com ./websites/my-site

# Clean up
./cleanup-website.sh example.com
```

## Prerequisites

- AWS CLI
- jq
- Valid AWS credentials

## Files

- `website-template.yaml` - CloudFormation template
- `deploy-website.sh` - Main deployment script
- `cleanup-website.sh` - Cleanup script
- `examples/` - Example website files
- `websites/` - Your website folders

## Cost

Typically $1-5/month per website for small sites.

## Support

- Route53: $0.50/month per hosted zone
- CloudFront: $0.085/GB + $0.0075/10,000 requests
- S3: $0.023/GB storage
- ACM: Free SSL certificates
EOF

print_success "Project structure created!"
echo ""
print_status "Next steps:"
echo "1. Follow the FILE_COLLECTION_CHECKLIST.md to copy files from conversation"
echo "2. Run: chmod +x *.sh"
echo "3. Set up AWS credentials"
echo "4. Deploy your first site: ./deploy-website.sh example.com"
echo ""
print_status "Files created:"
echo "- FILE_COLLECTION_CHECKLIST.md (file collection guide)"
echo "- README.md (project documentation)"
echo "- examples/index.html (sample website)"
echo "- websites/ (folder for your sites)"
echo ""
print_warning "Remember to copy all the script files from the Claude conversation!"

ls -la