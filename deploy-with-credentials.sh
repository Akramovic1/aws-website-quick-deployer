#!/bin/bash

# AWS Static Website Deployer with Inline Credentials
# Deploy static websites to AWS with provided credentials
# Usage: ./deploy-with-credentials.sh <access-key> <secret-key> <domain-name> [website-folder] [region]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Emojis
ROCKET="🚀"
CHECK="✅"
WARNING="⚠️"
ERROR="❌"
INFO="ℹ️"
CLIPBOARD="📋"
KEY="🔑"

# Function to print colored output
print_status() {
    echo -e "${GREEN}${CHECK} $1${NC}"
}

print_info() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

print_error() {
    echo -e "${RED}${ERROR} $1${NC}"
}

print_header() {
    echo -e "${PURPLE}${ROCKET} $1${NC}"
}

print_key() {
    echo -e "${YELLOW}${KEY} $1${NC}"
}

# Function to validate credentials format
validate_credentials() {
    local access_key=$1
    local secret_key=$2
    
    # Basic validation
    if [[ ! $access_key =~ ^AKIA[A-Z0-9]{16}$ ]]; then
        print_warning "Access key format looks unusual (should start with AKIA)"
    fi
    
    if [ ${#secret_key} -ne 40 ]; then
        print_warning "Secret key length is unusual (should be 40 characters)"
    fi
}

# Function to test AWS credentials
test_credentials() {
    local access_key=$1
    local secret_key=$2
    local region=${3:-us-east-1}
    
    print_info "Testing AWS credentials..."
    
    # Set temporary credentials
    export AWS_ACCESS_KEY_ID="$access_key"
    export AWS_SECRET_ACCESS_KEY="$secret_key"
    export AWS_DEFAULT_REGION="$region"
    
    # Test credentials
    if aws sts get-caller-identity &> /dev/null; then
        local account_id=$(aws sts get-caller-identity --query 'Account' --output text)
        local user_arn=$(aws sts get-caller-identity --query 'Arn' --output text)
        print_status "Credentials validated successfully"
        print_info "Account ID: $account_id"
        print_info "User/Role: $user_arn"
        return 0
    else
        print_error "Invalid AWS credentials"
        return 1
    fi
}

# Function to validate domain name
validate_domain() {
    local domain=$1
    if [[ ! $domain =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$ ]]; then
        print_error "Invalid domain name format: $domain"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        echo "Install: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
        exit 1
    fi
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        print_error "jq is not installed. Please install it first."
        echo "Ubuntu/Debian: sudo apt-get install jq"
        echo "macOS: brew install jq"
        exit 1
    fi
    
    print_status "All prerequisites satisfied"
}

# Function to deploy CloudFormation stack
deploy_stack() {
    local domain=$1
    local stack_name="website-$(echo $domain | tr '.' '-')"
    
    print_header "Deploying AWS Infrastructure for $domain..."
    
    # Deploy CloudFormation stack
    aws cloudformation deploy \
        --template-file website-template.yaml \
        --stack-name "$stack_name" \
        --parameter-overrides DomainName="$domain" \
        --capabilities CAPABILITY_IAM \
        --region us-east-1
    
    if [ $? -eq 0 ]; then
        print_status "Infrastructure deployed successfully"
    else
        print_error "Infrastructure deployment failed"
        exit 1
    fi
    
    # Get stack outputs
    print_info "Retrieving stack information..."
    
    local outputs=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region us-east-1 \
        --query 'Stacks[0].Outputs' \
        --output json)
    
    # Extract values
    local website_url=$(echo "$outputs" | jq -r '.[] | select(.OutputKey=="WebsiteURL") | .OutputValue')
    local bucket_name=$(echo "$outputs" | jq -r '.[] | select(.OutputKey=="S3BucketSecureURL") | .OutputValue' | sed 's|https://||' | sed 's|.s3.amazonaws.com||')
    local cloudfront_id=$(echo "$outputs" | jq -r '.[] | select(.OutputKey=="CloudFrontDistributionId") | .OutputValue')
    local name_servers=$(echo "$outputs" | jq -r '.[] | select(.OutputKey=="NameServers") | .OutputValue')
    
    # Display information
    echo
    print_header "Deployment Complete!"
    echo
    print_info "Website URL: $website_url"
    print_info "S3 Bucket: $bucket_name"
    print_info "CloudFront Distribution ID: $cloudfront_id"
    echo
    
    # Display name servers
    echo -e "${YELLOW}${CLIPBOARD} NAME SERVERS (Add these to your domain registrar):${NC}"
    IFS=', ' read -ra NS_ARRAY <<< "$name_servers"
    counter=1
    for ns in "${NS_ARRAY[@]}"; do
        echo "   $counter. $ns"
        ((counter++))
    done
    echo
    
    print_warning "DNS propagation can take 24-48 hours"
    
    return 0
}

# Function to upload website files
upload_files() {
    local domain=$1
    local folder=$2
    
    if [ ! -d "$folder" ]; then
        print_error "Website folder '$folder' does not exist"
        exit 1
    fi
    
    print_header "Uploading website files from $folder..."
    
    # Upload files to S3
    aws s3 sync "$folder" "s3://$domain" --delete
    
    if [ $? -eq 0 ]; then
        print_status "Files uploaded successfully"
        
        # Get CloudFront distribution ID
        local stack_name="website-$(echo $domain | tr '.' '-')"
        local cloudfront_id=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" \
            --region us-east-1 \
            --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
            --output text)
        
        # Invalidate CloudFront cache
        if [ ! -z "$cloudfront_id" ]; then
            print_info "Invalidating CloudFront cache..."
            aws cloudfront create-invalidation \
                --distribution-id "$cloudfront_id" \
                --paths "/*" > /dev/null
            print_status "CloudFront cache invalidated"
        fi
    else
        print_error "File upload failed"
        exit 1
    fi
}

