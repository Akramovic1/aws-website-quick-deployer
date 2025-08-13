#!/bin/bash

# AWS Static Website Cleanup Script
# Removes all AWS resources created for a static website
# Usage: ./cleanup-website.sh <domain-name>

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

# Function to validate domain name
validate_domain() {
    local domain=$1
    if [[ ! $domain =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$ ]]; then
        print_error "Invalid domain name format: $domain"
        exit 1
    fi
}

# Function to check if AWS CLI is configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured"
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

# Function to cleanup DNS records that might block hosted zone deletion
cleanup_dns_records() {
    local domain=$1
    
    print_info "Cleaning up DNS records that might block deletion..."
    
    # Find hosted zone for the domain
    local hosted_zone_id=$(aws route53 list-hosted-zones-by-name \
        --dns-name "$domain" \
        --query 'HostedZones[?Name==`'$domain'.`].Id' \
        --output text | cut -d'/' -f3)
    
    if [ -z "$hosted_zone_id" ]; then
        print_info "No hosted zone found for $domain"
        return
    fi
    
    print_info "Found hosted zone: $hosted_zone_id"
    
    # Get all DNS records except NS and SOA (which are required and will be deleted with the zone)
    local records=$(aws route53 list-resource-record-sets \
        --hosted-zone-id "$hosted_zone_id" \
        --query 'ResourceRecordSets[?Type!=`NS` && Type!=`SOA`]' \
        --output json 2>/dev/null)
    
    if [ "$records" = "[]" ] || [ -z "$records" ]; then
        print_info "No additional DNS records found to clean up"
        return
    fi
    
    # Delete each record
    echo "$records" | jq -c '.[]' | while read -r record; do
        local name=$(echo "$record" | jq -r '.Name')
        local type=$(echo "$record" | jq -r '.Type')
        
        print_info "Deleting DNS record: $name ($type)"
        
        # Create change batch for deletion
        local change_batch=$(echo "{\"Changes\":[{\"Action\":\"DELETE\",\"ResourceRecordSet\":$record}]}")
        
        # Delete the record
        aws route53 change-resource-record-sets \
            --hosted-zone-id "$hosted_zone_id" \
            --change-batch "$change_batch" \
            >/dev/null 2>&1 || print_warning "Failed to delete record $name"
    done
    
    print_status "DNS cleanup completed"
}

# Function to delete CloudFormation stacks
delete_stacks() {
    local domain=$1
    local stack_name="website-$(echo $domain | tr '.' '-')"
    
    print_info "Checking for CloudFormation stacks..."
    
    # Delete Phase 2 stack first (if exists)
    local phase2_stack="$stack_name-phase2"
    if aws cloudformation describe-stacks --stack-name "$phase2_stack" --region us-east-1 &> /dev/null; then
        print_info "Deleting Phase 2 stack: $phase2_stack"
        
        aws cloudformation delete-stack \
            --stack-name "$phase2_stack" \
            --region us-east-1
        
        print_info "Waiting for Phase 2 stack deletion..."
        print_warning "This may take several minutes..."
        
        aws cloudformation wait stack-delete-complete \
            --stack-name "$phase2_stack" \
            --region us-east-1
        
        if [ $? -eq 0 ]; then
            print_status "Phase 2 stack deleted successfully"
        else
            print_error "Phase 2 stack deletion failed or timed out"
            print_info "Check AWS CloudFormation console for details"
        fi
    else
        print_info "Phase 2 stack $phase2_stack does not exist"
    fi
    
    # Delete Phase 1 stack (if exists)
    local phase1_stack="$stack_name-phase1"
    if aws cloudformation describe-stacks --stack-name "$phase1_stack" --region us-east-1 &> /dev/null; then
        print_info "Deleting Phase 1 stack: $phase1_stack"
        
        aws cloudformation delete-stack \
            --stack-name "$phase1_stack" \
            --region us-east-1
        
        print_info "Waiting for Phase 1 stack deletion..."
        
        aws cloudformation wait stack-delete-complete \
            --stack-name "$phase1_stack" \
            --region us-east-1
        
        if [ $? -eq 0 ]; then
            print_status "Phase 1 stack deleted successfully"
        else
            print_error "Phase 1 stack deletion failed or timed out"
            print_info "Check AWS CloudFormation console for details"
        fi
    else
        print_info "Phase 1 stack $phase1_stack does not exist"
    fi
    
    # Also check for legacy single stack (backward compatibility)
    if aws cloudformation describe-stacks --stack-name "$stack_name" --region us-east-1 &> /dev/null; then
        print_info "Found legacy single stack: $stack_name"
        print_info "Deleting legacy stack..."
        
        aws cloudformation delete-stack \
            --stack-name "$stack_name" \
            --region us-east-1
        
        print_info "Waiting for legacy stack deletion..."
        
        aws cloudformation wait stack-delete-complete \
            --stack-name "$stack_name" \
            --region us-east-1
        
        if [ $? -eq 0 ]; then
            print_status "Legacy stack deleted successfully"
        else
            print_error "Legacy stack deletion failed or timed out"
            print_info "Check AWS CloudFormation console for details"
        fi
    else
        print_info "Legacy stack $stack_name does not exist"
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

# Main function
main() {
    echo
    print_header "AWS Static Website Cleanup"
    echo
    
    # Check arguments
    if [ $# -ne 1 ]; then
        echo "Usage: $0 <domain-name>"
        echo
        echo "Example: $0 example.com"
        echo
        print_warning "This will delete ALL AWS resources for the specified domain"
        echo
        exit 1
    fi
    
    local domain=$1
    
    # Validate inputs
    validate_domain "$domain"
    check_aws_cli
    
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
        exit 0
    fi
    
    echo
    print_header "Starting cleanup process..."
    
    # Empty S3 buckets first (required before stack deletion)
    empty_s3_buckets "$domain"
    
    # Clean up Route53 DNS records that might block deletion
    cleanup_dns_records "$domain"
    
    # Delete CloudFormation stacks
    delete_stacks "$domain"
    
    # Check for remaining resources
    check_remaining_resources "$domain"
    
    # Show summary
    show_cleanup_summary "$domain"
    
    print_status "Cleanup completed!"
}

# Run main function
main "$@"