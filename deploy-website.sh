#!/bin/bash

# AWS Static Website Deployer
# Deploy static websites to AWS with S3, CloudFront, Route53, and SSL
# Usage: ./deploy-website.sh <domain-name> [website-folder]

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
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured."
        echo "Run: aws configure"
        echo "Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
        exit 1
    fi
    
    print_status "All prerequisites satisfied"
}

# Function to validate domain name
validate_domain() {
    local domain=$1
    if [[ ! $domain =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$ ]]; then
        print_error "Invalid domain name format: $domain"
        exit 1
    fi
}

# Function to deploy Phase 1 (Route53 hosted zone)
deploy_phase1() {
    local domain=$1
    local stack_name="website-$(echo $domain | tr '.' '-')-phase1"
    
    print_header "Phase 1: Creating DNS hosted zone for $domain..."
    
    # Check if Phase 1 stack already exists
    local existing_stack=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region us-east-1 \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$existing_stack" != "NOT_FOUND" ] && [ "$existing_stack" != "DELETE_COMPLETE" ]; then
        print_info "Found existing Phase 1 stack, retrieving nameservers..."
    else
        # Deploy Phase 1 CloudFormation stack
        aws cloudformation deploy \
            --template-file website-template-phase1.yaml \
            --stack-name "$stack_name" \
            --parameter-overrides DomainName="$domain" \
            --region us-east-1
        
        if [ $? -ne 0 ]; then
            print_error "Phase 1 deployment failed"
            exit 1
        fi
        print_status "Phase 1 deployment complete"
    fi
    
    # Get nameservers
    local name_servers=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region us-east-1 \
        --query 'Stacks[0].Outputs[?OutputKey==`NameServers`].OutputValue' \
        --output text)
    
    # Display name servers prominently to stderr so it doesn't interfere with return value
    >&2 echo
    >&2 echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    >&2 echo -e "${YELLOW}║                  IMPORTANT: NAMESERVERS                       ║${NC}"
    >&2 echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
    >&2 echo
    >&2 echo -e "${YELLOW}${CLIPBOARD} Add these nameservers to your domain registrar (GoDaddy, etc.):${NC}"
    >&2 echo
    IFS=', ' read -ra NS_ARRAY <<< "$name_servers"
    counter=1
    for ns in "${NS_ARRAY[@]}"; do
        >&2 echo -e "${GREEN}   $counter. $ns${NC}"
        ((counter++))
    done
    >&2 echo
    >&2 echo -e "${YELLOW}Steps to update nameservers:${NC}"
    >&2 echo -e "${BLUE}   1. Log into your domain registrar (GoDaddy, etc.)${NC}"
    >&2 echo -e "${BLUE}   2. Find DNS/Nameserver settings for $domain${NC}"
    >&2 echo -e "${BLUE}   3. Replace existing nameservers with the 4 above${NC}"
    >&2 echo -e "${BLUE}   4. Wait 5-15 minutes for DNS propagation${NC}"
    >&2 echo
    >&2 echo -e "${RED}⚠️  SSL certificate creation will FAIL if nameservers aren't updated!${NC}"
    >&2 echo
    
    # Wait for user confirmation
    >&2 echo -e "${CYAN}Press Enter ONLY after you've updated nameservers at your registrar...${NC}"
    read -p ""
    
    # Simple DNS propagation check (non-blocking)
    >&2 print_info "Checking DNS propagation..."
    local first_ns=$(echo "$name_servers" | cut -d',' -f1 | xargs)
    
    # Quick check with timeout - don't get stuck
    if timeout 10 nslookup "$domain" "$first_ns" >/dev/null 2>&1; then
        >&2 print_status "DNS propagation verified"
    else
        >&2 print_warning "DNS propagation not yet verified, but continuing anyway"
        >&2 print_info "SSL certificate will validate automatically once DNS propagates"
    fi
    
    echo "$stack_name"  # Return stack name for Phase 2
}

