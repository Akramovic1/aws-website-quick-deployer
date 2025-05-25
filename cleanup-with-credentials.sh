#!/bin/bash

# AWS Static Website Cleanup Script with Inline Credentials
# Removes all AWS resources created for a static website using provided credentials
# Usage: ./cleanup-with-credentials.sh <access-key> <secret-key> <domain-name> [region]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Emojis
TRASH="🗑️"
CHECK="✅"
WARNING="⚠️"
ERROR="❌"
INFO="ℹ️"
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
    echo -e "${PURPLE}${TRASH} $1${NC}"
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

# Function to check if AWS CLI is available
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi
}

# Function to empty S3 buckets
empty_s3_buckets() {
    local domain=$1
    
    print_info "Emptying S3 buckets..."
    
    # Empty main bucket
    if aws s3 ls "s3://$domain" &> /dev/null; then
        print_info "Emptying bucket: $domain"
        aws s3 rm "s3://$domain" --recursive
        print_status "Bucket $domain emptied"
    else
        print_info "Bucket $domain does not exist or already empty"
    fi
    
    # Empty www bucket
    if aws s3 ls "s3://www.$domain" &> /dev/null; then
        print_info "Emptying bucket: www.$domain"
        aws s3 rm "s3://www.$domain" --recursive
        print_status "Bucket www.$domain emptied"
    else
        print_info "Bucket www.$domain does not exist or already empty"
    fi
}

# Function to delete CloudFormation stack
delete_stack() {
    local domain=$1
    local stack_name="website-$(echo $domain | tr '.' '-')"
    
    print_info "Checking if CloudFormation stack exists..."
    
    if aws cloudformation describe-stacks --stack-name "$stack_name" --region us-east-1 &> /dev/null; then
        print_info "Deleting CloudFormation stack: $stack_name"
        
        aws cloudformation delete-stack \
            --stack-name "$stack_name" \
            --region us-east-1
        
        print_info "Waiting for stack deletion to complete..."
        print_warning "This may take several minutes..."
        
        aws cloudformation wait stack-delete-complete \
            --stack-name "$stack_name" \
            --region us-east-1
        
        if [ $? -eq 0 ]; then
            print_status "Stack deleted successfully"
        else
            print_error "Stack deletion failed or timed out"
            print_info "Check AWS CloudFormation console for details"
            exit 1
        fi
    else
        print_info "CloudFormation stack $stack_name does not exist"
    fi
}

# Function to check for remaining resources
check_remaining_resources() {
    local domain=$1
    
    print_info "Checking for any remaining resources..."
    
    # Check S3 buckets
    local buckets_exist=false
    if aws s3 ls "s3://$domain" &> /dev/null; then
        print_warning "S3 bucket still exists: $domain"
        buckets_exist=true
    fi
    
    if aws s3 ls "s3://www.$domain" &> /dev/null; then
        print_warning "S3 bucket still exists: www.$domain"
        buckets_exist=true
    fi
    
    # Check Route53 hosted zone
    local hosted_zones=$(aws route53 list-hosted-zones-by-name \
        --dns-name "$domain" \
        --query 'HostedZones[?Name==`'$domain'.`].Id' \
        --output text)
    
    if [ ! -z "$hosted_zones" ]; then
        print_warning "Route53 hosted zone might still exist for $domain"
        print_info "Hosted Zone ID(s): $hosted_zones"
    fi
    
    if [ "$buckets_exist" = true ]; then
        print_warning "Some resources may still exist. Check AWS console."
    else
        print_status "All resources appear to be cleaned up"
    fi
}

# Function to show cleanup summary
show_cleanup_summary() {
    local domain=$1
    
    echo
    print_header "Cleanup Summary for $domain"
    echo
    echo "The following resources have been removed:"
    echo "• S3 buckets ($domain and www.$domain)"
    echo "• CloudFront distribution"
    echo "• Route53 hosted zone"
    echo "• SSL certificate"
    echo "• IAM policies and roles"
    echo
    print_info "Remember to:"
    echo "1. Remove name servers from your domain registrar"
    echo "2. Check AWS billing for any remaining charges"
    echo
}

# Function to clean up credentials from environment
cleanup_credentials() {
    unset AWS_ACCESS_KEY_ID
    unset AWS_SECRET_ACCESS_KEY
    unset AWS_DEFAULT_REGION
    print_key "Credentials cleared from environment"
}

# Main function
main() {
    echo
    print_header "AWS Static Website Cleanup (with Credentials)"
    echo
    
    # Check arguments
    if [ $# -lt 3 ]; then
        echo "Usage: $0 <access-key> <secret-key> <domain-name> [region]"
        echo
        echo "Examples:"
        echo "  $0 AKIAIOSFODNN7EXAMPLE wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY example.com"
        echo "  $0 AKIAIOSFODNN7EXAMPLE wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY example.com us-west-2"
        echo
        print_warning "⚠️  Security Warning:"
        echo "• This script accepts credentials as command line arguments"
        echo "• Command line arguments may be visible in process lists"
        echo "• Consider using environment variables or AWS CLI configuration instead"
        echo "• Use this script only in secure environments"
        echo
        print_warning "⚠️  This will permanently delete all AWS resources for the domain"
        echo
        exit 1
    fi
    
    local access_key=$1
    local secret_key=$2
    local domain=$3
    local region=${4:-us-east-1}
    
    # Security warning
    print_warning "Security Notice: Credentials provided via command line"
    print_info "Ensure you're in a secure environment"
    echo
    
    # Validate inputs
    validate_domain "$domain"
    validate_credentials "$access_key" "$secret_key"
    check_aws_cli
    
    # Test credentials
    if ! test_credentials "$access_key" "$secret_key" "$region"; then
        cleanup_credentials
        exit 1
    fi
    
    # Confirmation
    echo
    print_warning "⚠️  WARNING: This will permanently delete all AWS resources for $domain"
    echo
    echo "This includes:"
    echo "• S3 buckets and all website files"
    echo "• CloudFront distribution"
    echo "• Route53 hosted zone"
    echo "• SSL certificate"
    echo
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        print_info "Cleanup cancelled"
        cleanup_credentials
        exit 0
    fi
    
    echo
    print_header "Starting cleanup process..."
    
    # Empty S3 buckets first (required before stack deletion)
    empty_s3_buckets "$domain"
    
    # Delete CloudFormation stack
    delete_stack "$domain"
    
    # Check for remaining resources
    check_remaining_resources "$domain"
    
    # Show summary
    show_cleanup_summary "$domain"
    
    print_status "Cleanup completed!"
    
    # Clean up credentials
    cleanup_credentials
}

# Trap to clean up credentials on script exit
trap cleanup_credentials EXIT

# Run main function
main "$@"