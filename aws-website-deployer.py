#!/usr/bin/env python3
"""
AWS Static Website Deployer - Python Version
Deploy static websites to AWS with S3, CloudFront, Route53, and SSL certificates

Usage:
    python aws-website-deployer.py deploy <domain> [--website-folder path] [--region region]
    python aws-website-deployer.py cleanup <domain> [--region region]
    python aws-website-deployer.py status <domain> [--region region]

Examples:
    python aws-website-deployer.py deploy example.com
    python aws-website-deployer.py deploy example.com --website-folder ./website
    python aws-website-deployer.py cleanup example.com
    python aws-website-deployer.py status example.com
"""

import argparse
import boto3
import json
import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError
import re

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    PURPLE = '\033[0;35m'
    NC = '\033[0m'  # No Color

# Emojis
class Emojis:
    ROCKET = "🚀"
    CHECK = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    INFO = "ℹ️"
    CLIPBOARD = "📋"
    TRASH = "🗑️"
    PYTHON = "🐍"

def print_status(message):
    print(f"{Colors.GREEN}{Emojis.CHECK} {message}{Colors.NC}")

def print_info(message):
    print(f"{Colors.BLUE}{Emojis.INFO} {message}{Colors.NC}")

def print_warning(message):
    print(f"{Colors.YELLOW}{Emojis.WARNING} {message}{Colors.NC}")

def print_error(message):
    print(f"{Colors.RED}{Emojis.ERROR} {message}{Colors.NC}")

def print_header(message):
    print(f"{Colors.PURPLE}{Emojis.PYTHON} {message}{Colors.NC}")