# Function to deploy Phase 2 (Complete infrastructure with SSL)
deploy_phase2() {
    local domain=$1
    local phase1_stack_name=$2
    local stack_name="website-$(echo $domain | tr '.' '-')-phase2"
    
    print_header "Phase 2: Creating complete infrastructure with SSL..."
    
    # Deploy Phase 2 CloudFormation stack with retry logic
    local max_retries=3
    local retry_count=0
    local deployment_success=false
    
    while [ $retry_count -lt $max_retries ] && [ "$deployment_success" = false ]; do
        if [ $retry_count -gt 0 ]; then
            print_info "Retry attempt $retry_count of $max_retries..."
            print_info "Waiting 2 minutes for DNS propagation before retry..."
            sleep 120
        fi
        
        print_info "Deploying Phase 2 infrastructure..."
        
        if aws cloudformation deploy \
            --template-file website-template-phase2.yaml \
            --stack-name "$stack_name" \
            --parameter-overrides DomainName="$domain" Phase1StackName="$phase1_stack_name" \
            --capabilities CAPABILITY_IAM \
            --region us-east-1; then
            deployment_success=true
            print_status "Infrastructure deployed successfully"
        else
            ((retry_count++))
            if [ $retry_count -lt $max_retries ]; then
                print_warning "Phase 2 deployment failed, likely due to DNS propagation delay"
                print_info "SSL certificate validation may still be in progress..."
            else
                print_error "Phase 2 deployment failed after $max_retries attempts"
                print_info "This is likely due to DNS propagation delays. You can:"
                print_info "1. Wait 30 minutes and run the deployment again"
                print_info "2. Check that nameservers are correctly set at your registrar"
                exit 1
            fi
        fi
    done
    
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
    
    # Get nameservers from Phase 1
    local name_servers=$(aws cloudformation describe-stacks \
        --stack-name "$phase1_stack_name" \
        --region us-east-1 \
        --query 'Stacks[0].Outputs[?OutputKey==`NameServers`].OutputValue' \
        --output text)
    
    # Display information
    echo
    print_header "Deployment Complete!"
    echo
    print_info "Website URL: $website_url"
    print_info "S3 Bucket: $bucket_name"
    print_info "CloudFront Distribution ID: $cloudfront_id"
    echo
    
    # Display name servers again for reference
    echo -e "${YELLOW}${CLIPBOARD} Your nameservers (should already be set):${NC}"
    IFS=', ' read -ra NS_ARRAY <<< "$name_servers"
    counter=1
    for ns in "${NS_ARRAY[@]}"; do
        echo "   $counter. $ns"
        ((counter++))
    done
    echo
    
    return 0
}

# Function to deploy CloudFormation stack (combines both phases)
deploy_stack() {
    local domain=$1
    
    print_header "Deploying AWS Infrastructure for $domain..."
    
    # Phase 1: Create hosted zone and get nameservers
    local phase1_stack_name=$(deploy_phase1 "$domain")
    
    # Phase 2: Create complete infrastructure with SSL
    deploy_phase2 "$domain" "$phase1_stack_name"
    
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

# Main function
main() {
    echo
    print_header "AWS Static Website Deployer"
    echo
    
    # Check arguments
    if [ $# -lt 1 ]; then
        echo "Usage: $0 <domain-name> [website-folder]"
        echo
        echo "Examples:"
        echo "  $0 example.com                    # Deploy infrastructure only"
        echo "  $0 example.com ./website          # Deploy infrastructure + upload files"
        echo
        exit 1
    fi
    
    local domain=$1
    local website_folder=$2
    
    # Validate inputs
    validate_domain "$domain"
    check_prerequisites
    
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
    echo "1. Nameservers should already be added to your domain registrar"
    echo "2. Wait 24-48 hours for DNS propagation"
    echo "3. Visit https://$domain to see your website"
    echo
    print_info "To update your website:"
    echo "aws s3 sync ./your-website s3://$domain --delete"
    echo
}

# Run main function
main "$@"