# Function to create sample website
create_sample_website() {
    local domain=$1
    local temp_dir=$(mktemp -d)
    
    print_info "Creating sample website..."
    
    cat > "$temp_dir/index.html" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to $domain</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 600px;
            margin: 1rem;
        }
        h1 {
            color: #333;
            margin-bottom: 1rem;
        }
        .emoji {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        .info {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }
        .badge {
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 3px;
            font-size: 0.8rem;
            margin: 0.2rem;
        }
        .deployed-with {
            margin-top: 1rem;
            padding: 1rem;
            background: #e3f2fd;
            border-radius: 5px;
            border-left: 4px solid #2196f3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="emoji">🚀</div>
        <h1>Welcome to $domain</h1>
        <p>Your website is now live on AWS!</p>
        
        <div class="info">
            <h3>Powered by:</h3>
            <span class="badge">Amazon S3</span>
            <span class="badge">CloudFront CDN</span>
            <span class="badge">Route53 DNS</span>
            <span class="badge">SSL Certificate</span>
        </div>
        
        <div class="deployed-with">
            <h4>🔑 Deployed with Credentials Script</h4>
            <p>This site was deployed using the <code>deploy-with-credentials.sh</code> script</p>
        </div>
        
        <p>Replace this file with your own <code>index.html</code> to get started.</p>
        <p><small>Deployed with AWS Static Website Deployer</small></p>
    </div>
</body>
</html>
EOF

    # Upload sample website
    upload_files "$domain" "$temp_dir"
    
    # Clean up
    rm -rf "$temp_dir"
    
    print_status "Sample website deployed"
}

# Function to clean up credentials from environment
cleanup_credentials() {
    unset AWS_ACCESS_KEY_ID
    unset AWS_SECRET_ACCESS_KEY
    unset AWS_DEFAULT_REGION
    print_info "Credentials cleared from environment"
}

# Main function
main() {
    echo
    print_header "AWS Static Website Deployer (with Credentials)"
    echo
    
    # Check arguments
    if [ $# -lt 3 ]; then
        echo "Usage: $0 <access-key> <secret-key> <domain-name> [website-folder] [region]"
        echo
        echo "Examples:"
        echo "  $0 AKIAIOSFODNN7EXAMPLE wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY example.com"
        echo "  $0 AKIAIOSFODNN7EXAMPLE wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY example.com ./website"
        echo "  $0 AKIAIOSFODNN7EXAMPLE wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY example.com ./website us-west-2"
        echo
        print_warning "⚠️  Security Warning:"
        echo "• This script accepts credentials as command line arguments"
        echo "• Command line arguments may be visible in process lists"
        echo "• Consider using environment variables or AWS CLI configuration instead"
        echo "• Use this script only in secure environments"
        echo
        exit 1
    fi
    
    local access_key=$1
    local secret_key=$2
    local domain=$3
    local website_folder=$4
    local region=${5:-us-east-1}
    
    # Security warning
    print_warning "Security Notice: Credentials provided via command line"
    print_info "Ensure you're in a secure environment"
    echo
    
    # Validate inputs
    validate_domain "$domain"
    validate_credentials "$access_key" "$secret_key"
    check_prerequisites
    
    # Test credentials
    if ! test_credentials "$access_key" "$secret_key" "$region"; then
        cleanup_credentials
        exit 1
    fi
    
    # Deploy infrastructure
    deploy_stack "$domain"
    
    # Handle file upload
    if [ -n "$website_folder" ]; then
        upload_files "$domain" "$website_folder"
    else
        print_info "No website folder specified, creating sample website..."
        create_sample_website "$domain"
    fi
    
    echo
    print_header "🎉 Deployment Complete!"
    echo
    print_info "Next steps:"
    echo "1. Add the name servers to your domain registrar"
    echo "2. Wait 24-48 hours for DNS propagation"
    echo "3. Visit https://$domain to see your website"
    echo
    print_info "To update your website:"
    echo "aws s3 sync ./your-website s3://$domain --delete"
    echo
    
    # Clean up credentials
    cleanup_credentials
    
    print_key "Credentials have been cleared from this session"
}

# Trap to clean up credentials on script exit
trap cleanup_credentials EXIT

# Run main function
main "$@"