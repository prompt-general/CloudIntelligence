import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

class IAMGenerator:
    """Generate IAM roles and policies for AWS integration."""
    
    AWS_READ_ONLY_POLICY = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    # CloudTrail
                    "cloudtrail:LookupEvents",
                    "cloudtrail:GetTrail",
                    "cloudtrail:DescribeTrails",
                    "cloudtrail:GetEventSelectors",
                    
                    # CloudWatch
                    "cloudwatch:GetMetricData",
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:ListMetrics",
                    "cloudwatch:DescribeAlarms",
                    
                    # Cost Explorer
                    "ce:GetCostAndUsage",
                    "ce:GetCostForecast",
                    "ce:GetDimensionValues",
                    "ce:GetTags",
                    
                    # AWS Config
                    "config:Describe*",
                    "config:Get*",
                    "config:List*",
                    "config:BatchGet*",
                    
                    # Security Hub
                    "securityhub:GetFindings",
                    "securityhub:ListFindings",
                    "securityhub:DescribeHub",
                    
                    # Resource Explorer
                    "resource-explorer-2:Search",
                    "resource-explorer-2:ListIndexes",
                    "resource-explorer-2:ListViews",
                    
                    # EC2
                    "ec2:Describe*",
                    "ec2:Get*",
                    
                    # S3
                    "s3:GetBucket*",
                    "s3:GetObject*",
                    "s3:List*",
                    
                    # RDS
                    "rds:Describe*",
                    "rds:List*",
                    
                    # IAM
                    "iam:Get*",
                    "iam:List*",
                    "iam:GenerateServiceLastAccessedDetails",
                    
                    # VPC
                    "vpc:Describe*",
                    "vpc:Get*",
                    
                    # Lambda
                    "lambda:Get*",
                    "lambda:List*",
                    
                    # CloudFormation
                    "cloudformation:Describe*",
                    "cloudformation:Get*",
                    "cloudformation:List*",
                    
                    # EventBridge
                    "events:Describe*",
                    "events:List*",
                ],
                "Resource": "*"
            }
        ]
    }
    
    @classmethod
    def generate_cloudformation_template(
        cls, 
        external_id: str, 
        role_name: str = "CloudIntelligenceReadOnlyRole"
    ) -> str:
        """Generate CloudFormation template for AWS integration."""
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "CloudIntelligence AWS Integration Role",
            "Parameters": {
                "ExternalId": {
                    "Type": "String",
                    "Description": "External ID for secure cross-account access"
                }
            },
            "Resources": {
                "CloudIntelligenceReadOnlyRole": {
                    "Type": "AWS::IAM::Role",
                    "Properties": {
                        "RoleName": role_name,
                        "AssumeRolePolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {
                                        "AWS": "arn:aws:iam::YOUR_SAAS_ACCOUNT:root"  # Replace with SaaS account
                                    },
                                    "Action": "sts:AssumeRole",
                                    "Condition": {
                                        "StringEquals": {
                                            "sts:ExternalId": {"Ref": "ExternalId"}
                                        }
                                    }
                                }
                            ]
                        },
                        "Policies": [
                            {
                                "PolicyName": "CloudIntelligenceReadOnlyAccess",
                                "PolicyDocument": cls.AWS_READ_ONLY_POLICY
                            }
                        ],
                        "MaxSessionDuration": 3600
                    }
                }
            },
            "Outputs": {
                "RoleArn": {
                    "Description": "ARN of the created IAM role",
                    "Value": {"Fn::GetAtt": ["CloudIntelligenceReadOnlyRole", "Arn"]}
                }
            }
        }
        
        return yaml.dump(template, default_flow_style=False)
    
    @classmethod
    def generate_terraform_config(
        cls,
        external_id: str,
        role_name: str = "cloud_intelligence_read_only"
    ) -> str:
        """Generate Terraform configuration for AWS integration."""
        tf_config = f'''
# CloudIntelligence AWS Integration
# Generated for secure read-only access

variable "external_id" {{
  description = "External ID for secure cross-account access"
  type        = string
  default     = "{external_id}"
}}

# IAM Role for CloudIntelligence
resource "aws_iam_role" "cloud_intelligence" {{
  name = "{role_name}"
  
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Effect = "Allow"
        Principal = {{
          AWS = "arn:aws:iam::YOUR_SAAS_ACCOUNT:root"  # Replace with SaaS account
        }}
        Action = "sts:AssumeRole"
        Condition = {{
          StringEquals = {{
            "sts:ExternalId" = var.external_id
          }}
        }}
      }}
    ]
  }})
}}

# IAM Policy for read-only access
resource "aws_iam_policy" "cloud_intelligence_read_only" {{
  name        = "CloudIntelligenceReadOnlyAccess"
  description = "Read-only access for CloudIntelligence platform"
  
  policy = jsonencode({json.dumps(cls.AWS_READ_ONLY_POLICY, indent=2)})
}}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "cloud_intelligence" {{
  role       = aws_iam_role.cloud_intelligence.name
  policy_arn = aws_iam_policy.cloud_intelligence_read_only.arn
}}

# Output the role ARN
output "cloud_intelligence_role_arn" {{
  value = aws_iam_role.cloud_intelligence.arn
  description = "ARN of the IAM role for CloudIntelligence access"
}}
'''
        return tf_config
    
    @classmethod
    def generate_external_id(cls) -> str:
        """Generate a secure external ID."""
        import secrets
        return secrets.token_urlsafe(32)