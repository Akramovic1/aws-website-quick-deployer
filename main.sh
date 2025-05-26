#!/bin/bash

# AWS Static Website Deployer - Main Control Script
# Interactive terminal program to control all deployment scripts
# Usage: ./main-deployer.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Emojis
ROCKET="🚀"
TERMINAL="💻"
PYTHON="🐍"
KEY="🔑"
TRASH="🗑️"
GEAR="⚙️"
INFO="ℹ️"
CHECK="✅"
WARNING="⚠️"
ERROR="❌"

# Function to print colored output
print_header() {
    echo -e "${PURPLE}${1}${NC}"
}

print_menu_item() {
    echo -e "${CYAN}${1}${NC} ${2}"
}

print_info() {
    echo -e "${BLUE}${INFO} ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}${CHECK} ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} ${1}${NC}"
}

print_error() {
    echo -e "${RED}${ERROR} ${1}${NC}"
}

print_title() {
    echo -e "${WHITE}${1}${NC}"
}

# Function to display main menu
show_main_menu() {
    clear
    echo
    print_header "╔══════════════════════════════════════════════════════════════╗"
    print_header "║            AWS Static Website Deployer Control              ║"
    print_header "╚══════════════════════════════════════════════════════════════╝"
    echo
    print_title "                    Choose Your Deployment Method:"
    echo
    print_menu_item "1. ${ROCKET}" "Standard Deployment (Bash Script)"
    print_menu_item "2. ${KEY}" "Deploy with Credentials (Inline)"
    print_menu_item "3. ${PYTHON}" "Python Deployment (Full Featured)"
    echo
    print_title "                      Management Options:"
    echo
    print_menu_item "4. ${TRASH}" "Cleanup Resources (Standard)"
    print_menu_item "5. ${KEY}${TRASH}" "Cleanup with Credentials"
    print_menu_item "6. ${PYTHON}${TRASH}" "Python Cleanup"
    print_menu_item "7. ${PYTHON}${INFO}" "Check Deployment Status"
    echo
    print_title "                         Utilities:"
    echo
    print_menu_item "8. ${GEAR}" "Prerequisites Check"
    print_menu_item "9. ${INFO}" "View Documentation"
    print_menu_item "0. ${CHECK}" "Exit"
    echo
    print_header "══════════════════════════════════════════════════════════════"
    echo
}