class AWSWebsiteDeployer:
    def __init__(self, region='us-east-1'):
        self.region = region
        try:
            self.session = boto3.Session()
            self.cloudformation = self.session.client('cloudformation', region_name=region)
            self.s3 = self.session.client('s3')
            self.cloudfront = self.session.client('cloudfront')
            self.route53 = self.session.client('route53')
            self.sts = self.session.client('sts')
        except NoCredentialsError:
            print_error("AWS credentials not configured")
            print("Configure using: aws configure")
            print("Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            sys.exit(1)

    def validate_domain(self, domain):
        """Validate domain name format"""
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$'
        if not re.match(pattern, domain):
            print_error(f"Invalid domain name format: {domain}")
            sys.exit(1)

    def get_stack_name(self, domain):
        """Generate CloudFormation stack name from domain"""
        return f"website-{domain.replace('.', '-')}"

    def get_cloudformation_template(self):
        """Return CloudFormation template as string"""
        return """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Static website hosting with S3, CloudFront, Route53, and SSL certificate'

Parameters:
  DomainName:
    Type: String
    Description: Domain name for the website
    AllowedPattern: (?!-)[a-zA-Z0-9-.]{1,63}(?<!-)
    ConstraintDescription: must be a valid domain name.

Resources:
  S3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref DomainName
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      VersioningConfiguration:
        Status: Enabled

  S3BucketWww:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'www.${DomainName}'
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      WebsiteConfiguration:
        RedirectAllRequestsTo:
          HostName: !Ref DomainName
          Protocol: https

  OriginAccessControl:
    Type: AWS::CloudFront::OriginAccessControl
    Properties:
      OriginAccessControlConfig:
        Name: !Sub '${DomainName}-OAC'
        OriginAccessControlOriginType: s3
        SigningBehavior: always
        SigningProtocol: sigv4

  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Origins:
          - DomainName: !GetAtt S3Bucket.RegionalDomainName
            Id: S3Origin
            S3OriginConfig:
              OriginAccessIdentity: ''
            OriginAccessControlId: !GetRef OriginAccessControl
        Enabled: true
        HttpVersion: http2
        DefaultRootObject: index.html
        Aliases:
          - !Ref DomainName
          - !Sub 'www.${DomainName}'
        DefaultCacheBehavior:
          AllowedMethods:
            - DELETE
            - GET
            - HEAD
            - OPTIONS
            - PATCH
            - POST
            - PUT
          TargetOriginId: S3Origin
          ViewerProtocolPolicy: redirect-to-https
          CachePolicyId: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad
          OriginRequestPolicyId: 88a5eaf4-2fd4-4709-b370-b4c650ea3fcf
        PriceClass: PriceClass_100
        ViewerCertificate:
          AcmCertificateArn: !Ref SSLCertificate
          SslSupportMethod: sni-only
          MinimumProtocolVersion: TLSv1.2_2021
        CustomErrorResponses:
          - ErrorCode: 403
            ResponseCode: 200
            ResponsePagePath: /index.html
          - ErrorCode: 404
            ResponseCode: 200
            ResponsePagePath: /index.html

  S3BucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref S3Bucket
      PolicyDocument:
        Statement:
          - Sid: AllowCloudFrontServicePrincipal
            Effect: Allow
            Principal:
              Service: cloudfront.amazonaws.com
            Action: 's3:GetObject'
            Resource: !Sub '${S3Bucket}/*'
            Condition:
              StringEquals:
                'AWS:SourceArn': !Sub 'arn:aws:cloudfront::${AWS::AccountId}:distribution/${CloudFrontDistribution}'

  HostedZone:
    Type: AWS::Route53::HostedZone
    Properties:
      HostedZoneConfig:
        Comment: !Sub 'Hosted zone for ${DomainName}'
      Name: !Ref DomainName

  SSLCertificate:
    Type: AWS::CertificateManager::Certificate
    Properties:
      DomainName: !Ref DomainName
      SubjectAlternativeNames:
        - !Sub 'www.${DomainName}'
      DomainValidationOptions:
        - DomainName: !Ref DomainName
          HostedZoneId: !Ref HostedZone
        - DomainName: !Sub 'www.${DomainName}'
          HostedZoneId: !Ref HostedZone
      ValidationMethod: DNS

  DNSRecord:
    Type: AWS::Route53::RecordSetGroup
    Properties:
      HostedZoneId: !Ref HostedZone
      RecordSets:
        - Name: !Ref DomainName
          Type: A
          AliasTarget:
            DNSName: !GetAtt CloudFrontDistribution.DomainName
            HostedZoneId: Z2FDTNDATAQYW2
        - Name: !Sub 'www.${DomainName}'
          Type: A
          AliasTarget:
            DNSName: !GetAtt CloudFrontDistribution.DomainName
            HostedZoneId: Z2FDTNDATAQYW2

Outputs:
  WebsiteURL:
    Value: !Sub 'https://${DomainName}'
    Description: URL for website hosted on S3
  
  S3BucketSecureURL:
    Value: !Sub 'https://${S3Bucket.DomainName}'
    Description: Name of S3 bucket to hold website content
  
  CloudFrontDistributionId:
    Value: !Ref CloudFrontDistribution
    Description: CloudFront Distribution ID
  
  CloudFrontDomainName:
    Value: !GetAtt CloudFrontDistribution.DomainName
    Description: CloudFront Distribution Domain Name
  
  HostedZoneId:
    Value: !Ref HostedZone
    Description: Route53 Hosted Zone ID
  
  SSLCertificateArn:
    Value: !Ref SSLCertificate
    Description: SSL Certificate ARN
  
  NameServers:
    Value: !Join [', ', !GetAtt HostedZone.NameServers]
    Description: Name servers for the hosted zone
"""

    def check_credentials(self):
        """Test AWS credentials"""
        try:
            identity = self.sts.get_caller_identity()
            print_status("AWS credentials validated")
            print_info(f"Account ID: {identity['Account']}")
            print_info(f"User/Role: {identity['Arn']}")
            return True
        except Exception as e:
            print_error(f"AWS credentials invalid: {str(e)}")
            return False

    def deploy_stack(self, domain):
        """Deploy CloudFormation stack"""
        stack_name = self.get_stack_name(domain)
        
        print_header(f"Deploying AWS Infrastructure for {domain}...")
        
        template = self.get_cloudformation_template()
        
        try:
            # Create or update stack
            try:
                self.cloudformation.describe_stacks(StackName=stack_name)
                print_info("Stack exists, updating...")
                operation = 'UPDATE'
                self.cloudformation.update_stack(
                    StackName=stack_name,
                    TemplateBody=template,
                    Parameters=[
                        {
                            'ParameterKey': 'DomainName',
                            'ParameterValue': domain
                        }
                    ],
                    Capabilities=['CAPABILITY_IAM']
                )
            except ClientError as e:
                if 'does not exist' in str(e):
                    print_info("Creating new stack...")
                    operation = 'CREATE'
                    self.cloudformation.create_stack(
                        StackName=stack_name,
                        TemplateBody=template,
                        Parameters=[
                            {
                                'ParameterKey': 'DomainName',
                                'ParameterValue': domain
                            }
                        ],
                        Capabilities=['CAPABILITY_IAM']
                    )
                else:
                    raise e

            # Wait for stack operation to complete
            print_info("Waiting for stack operation to complete...")
            print_warning("This may take 10-15 minutes for SSL certificate validation...")
            
            if operation == 'CREATE':
                waiter = self.cloudformation.get_waiter('stack_create_complete')
            else:
                waiter = self.cloudformation.get_waiter('stack_update_complete')
            
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={
                    'Delay': 30,
                    'MaxAttempts': 120  # 60 minutes max
                }
            )
            
            print_status("Infrastructure deployed successfully")
            return True
            
        except Exception as e:
            print_error(f"Stack deployment failed: {str(e)}")
            return False

    def get_stack_outputs(self, domain):
        """Get CloudFormation stack outputs"""
        stack_name = self.get_stack_name(domain)
        
        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            outputs = response['Stacks'][0].get('Outputs', [])
            
            output_dict = {}
            for output in outputs:
                output_dict[output['OutputKey']] = output['OutputValue']
            
            return output_dict
        except Exception as e:
            print_error(f"Failed to get stack outputs: {str(e)}")
            return {}

    def display_stack_info(self, domain):
        """Display stack information"""
        outputs = self.get_stack_outputs(domain)
        
        if not outputs:
            return
        
        print()
        print_header("Deployment Complete!")
        print()
        print_info(f"Website URL: {outputs.get('WebsiteURL', 'N/A')}")
        print_info(f"S3 Bucket: {domain}")
        print_info(f"CloudFront Distribution ID: {outputs.get('CloudFrontDistributionId', 'N/A')}")
        print()
        
        # Display name servers
        name_servers = outputs.get('NameServers', '')
        if name_servers:
            print(f"{Colors.YELLOW}{Emojis.CLIPBOARD} NAME SERVERS (Add these to your domain registrar):{Colors.NC}")
            for i, ns in enumerate(name_servers.split(', '), 1):
                print(f"   {i}. {ns}")
            print()
            
        print_warning("DNS propagation can take 24-48 hours")

    def upload_files(self, domain, folder_path):
        """Upload website files to S3"""
        if not os.path.exists(folder_path):
            print_error(f"Website folder '{folder_path}' does not exist")
            return False
        
        print_header(f"Uploading website files from {folder_path}...")
        
        try:
            # Upload files
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, folder_path)
                    s3_key = relative_path.replace('\\', '/')  # Handle Windows paths
                    
                    # Determine content type
                    content_type = self.get_content_type(file)
                    
                    self.s3.upload_file(
                        local_path,
                        domain,
                        s3_key,
                        ExtraArgs={'ContentType': content_type}
                    )
                    print_info(f"Uploaded: {s3_key}")
            
            print_status("Files uploaded successfully")
            
            # Invalidate CloudFront cache
            outputs = self.get_stack_outputs(domain)
            cloudfront_id = outputs.get('CloudFrontDistributionId')
            
            if cloudfront_id:
                print_info("Invalidating CloudFront cache...")
                self.cloudfront.create_invalidation(
                    DistributionId=cloudfront_id,
                    InvalidationBatch={
                        'Paths': {
                            'Quantity': 1,
                            'Items': ['/*']
                        },
                        'CallerReference': str(int(time.time()))
                    }
                )
                print_status("CloudFront cache invalidated")
            
            return True
            
        except Exception as e:
            print_error(f"File upload failed: {str(e)}")
            return False

    def get_content_type(self, filename):
        """Get content type based on file extension"""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.xml': 'application/xml'
        }
        return content_types.get(ext, 'binary/octet-stream')

    def create_sample_website(self, domain):
        """Create and upload a sample website"""
        print_info("Creating sample website...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample HTML
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to {domain}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 600px;
            margin: 1rem;
        }}
        h1 {{
            color: #333;
            margin-bottom: 1rem;
        }}
        .emoji {{
            font-size: 3rem;
            margin-bottom: 1rem;
        }}
        .info {{
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }}
        .badge {{
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 3px;
            font-size: 0.8rem;
            margin: 0.2rem;
        }}
        .python-badge {{
            background: #3776ab;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            margin: 1rem 0;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="emoji">🚀</div>
        <h1>Welcome to {domain}</h1>
        <p>Your website is now live on AWS!</p>
        
        <div class="info">
            <h3>Powered by:</h3>
            <span class="badge">Amazon S3</span>
            <span class="badge">CloudFront CDN</span>
            <span class="badge">Route53 DNS</span>
            <span class="badge">SSL Certificate</span>
        </div>
        
        <div class="python-badge">
            🐍 Deployed with Python Script
        </div>
        
        <p>Replace this file with your own <code>index.html</code> to get started.</p>
        <p><small>Deployed with AWS Static Website Deployer (Python)</small></p>
    </div>
</body>
</html>"""
            
            # Write HTML file
            with open(os.path.join(temp_dir, 'index.html'), 'w') as f:
                f.write(html_content)
            
            # Upload sample website
            self.upload_files(domain, temp_dir)
            
        print_status("Sample website deployed")

    def cleanup_stack(self, domain):
        """Clean up all AWS resources for a domain"""
        stack_name = self.get_stack_name(domain)
        
        print_header(f"Cleaning up AWS resources for {domain}...")
        
        # Empty S3 buckets first
        self.empty_s3_buckets(domain)
        
        try:
            # Check if stack exists
            self.cloudformation.describe_stacks(StackName=stack_name)
            
            print_info(f"Deleting CloudFormation stack: {stack_name}")
            self.cloudformation.delete_stack(StackName=stack_name)
            
            print_info("Waiting for stack deletion to complete...")
            print_warning("This may take several minutes...")
            
            waiter = self.cloudformation.get_waiter('stack_delete_complete')
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={
                    'Delay': 30,
                    'MaxAttempts': 60  # 30 minutes max
                }
            )
            
            print_status("Stack deleted successfully")
            return True
            
        except ClientError as e:
            if 'does not exist' in str(e):
                print_info(f"CloudFormation stack {stack_name} does not exist")
                return True
            else:
                print_error(f"Stack deletion failed: {str(e)}")
                return False

    def empty_s3_buckets(self, domain):
        """Empty S3 buckets before deletion"""
        print_info("Emptying S3 buckets...")
        
        buckets = [domain, f"www.{domain}"]
        
        for bucket_name in buckets:
            try:
                # Check if bucket exists
                self.s3.head_bucket(Bucket=bucket_name)
                
                print_info(f"Emptying bucket: {bucket_name}")
                
                # List and delete all objects
                paginator = self.s3.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=bucket_name)
                
                for page in pages:
                    if 'Contents' in page:
                        objects = [{'Key': obj['Key']} for obj in page['Contents']]
                        self.s3.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': objects}
                        )
                
                print_status(f"Bucket {bucket_name} emptied")
                
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    print_info(f"Bucket {bucket_name} does not exist")
                else:
                    print_warning(f"Error emptying bucket {bucket_name}: {str(e)}")

    def get_stack_status(self, domain):
        """Get status of deployed stack"""
        stack_name = self.get_stack_name(domain)
        
        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            print_header(f"Status for {domain}")
            print()
            print_info(f"Stack Name: {stack_name}")
            print_info(f"Stack Status: {stack['StackStatus']}")
            print_info(f"Creation Time: {stack['CreationTime']}")
            
            if 'LastUpdatedTime' in stack:
                print_info(f"Last Updated: {stack['LastUpdatedTime']}")
            
            # Display outputs
            outputs = self.get_stack_outputs(domain)
            if outputs:
                print()
                print_info("Stack Outputs:")
                for key, value in outputs.items():
                    print(f"  • {key}: {value}")
            
            return True
            
        except ClientError as e:
            if 'does not exist' in str(e):
                print_info(f"No stack found for domain: {domain}")
                return False
            else:
                print_error(f"Error getting stack status: {str(e)}")
                return False


def main():
    parser = argparse.ArgumentParser(
        description='AWS Static Website Deployer - Python Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python aws-website-deployer.py deploy example.com
  python aws-website-deployer.py deploy example.com --website-folder ./website
  python aws-website-deployer.py cleanup example.com
  python aws-website-deployer.py status example.com
        """
    )
    
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy website infrastructure')
    deploy_parser.add_argument('domain', help='Domain name for the website')
    deploy_parser.add_argument('--website-folder', help='Path to website files folder')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up all AWS resources')
    cleanup_parser.add_argument('domain', help='Domain name to clean up')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get deployment status')
    status_parser.add_argument('domain', help='Domain name to check')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    print()
    print_header("AWS Static Website Deployer - Python Edition")
    print()
    
    # Initialize deployer
    deployer = AWSWebsiteDeployer(region=args.region)
    
    # Validate domain
    deployer.validate_domain(args.domain)
    
    # Check credentials
    if not deployer.check_credentials():
        sys.exit(1)
    
    # Execute command
    if args.command == 'deploy':
        # Deploy infrastructure
        if not deployer.deploy_stack(args.domain):
            sys.exit(1)
        
        # Display info
        deployer.display_stack_info(args.domain)
        
        # Handle file upload
        if args.website_folder:
            if not deployer.upload_files(args.domain, args.website_folder):
                sys.exit(1)
        else:
            print_info("No website folder specified, creating sample website...")
            deployer.create_sample_website(args.domain)
        
        print()
        print_header("🎉 Deployment Complete!")
        print()
        print_info("Next steps:")
        print("1. Add the name servers to your domain registrar")
        print("2. Wait 24-48 hours for DNS propagation")
        print(f"3. Visit https://{args.domain} to see your website")
        print()
        
    elif args.command == 'cleanup':
        # Confirmation
        print_warning(f"⚠️  WARNING: This will permanently delete all AWS resources for {args.domain}")
        print()
        print("This includes:")
        print("• S3 buckets and all website files")
        print("• CloudFront distribution")
        print("• Route53 hosted zone")
        print("• SSL certificate")
        print()
        
        confirmation = input("Are you sure you want to continue? (type 'yes' to confirm): ")
        if confirmation != 'yes':
            print_info("Cleanup cancelled")
            sys.exit(0)
        
        if not deployer.cleanup_stack(args.domain):
            sys.exit(1)
        
        print_status("Cleanup completed!")
        
    elif args.command == 'status':
        if not deployer.get_stack_status(args.domain):
            sys.exit(1)


if __name__ == '__main__':
    main()