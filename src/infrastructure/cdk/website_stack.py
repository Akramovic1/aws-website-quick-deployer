"""
AWS CDK Stack for Static Website Deployment
"""
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_iam as iam,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from constructs import Construct
from typing import Dict, Any


class StaticWebsiteStack(Stack):
    """CDK Stack for static website deployment"""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        domain_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.domain_name = domain_name
        self.www_domain = f"www.{domain_name}"
        
        # Create resources
        self.hosted_zone = self._create_hosted_zone()
        self.certificate = self._create_certificate()
        self.bucket = self._create_s3_bucket()
        self.oac = self._create_origin_access_control()
        self.distribution = self._create_cloudfront_distribution()
        self._create_bucket_policy()
        self._create_dns_records()
        
        # Outputs
        self._create_outputs()
    
    def _create_hosted_zone(self) -> route53.HostedZone:
        """Create Route53 hosted zone"""
        return route53.HostedZone(
            self, "HostedZone",
            zone_name=self.domain_name,
            comment=f"Hosted zone for {self.domain_name}"
        )
    
    def _create_certificate(self) -> acm.Certificate:
        """Create ACM certificate with DNS validation"""
        return acm.Certificate(
            self, "Certificate",
            domain_name=self.domain_name,
            subject_alternative_names=[self.www_domain],
            validation=acm.CertificateValidation.from_dns(self.hosted_zone),
            removal_policy=RemovalPolicy.DESTROY
        )
    
    def _create_s3_bucket(self) -> s3.Bucket:
        """Create S3 bucket for website hosting"""
        return s3.Bucket(
            self, "WebsiteBucket",
            bucket_name=self.domain_name,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,  # For easier cleanup in dev
        )
    
    def _create_origin_access_control(self) -> cloudfront.S3OriginAccessControl:
        """Create Origin Access Control"""
        return cloudfront.S3OriginAccessControl(
            self, "OAC",
            description=f"OAC for {self.domain_name}",
            origin_access_control_name=f"{self.domain_name}-oac",
            signing_behavior=cloudfront.SigningBehavior.ALWAYS,
            signing_protocol=cloudfront.SigningProtocol.SIGV4
        )
    
    def _create_cloudfront_distribution(self) -> cloudfront.Distribution:
        """Create CloudFront distribution"""
        return cloudfront.Distribution(
            self, "Distribution",
            default_root_object="index.html",
            domain_names=[self.domain_name, self.www_domain],
            certificate=self.certificate,
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin(
                    bucket=self.bucket,
                    origin_access_control=self.oac
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True
            ),
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=404,
                    response_page_path="/404.html",
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                )
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            http_version=cloudfront.HttpVersion.HTTP2_AND_3,
            enable_ipv6=True
        )
    
    def _create_bucket_policy(self):
        """Create S3 bucket policy for CloudFront access"""
        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontAccessOnly",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[f"{self.bucket.bucket_arn}/*"],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{self.account}:distribution/{self.distribution.distribution_id}"
                    }
                }
            )
        )
    
    def _create_dns_records(self):
        """Create Route53 A records"""
        # Root domain A record
        route53.ARecord(
            self, "AliasRecord",
            zone=self.hosted_zone,
            record_name=self.domain_name,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.distribution)
            )
        )
        
        # WWW subdomain A record
        route53.ARecord(
            self, "WWWAliasRecord",
            zone=self.hosted_zone,
            record_name=self.www_domain,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.distribution)
            )
        )
    
    def _create_outputs(self):
        """Create stack outputs"""
        CfnOutput(
            self, "WebsiteURL",
            value=f"https://{self.domain_name}",
            description="Website URL"
        )
        
        CfnOutput(
            self, "DistributionId",
            value=self.distribution.distribution_id,
            description="CloudFront Distribution ID"
        )
        
        CfnOutput(
            self, "BucketName",
            value=self.bucket.bucket_name,
            description="S3 Bucket Name"
        )
        
        CfnOutput(
            self, "HostedZoneId",
            value=self.hosted_zone.hosted_zone_id,
            description="Route53 Hosted Zone ID"
        )
        
        CfnOutput(
            self, "NameServers",
            value=",".join(self.hosted_zone.hosted_zone_name_servers),
            description="Name servers for domain registrar"
        )