# Function to read user input with validation
read_input() {
    local prompt="$1"
    local var_name="$2"
    local validation="$3"
    
    while true; do
        echo -n -e "${CYAN}${prompt}: ${NC}"
        read value
        
        if [ -z "$value" ]; then
            print_error "Input cannot be empty. Please try again."
            continue
        fi
        
        # Domain validation
        if [ "$validation" = "domain" ]; then
            if [[ ! $value =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$ ]]; then
                print_error "Invalid domain format. Example: example.com"
                continue
            fi
        fi
        
        # Directory validation
        if [ "$validation" = "directory" ]; then
            if [ "$value" != "skip" ] && [ ! -d "$value" ]; then
                print_error "Directory does not exist. Enter 'skip' to create sample website."
                continue
            fi
        fi
        
        # AWS access key validation
        if [ "$validation" = "access_key" ]; then
            if [[ ! $value =~ ^AKIA[A-Z0-9]{16}$ ]]; then
                print_warning "Access key format looks unusual (should start with AKIA and be 20 chars)"
                echo -n -e "${YELLOW}Continue anyway? (y/n): ${NC}"
                read confirm
                if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                    continue
                fi
            fi
        fi
        
        # AWS secret key validation
        if [ "$validation" = "secret_key" ]; then
            if [ ${#value} -ne 40 ]; then
                print_warning "Secret key length is unusual (should be 40 characters)"
                echo -n -e "${YELLOW}Continue anyway? (y/n): ${NC}"
                read confirm
                if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                    continue
                fi
            fi
        fi
        
        eval "$var_name='$value'"
        break
    done
}

# Function to check prerequisites
check_prerequisites() {
    clear
    print_header "Checking Prerequisites..."
    echo
    
    # Check AWS CLI
    if command -v aws &> /dev/null; then
        print_success "AWS CLI is installed"
        aws --version
    else
        print_error "AWS CLI is not installed"
        echo "Install from: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    fi
    echo
    
    # Check jq
    if command -v jq &> /dev/null; then
        print_success "jq is installed"
        jq --version
    else
        print_error "jq is not installed"
        echo "Ubuntu/Debian: sudo apt-get install jq"
        echo "macOS: brew install jq"
    fi
    echo
    
    # Check Python (for Python scripts)
    if command -v python3 &> /dev/null; then
        print_success "Python 3 is installed"
        python3 --version
    else
        print_warning "Python 3 is not installed (needed for Python deployment option)"
    fi
    echo
    
    # Check boto3 (for Python scripts)
    if python3 -c "import boto3" 2>/dev/null; then
        print_success "boto3 is installed"
    else
        print_warning "boto3 is not installed (needed for Python deployment)"
        echo "Install with: pip3 install boto3"
    fi
    echo
    
    # Check AWS credentials
    if aws sts get-caller-identity &> /dev/null; then
        print_success "AWS credentials are configured"
        aws sts get-caller-identity --output table
    else
        print_warning "AWS credentials not configured"
        echo "Configure with: aws configure"
    fi
    echo
    
    echo -n -e "${CYAN}Press Enter to continue...${NC}"
    read
}

# Function for standard deployment
standard_deployment() {
    clear
    print_header "Standard Deployment (Bash Script)"
    echo
    print_info "This will use your configured AWS credentials"
    echo
    
    read_input "Enter domain name (e.g., example.com)" domain "domain"
    read_input "Enter website folder path (or 'skip' for sample)" folder "directory"
    
    echo
    print_info "Starting deployment..."
    echo
    
    if [ "$folder" = "skip" ]; then
        ./deploy-website.sh "$domain"
    else
        ./deploy-website.sh "$domain" "$folder"
    fi
    
    echo
    echo -n -e "${CYAN}Press Enter to continue...${NC}"
    read
}

# Function for deployment with credentials
deployment_with_credentials() {
    clear
    print_header "Deploy with Credentials"
    echo
    print_warning "Security Warning: Credentials will be passed as command line arguments"
    print_info "Use this only in secure environments"
    echo
    
    read_input "Enter AWS Access Key ID" access_key "access_key"
    echo -n -e "${CYAN}Enter AWS Secret Access Key (hidden): ${NC}"
    read -s secret_key
    echo
    read_input "Enter domain name (e.g., example.com)" domain "domain"
    read_input "Enter website folder path (or 'skip' for sample)" folder "directory"
    read_input "Enter AWS region (default: us-east-1)" region
    
    if [ -z "$region" ]; then
        region="us-east-1"
    fi
    
    echo
    print_info "Starting deployment..."
    echo
    
    if [ "$folder" = "skip" ]; then
        ./deploy-with-credentials.sh "$access_key" "$secret_key" "$domain" "" "$region"
    else
        ./deploy-with-credentials.sh "$access_key" "$secret_key" "$domain" "$folder" "$region"
    fi
    
    echo
    echo -n -e "${CYAN}Press Enter to continue...${NC}"
    read
}

# Function for Python deployment
python_deployment() {
    clear
    print_header "Python Deployment"
    echo
    
    # Check if Python and boto3 are available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo -n -e "${CYAN}Press Enter to continue...${NC}"
        read
        return
    fi
    
    if ! python3 -c "import boto3" 2>/dev/null; then
        print_error "boto3 is not installed"
        print_info "Install with: pip3 install boto3"
        echo -n -e "${CYAN}Press Enter to continue...${NC}"
        read
        return
    fi
    
    read_input "Enter domain name (e.g., example.com)" domain "domain"
    read_input "Enter website folder path (or 'skip' for sample)" folder "directory"
    read_input "Enter AWS region (default: us-east-1)" region
    
    if [ -z "$region" ]; then
        region="us-east-1"
    fi
    
    echo
    print_info "Starting Python deployment..."
    echo
    
    if [ "$folder" = "skip" ]; then
        python3 aws-website-deployer.py deploy "$domain" --region "$region"
    else
        python3 aws-website-deployer.py deploy "$domain" --website-folder "$folder" --region "$region"
    fi
    
    echo
    echo -n -e "${CYAN}Press Enter to continue...${NC}"
    read
}

# Function for standard cleanup
standard_cleanup() {
    clear
    print_header "Standard Cleanup"
    echo
    print_warning "This will permanently delete ALL AWS resources for the domain"
    echo
    
    read_input "Enter domain name to cleanup" domain "domain"
    
    echo
    print_warning "⚠️  FINAL WARNING: This will delete everything for $domain"
    echo -n -e "${YELLOW}Are you absolutely sure? (type 'DELETE' to confirm): ${NC}"
    read confirmation
    
    if [ "$confirmation" != "DELETE" ]; then
        print_info "Cleanup cancelled"
        echo -n -e "${CYAN}Press Enter to continue...${NC}"
        read
        return
    fi
    
    echo
    print_info "Starting cleanup..."
    echo
    
    ./cleanup-website.sh "$domain"
    
    echo
    echo -n -e "${CYAN}Press Enter to continue...${NC}"
    read
}

# Function for cleanup with credentials
cleanup_with_credentials() {
    clear
    print_header "Cleanup with Credentials"
    echo
    print_warning "This will permanently delete ALL AWS resources for the domain"
    echo
    
    read_input "Enter AWS Access Key ID" access_key "access_key"
    echo -n -e "${CYAN}Enter AWS Secret Access Key (hidden): ${NC}"
    read -s secret_key
    echo
    read_input "Enter domain name to cleanup" domain "domain"
    read_input "Enter AWS region (default: us-east-1)" region
    
    if [ -z "$region" ]; then
        region="us-east-1"
    fi
    
    echo
    print_warning "⚠️  FINAL WARNING: This will delete everything for $domain"
    echo -n -e "${YELLOW}Are you absolutely sure? (type 'DELETE' to confirm): ${NC}"
    read confirmation
    
    if [ "$confirmation" != "DELETE" ]; then
        print_info "Cleanup cancelled"
        echo -n -e "${CYAN}Press Enter to continue...${NC}"
        read
        return
    fi
    
    echo
    print_info "Starting cleanup..."
    echo
    
    ./cleanup-with-credentials.sh "$access_key" "$secret_key" "$domain" "$region"
    
    echo
    echo -n -e "${CYAN}Press Enter to continue...${NC}"
    read
}

# Function for Python cleanup
python_cleanup() {
    clear
    print_header "Python Cleanup"
    echo
    
    # Check if Python and boto3 are available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo -n -e "${CYAN}Press Enter to continue...${NC}"
        read
        return
    fi
    
    if ! python3 -c "import boto3" 2>/dev/null; then
        print_error "boto3 is not installed"
        print_info "Install with: pip3 install boto3"
        echo -n -e "${CYAN}Press Enter to continue...${NC}"
        read
        return
    fi
    
    print_warning "This will permanently delete ALL AWS resources for the domain"
    echo
    
    read_input "Enter domain name to cleanup" domain "domain"
    read_input "Enter AWS region (default: us-east-1)" region
    
    if [ -z "$region" ]; then
        region="us-east-1"
    fi
    
    echo
    print_warning "⚠️  FINAL WARNING: This will delete everything for $domain"
    echo -n -e "${YELLOW}Are you absolutely sure? (type 'DELETE' to confirm): ${NC}"
    read confirmation
    
    if [ "$confirmation" != "DELETE" ]; then
        print_info "Cleanup cancelled"
        echo -n -e "${CYAN}Press Enter to continue...${NC}"
        read
        return
    fi
    
    echo
    print_info "Starting Python cleanup..."
    echo
    
    python3 aws-website-deployer.py cleanup "$domain" --region "$region"
    
    echo
    echo -n -e "${CYAN}Press Enter to continue...${NC}"
    read
}

# Function to check deployment status
check_status() {
    clear
    print_header "Check Deployment Status"
    echo
    
    # Check if Python and boto3 are available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo -n -e "${CYAN}Press Enter to continue...${NC}"
        read
        return
    fi
    
    if ! python3 -c "import boto3" 2>/dev/null; then
        print_error "boto3 is not installed"
        print_info "Install with: pip3 install boto3"
        echo -n -e "${CYAN}Press Enter to continue...${NC}"
        read
        return
    fi
    
    read_input "Enter domain name to check" domain "domain"
    read_input "Enter AWS region (default: us-east-1)" region
    
    if [ -z "$region" ]; then
        region="us-east-1"
    fi
    
    echo
    print_info "Checking status..."
    echo
    
    python3 aws-website-deployer.py status "$domain" --region "$region"
    
    echo
    echo -n -e "${CYAN}Press Enter to continue...${NC}"
    read
}

# Function to show documentation
show_documentation() {
    clear
    print_header "AWS Static Website Deployer Documentation"
    echo
    
    print_title "📚 Available Scripts:"
    echo
    print_info "1. deploy-website.sh - Standard deployment using AWS CLI config"
    print_info "2. deploy-with-credentials.sh - Deploy with inline credentials"
    print_info "3. aws-website-deployer.py - Python version with full features"
    print_info "4. cleanup-website.sh - Clean up AWS resources"
    print_info "5. cleanup-with-credentials.sh - Cleanup with inline credentials"
    echo
    
    print_title "🏗️ What Gets Created:"
    echo
    print_info "• S3 bucket for website hosting"
    print_info "• S3 bucket for www redirect"
    print_info "• CloudFront distribution (global CDN)"
    print_info "• Route53 hosted zone (DNS)"
    print_info "• SSL certificate (free, auto-renewing)"
    print_info "• All necessary IAM policies and roles"
    echo
    
    print_title "💰 Estimated Monthly Cost:"
    echo
    print_info "• Route53 Hosted Zone: $0.50"
    print_info "• CloudFront: $0.085/GB + $0.0075/10k requests"
    print_info "• S3 Storage: $0.023/GB"
    print_info "• SSL Certificate: FREE"
    print_info "• Total for small sites: $1-5/month"
    echo
    
    print_title "🔧 Prerequisites:"
    echo
    print_info "• AWS CLI installed and configured"
    print_info "• jq command-line tool"
    print_info "• Python 3 + boto3 (for Python scripts)"
    print_info "• Valid domain name"
    echo
    
    print_title "📖 Full Documentation:"
    echo
    print_info "Check README.md for complete instructions"
    print_info "GitHub: https://github.com/Akramovic1/aws-website-quick-deployer"
    echo
    
    echo -n -e "${CYAN}Press Enter to continue...${NC}"
    read
}

# Main function
main() {
    # Check if we're in the right directory
    if [ ! -f "deploy-website.sh" ] || [ ! -f "website-template.yaml" ]; then
        print_error "Required files not found in current directory"
        print_info "Make sure you're running this from the aws-website-quick-deployer directory"
        exit 1
    fi
    
    # Make sure scripts are executable
    chmod +x *.sh 2>/dev/null || true
    
    while true; do
        show_main_menu
        
        echo -n -e "${CYAN}Enter your choice (0-9): ${NC}"
        read choice
        
        case $choice in
            1)
                standard_deployment
                ;;
            2)
                deployment_with_credentials
                ;;
            3)
                python_deployment
                ;;
            4)
                standard_cleanup
                ;;
            5)
                cleanup_with_credentials
                ;;
            6)
                python_cleanup
                ;;
            7)
                check_status
                ;;
            8)
                check_prerequisites
                ;;
            9)
                show_documentation
                ;;
            0)
                clear
                print_success "Thank you for using AWS Static Website Deployer!"
                print_info "Visit https://github.com/Akramovic1/aws-website-quick-deployer for updates"
                echo
                exit 0
                ;;
            *)
                print_error "Invalid choice. Please select 0-9."
                sleep 2
                ;;
        esac
    done
}

# Run main function
main "$@"