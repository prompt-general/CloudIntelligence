from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import boto3
from botocore.exceptions import ClientError

class SecuritySeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityCategory(Enum):
    IDENTITY = "identity"
    NETWORK = "network"
    DATA = "data"
    COMPLIANCE = "compliance"
    CONFIGURATION = "configuration"

@dataclass
class SecurityFinding:
    id: str
    resource_id: str
    resource_type: str
    account_id: str
    region: str
    rule_id: str
    title: str
    description: str
    severity: SecuritySeverity
    category: SecurityCategory
    remediation: str
    evidence: Dict[str, Any]
    detected_at: datetime
    status: str = "open"
    risk_score: float = 0.0

class SecurityScanner:
    """Automated security vulnerability scanner for cloud resources."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rules = self._load_security_rules()
    
    async def scan_organization(self, organization_id: str) -> List[SecurityFinding]:
        """Run comprehensive security scan for an organization."""
        from app.models.cloud_account import CloudAccount
        from app.models.resource import Resource
        
        findings = []
        
        # Get all active cloud accounts
        result = await self.db.execute(
            select(CloudAccount).where(
                and_(
                    CloudAccount.organization_id == organization_id,
                    CloudAccount.is_active == True
                )
            )
        )
        accounts = result.scalars().all()
        
        for account in accounts:
            account_findings = await self.scan_account(account)
            findings.extend(account_findings)
        
        # Run cross-account checks
        cross_account_findings = await self._run_cross_account_checks(accounts)
        findings.extend(cross_account_findings)
        
        # Calculate risk scores
        for finding in findings:
            finding.risk_score = self._calculate_risk_score(finding)
        
        return findings
    
    async def scan_account(self, account) -> List[SecurityFinding]:
        """Scan a single cloud account."""
        findings = []
        
        if account.provider == "aws":
            aws_findings = await self._scan_aws_account(account)
            findings.extend(aws_findings)
        
        return findings
    
    async def _scan_aws_account(self, account) -> List[SecurityFinding]:
        """Scan AWS account for security issues."""
        findings = []
        
        try:
            # Initialize AWS session
            import boto3
            from app.services.aws.client import AWSClient
            
            aws_client = AWSClient()
            session = await aws_client.get_session(
                account.role_arn,
                account.external_id,
                account.regions[0] if account.regions else "us-east-1"
            )
            
            # Run IAM security checks
            iam_findings = await self._scan_aws_iam(session, account)
            findings.extend(iam_findings)
            
            # Run S3 security checks
            s3_findings = await self._scan_aws_s3(session, account)
            findings.extend(s3_findings)
            
            # Run EC2 security checks
            ec2_findings = await self._scan_aws_ec2(session, account)
            findings.extend(ec2_findings)
            
            # Run RDS security checks
            rds_findings = await self._scan_aws_rds(session, account)
            findings.extend(rds_findings)
            
            # Run VPC security checks
            vpc_findings = await self._scan_aws_vpc(session, account)
            findings.extend(vpc_findings)
            
            # Run CloudTrail checks
            cloudtrail_findings = await self._scan_aws_cloudtrail(session, account)
            findings.extend(cloudtrail_findings)
            
            # Run Security Hub findings (if enabled)
            security_hub_findings = await self._scan_aws_security_hub(session, account)
            findings.extend(security_hub_findings)
            
        except Exception as e:
            print(f"Error scanning AWS account {account.account_id}: {e}")
        
        return findings
    
    async def _scan_aws_iam(self, session, account) -> List[SecurityFinding]:
        """Scan AWS IAM for security issues."""
        findings = []
        
        def _check_iam():
            iam = session.client('iam')
            
            # Check for IAM users without MFA
            users = iam.list_users()['Users']
            for user in users:
                mfa_devices = iam.list_mfa_devices(UserName=user['UserName'])['MFADevices']
                
                if not mfa_devices:
                    findings.append(SecurityFinding(
                        id=f"iam_no_mfa_{user['UserId']}",
                        resource_id=user['Arn'],
                        resource_type="AWS::IAM::User",
                        account_id=account.account_id,
                        region="global",
                        rule_id="IAM_NO_MFA",
                        title="IAM User Without MFA",
                        description=f"IAM user {user['UserName']} does not have Multi-Factor Authentication enabled",
                        severity=SecuritySeverity.HIGH,
                        category=SecurityCategory.IDENTITY,
                        remediation="Enable MFA for the IAM user and enforce MFA for console access",
                        evidence={
                            "user_name": user['UserName'],
                            "arn": user['Arn'],
                            "created_date": user['CreateDate'].isoformat()
                        },
                        detected_at=datetime.utcnow()
                    ))
            
            # Check for IAM policies with admin privileges
            policies = iam.list_policies(Scope='Local', OnlyAttached=True)['Policies']
            for policy in policies:
                if self._is_admin_policy(policy['Arn'], iam):
                    findings.append(SecurityFinding(
                        id=f"iam_admin_policy_{policy['PolicyId']}",
                        resource_id=policy['Arn'],
                        resource_type="AWS::IAM::Policy",
                        account_id=account.account_id,
                        region="global",
                        rule_id="IAM_ADMIN_POLICY",
                        title="IAM Policy With Admin Privileges",
                        description=f"IAM policy {policy['PolicyName']} has administrative privileges",
                        severity=SecuritySeverity.CRITICAL,
                        category=SecurityCategory.IDENTITY,
                        remediation="Apply principle of least privilege. Review and restrict policy permissions.",
                        evidence={
                            "policy_name": policy['PolicyName'],
                            "arn": policy['Arn'],
                            "description": policy.get('Description', '')
                        },
                        detected_at=datetime.utcnow()
                    ))
            
            # Check for access keys older than 90 days
            for user in users:
                try:
                    access_keys = iam.list_access_keys(UserName=user['UserName'])['AccessKeyMetadata']
                    for key in access_keys:
                        key_age = (datetime.utcnow() - key['CreateDate'].replace(tzinfo=None)).days
                        if key_age > 90:
                            findings.append(SecurityFinding(
                                id=f"iam_old_key_{key['AccessKeyId']}",
                                resource_id=key['AccessKeyId'],
                                resource_type="AWS::IAM::AccessKey",
                                account_id=account.account_id,
                                region="global",
                                rule_id="IAM_OLD_ACCESS_KEY",
                                title="Old IAM Access Key",
                                description=f"IAM access key for user {user['UserName']} is {key_age} days old",
                                severity=SecuritySeverity.MEDIUM,
                                category=SecurityCategory.IDENTITY,
                                remediation="Rotate access keys every 90 days or less",
                                evidence={
                                    "user_name": user['UserName'],
                                    "access_key_id": key['AccessKeyId'],
                                    "created_date": key['CreateDate'].isoformat(),
                                    "age_days": key_age
                                },
                                detected_at=datetime.utcnow()
                            ))
                except Exception:
                    continue
            
            return findings
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check_iam)
    
    async def _scan_aws_s3(self, session, account) -> List[SecurityFinding]:
        """Scan AWS S3 for security issues."""
        findings = []
        
        def _check_s3():
            s3 = session.client('s3')
            s3_client = session.client('s3control')
            
            try:
                # Get all buckets
                buckets = s3.list_buckets()['Buckets']
                
                for bucket in buckets:
                    bucket_name = bucket['Name']
                    
                    try:
                        # Check bucket ACL
                        acl = s3.get_bucket_acl(Bucket=bucket_name)
                        for grant in acl['Grants']:
                            grantee = grant.get('Grantee', {})
                            if grantee.get('Type') == 'Group' and grantee.get('URI') == 'http://acs.amazonaws.com/groups/global/AllUsers':
                                findings.append(SecurityFinding(
                                    id=f"s3_public_acl_{bucket_name}",
                                    resource_id=f"arn:aws:s3:::{bucket_name}",
                                    resource_type="AWS::S3::Bucket",
                                    account_id=account.account_id,
                                    region="us-east-1",  # S3 is global
                                    rule_id="S3_PUBLIC_ACL",
                                    title="Public S3 Bucket",
                                    description=f"S3 bucket {bucket_name} has public ACL grants",
                                    severity=SecuritySeverity.CRITICAL,
                                    category=SecurityCategory.DATA,
                                    remediation="Remove public ACL grants and enable block public access",
                                    evidence={
                                        "bucket_name": bucket_name,
                                        "grant": grant,
                                        "permission": grant.get('Permission')
                                    },
                                    detected_at=datetime.utcnow()
                                ))
                        
                        # Check bucket policy for public access
                        try:
                            policy = s3.get_bucket_policy(Bucket=bucket_name)['Policy']
                            policy_json = json.loads(policy)
                            if self._is_public_s3_policy(policy_json):
                                findings.append(SecurityFinding(
                                    id=f"s3_public_policy_{bucket_name}",
                                    resource_id=f"arn:aws:s3:::{bucket_name}",
                                    resource_type="AWS::S3::Bucket",
                                    account_id=account.account_id,
                                    region="us-east-1",
                                    rule_id="S3_PUBLIC_POLICY",
                                    title="S3 Bucket With Public Policy",
                                    description=f"S3 bucket {bucket_name} has a policy allowing public access",
                                    severity=SecuritySeverity.CRITICAL,
                                    category=SecurityCategory.DATA,
                                    remediation="Review and update bucket policy to restrict public access",
                                    evidence={
                                        "bucket_name": bucket_name,
                                        "policy": policy_json
                                    },
                                    detected_at=datetime.utcnow()
                                ))
                        except ClientError:
                            # No bucket policy
                            pass
                        
                        # Check for server-side encryption
                        try:
                            encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                            if not encryption.get('ServerSideEncryptionConfiguration', {}).get('Rules', []):
                                findings.append(SecurityFinding(
                                    id=f"s3_no_encryption_{bucket_name}",
                                    resource_id=f"arn:aws:s3:::{bucket_name}",
                                    resource_type="AWS::S3::Bucket",
                                    account_id=account.account_id,
                                    region="us-east-1",
                                    rule_id="S3_NO_ENCRYPTION",
                                    title="S3 Bucket Without Encryption",
                                    description=f"S3 bucket {bucket_name} does not have server-side encryption enabled",
                                    severity=SecuritySeverity.HIGH,
                                    category=SecurityCategory.DATA,
                                    remediation="Enable default encryption for the S3 bucket",
                                    evidence={
                                        "bucket_name": bucket_name
                                    },
                                    detected_at=datetime.utcnow()
                                ))
                        except ClientError:
                            # No encryption configured
                            findings.append(SecurityFinding(
                                id=f"s3_no_encryption_{bucket_name}",
                                resource_id=f"arn:aws:s3:::{bucket_name}",
                                resource_type="AWS::S3::Bucket",
                                account_id=account.account_id,
                                region="us-east-1",
                                rule_id="S3_NO_ENCRYPTION",
                                title="S3 Bucket Without Encryption",
                                description=f"S3 bucket {bucket_name} does not have server-side encryption enabled",
                                severity=SecuritySeverity.HIGH,
                                category=SecurityCategory.DATA,
                                remediation="Enable default encryption for the S3 bucket",
                                evidence={
                                    "bucket_name": bucket_name
                                },
                                detected_at=datetime.utcnow()
                            ))
                        
                        # Check for versioning (security best practice)
                        try:
                            versioning = s3.get_bucket_versioning(Bucket=bucket_name)
                            if versioning.get('Status') != 'Enabled':
                                findings.append(SecurityFinding(
                                    id=f"s3_no_versioning_{bucket_name}",
                                    resource_id=f"arn:aws:s3:::{bucket_name}",
                                    resource_type="AWS::S3::Bucket",
                                    account_id=account.account_id,
                                    region="us-east-1",
                                    rule_id="S3_NO_VERSIONING",
                                    title="S3 Bucket Without Versioning",
                                    description=f"S3 bucket {bucket_name} does not have versioning enabled",
                                    severity=SecuritySeverity.MEDIUM,
                                    category=SecurityCategory.DATA,
                                    remediation="Enable versioning for data protection and recovery",
                                    evidence={
                                        "bucket_name": bucket_name,
                                        "versioning_status": versioning.get('Status', 'Not enabled')
                                    },
                                    detected_at=datetime.utcnow()
                                ))
                        except ClientError:
                            pass
                    
                    except Exception as e:
                        print(f"Error checking S3 bucket {bucket_name}: {e}")
                        continue
            
            except Exception as e:
                print(f"Error listing S3 buckets: {e}")
            
            return findings
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check_s3)
    
    async def _scan_aws_ec2(self, session, account) -> List[SecurityFinding]:
        """Scan AWS EC2 for security issues."""
        findings = []
        
        def _check_ec2():
            ec2 = session.client('ec2')
            
            # Check for public EC2 instances
            instances = ec2.describe_instances()['Reservations']
            for reservation in instances:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    
                    # Check if instance has public IP
                    if instance.get('PublicIpAddress'):
                        # Check security groups
                        for sg in instance.get('SecurityGroups', []):
                            sg_id = sg['GroupId']
                            sg_rules = ec2.describe_security_group_rules(
                                Filters=[{'Name': 'group-id', 'Values': [sg_id]}]
                            )['SecurityGroupRules']
                            
                            for rule in sg_rules:
                                if rule.get('IsEgress', False):
                                    continue
                                
                                # Check for overly permissive rules
                                if self._is_overly_permissive_rule(rule):
                                    findings.append(SecurityFinding(
                                        id=f"ec2_public_{instance_id}_{sg_id}",
                                        resource_id=instance_id,
                                        resource_type="AWS::EC2::Instance",
                                        account_id=account.account_id,
                                        region=session.region_name,
                                        rule_id="EC2_PUBLIC_WITH_PERMISSIVE_SG",
                                        title="Public EC2 Instance with Permissive Security Group",
                                        description=f"EC2 instance {instance_id} is publicly accessible with overly permissive security group rules",
                                        severity=SecuritySeverity.HIGH,
                                        category=SecurityCategory.NETWORK,
                                        remediation="Restrict security group rules and consider moving to private subnet",
                                        evidence={
                                            "instance_id": instance_id,
                                            "public_ip": instance['PublicIpAddress'],
                                            "security_group_id": sg_id,
                                            "rule": rule
                                        },
                                        detected_at=datetime.utcnow()
                                    ))
                    
                    # Check for unencrypted EBS volumes
                    for block_device in instance.get('BlockDeviceMappings', []):
                        volume_id = block_device.get('Ebs', {}).get('VolumeId')
                        if volume_id:
                            try:
                                volume = ec2.describe_volumes(VolumeIds=[volume_id])['Volumes'][0]
                                if not volume.get('Encrypted', False):
                                    findings.append(SecurityFinding(
                                        id=f"ec2_unencrypted_volume_{volume_id}",
                                        resource_id=volume_id,
                                        resource_type="AWS::EBS::Volume",
                                        account_id=account.account_id,
                                        region=session.region_name,
                                        rule_id="EBS_UNENCRYPTED",
                                        title="Unencrypted EBS Volume",
                                        description=f"EBS volume {volume_id} attached to instance {instance_id} is not encrypted",
                                        severity=SecuritySeverity.HIGH,
                                        category=SecurityCategory.DATA,
                                        remediation="Encrypt the EBS volume or create an encrypted snapshot",
                                        evidence={
                                            "instance_id": instance_id,
                                            "volume_id": volume_id,
                                            "volume_type": volume.get('VolumeType'),
                                            "size_gb": volume.get('Size')
                                        },
                                        detected_at=datetime.utcnow()
                                    ))
                            except Exception:
                                continue
            
            return findings
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check_ec2)
    
    async def _scan_aws_rds(self, session, account) -> List[SecurityFinding]:
        """Scan AWS RDS for security issues."""
        findings = []
        
        def _check_rds():
            rds = session.client('rds')
            
            try:
                instances = rds.describe_db_instances()['DBInstances']
                
                for instance in instances:
                    instance_id = instance['DBInstanceIdentifier']
                    
                    # Check if RDS is publicly accessible
                    if instance.get('PubliclyAccessible', False):
                        findings.append(SecurityFinding(
                            id=f"rds_public_{instance_id}",
                            resource_id=instance_id,
                            resource_type="AWS::RDS::DBInstance",
                            account_id=account.account_id,
                            region=session.region_name,
                            rule_id="RDS_PUBLIC",
                            title="Publicly Accessible RDS Instance",
                            description=f"RDS instance {instance_id} is publicly accessible",
                            severity=SecuritySeverity.CRITICAL,
                            category=SecurityCategory.NETWORK,
                            remediation="Modify RDS instance to disable public accessibility",
                            evidence={
                                "db_instance_id": instance_id,
                                "engine": instance.get('Engine'),
                                "endpoint": instance.get('Endpoint', {}).get('Address')
                            },
                            detected_at=datetime.utcnow()
                        ))
                    
                    # Check for encryption
                    if not instance.get('StorageEncrypted', False):
                        findings.append(SecurityFinding(
                            id=f"rds_unencrypted_{instance_id}",
                            resource_id=instance_id,
                            resource_type="AWS::RDS::DBInstance",
                            account_id=account.account_id,
                            region=session.region_name,
                            rule_id="RDS_UNENCRYPTED",
                            title="Unencrypted RDS Instance",
                            description=f"RDS instance {instance_id} is not encrypted at rest",
                            severity=SecuritySeverity.HIGH,
                            category=SecurityCategory.DATA,
                            remediation="Enable encryption for the RDS instance (requires snapshot/restore)",
                            evidence={
                                "db_instance_id": instance_id,
                                "engine": instance.get('Engine'),
                                "allocated_storage": instance.get('AllocatedStorage')
                            },
                            detected_at=datetime.utcnow()
                        ))
                    
                    # Check for auto minor version upgrade
                    if not instance.get('AutoMinorVersionUpgrade', False):
                        findings.append(SecurityFinding(
                            id=f"rds_no_auto_upgrade_{instance_id}",
                            resource_id=instance_id,
                            resource_type="AWS::RDS::DBInstance",
                            account_id=account.account_id,
                            region=session.region_name,
                            rule_id="RDS_NO_AUTO_UPGRADE",
                            title="RDS Instance Without Auto Minor Version Upgrade",
                            description=f"RDS instance {instance_id} does not have auto minor version upgrade enabled",
                            severity=SecuritySeverity.MEDIUM,
                            category=SecurityCategory.COMPLIANCE,
                            remediation="Enable auto minor version upgrade for security patches",
                            evidence={
                                "db_instance_id": instance_id,
                                "engine_version": instance.get('EngineVersion')
                            },
                            detected_at=datetime.utcnow()
                        ))
            
            except Exception as e:
                print(f"Error checking RDS instances: {e}")
            
            return findings
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check_rds)
    
    async def _scan_aws_vpc(self, session, account) -> List[SecurityFinding]:
        """Scan AWS VPC for security issues."""
        findings = []
        
        def _check_vpc():
            ec2 = session.client('ec2')
            
            # Check default VPCs (security best practice)
            vpcs = ec2.describe_vpcs()['Vpcs']
            for vpc in vpcs:
                if vpc.get('IsDefault', False):
                    findings.append(SecurityFinding(
                        id=f"vpc_default_{vpc['VpcId']}",
                        resource_id=vpc['VpcId'],
                        resource_type="AWS::EC2::VPC",
                        account_id=account.account_id,
                        region=session.region_name,
                        rule_id="VPC_DEFAULT",
                        title="Default VPC in Use",
                        description=f"Default VPC {vpc['VpcId']} is being used",
                        severity=SecuritySeverity.MEDIUM,
                        category=SecurityCategory.NETWORK,
                        remediation="Create custom VPCs with proper network segmentation",
                        evidence={
                            "vpc_id": vpc['VpcId'],
                            "cidr_block": vpc.get('CidrBlock')
                        },
                        detected_at=datetime.utcnow()
                    ))
            
            # Check for VPC flow logs
            flow_logs = ec2.describe_flow_logs()['FlowLogs']
            vpcs_with_logs = {log['ResourceId'] for log in flow_logs}
            
            for vpc in vpcs:
                if vpc['VpcId'] not in vpcs_with_logs:
                    findings.append(SecurityFinding(
                        id=f"vpc_no_flow_logs_{vpc['VpcId']}",
                        resource_id=vpc['VpcId'],
                        resource_type="AWS::EC2::VPC",
                        account_id=account.account_id,
                        region=session.region_name,
                        rule_id="VPC_NO_FLOW_LOGS",
                        title="VPC Without Flow Logs",
                        description=f"VPC {vpc['VpcId']} does not have VPC flow logs enabled",
                        severity=SecuritySeverity.MEDIUM,
                        category=SecurityCategory.NETWORK,
                        remediation="Enable VPC flow logs for network traffic monitoring",
                        evidence={
                            "vpc_id": vpc['VpcId'],
                            "cidr_block": vpc.get('CidrBlock')
                        },
                        detected_at=datetime.utcnow()
                    ))
            
            return findings
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check_vpc)
    
    async def _scan_aws_cloudtrail(self, session, account) -> List[SecurityFinding]:
        """Scan AWS CloudTrail for security issues."""
        findings = []
        
        def _check_cloudtrail():
            cloudtrail = session.client('cloudtrail')
            
            try:
                trails = cloudtrail.describe_trails()['trailList']
                
                # Check for multi-region trail
                multi_region_trail = False
                for trail in trails:
                    if trail.get('IsMultiRegionTrail', False):
                        multi_region_trail = True
                        # Check if trail is logging
                        status = cloudtrail.get_trail_status(Name=trail['TrailARN'])
                        if not status.get('IsLogging', False):
                            findings.append(SecurityFinding(
                                id=f"cloudtrail_not_logging_{trail['TrailARN']}",
                                resource_id=trail['TrailARN'],
                                resource_type="AWS::CloudTrail::Trail",
                                account_id=account.account_id,
                                region="multi-region",
                                rule_id="CLOUDTRAIL_NOT_LOGGING",
                                title="CloudTrail Trail Not Logging",
                                description=f"CloudTrail trail {trail['Name']} is not logging",
                                severity=SecuritySeverity.CRITICAL,
                                category=SecurityCategory.COMPLIANCE,
                                remediation="Enable logging for the CloudTrail trail",
                                evidence={
                                    "trail_name": trail['Name'],
                                    "trail_arn": trail['TrailARN'],
                                    "is_multi_region": trail.get('IsMultiRegionTrail', False)
                                },
                                detected_at=datetime.utcnow()
                            ))
                        break
                
                if not multi_region_trail:
                    findings.append(SecurityFinding(
                        id=f"cloudtrail_no_multi_region",
                        resource_id="cloudtrail",
                        resource_type="AWS::CloudTrail::Account",
                        account_id=account.account_id,
                        region="global",
                        rule_id="CLOUDTRAIL_NO_MULTI_REGION",
                        title="No Multi-Region CloudTrail Trail",
                        description="No multi-region CloudTrail trail configured",
                        severity=SecuritySeverity.HIGH,
                        category=SecurityCategory.COMPLIANCE,
                        remediation="Create a multi-region CloudTrail trail for comprehensive audit logging",
                        evidence={},
                        detected_at=datetime.utcnow()
                    ))
            
            except Exception as e:
                print(f"Error checking CloudTrail: {e}")
            
            return findings
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check_cloudtrail)
    
    async def _scan_aws_security_hub(self, session, account) -> List[SecurityFinding]:
        """Import findings from AWS Security Hub."""
        findings = []
        
        def _check_security_hub():
            try:
                securityhub = session.client('securityhub')
                
                # Get findings from Security Hub
                security_hub_findings = securityhub.get_findings(
                    Filters={
                        'RecordState': [
                            {'Value': 'ACTIVE', 'Comparison': 'EQUALS'}
                        ],
                        'SeverityLabel': [
                            {'Value': 'CRITICAL', 'Comparison': 'EQUALS'},
                            {'Value': 'HIGH', 'Comparison': 'EQUALS'}
                        ]
                    },
                    MaxResults=100
                )['Findings']
                
                for sh_finding in security_hub_findings:
                    severity_map = {
                        'CRITICAL': SecuritySeverity.CRITICAL,
                        'HIGH': SecuritySeverity.HIGH,
                        'MEDIUM': SecuritySeverity.MEDIUM,
                        'LOW': SecuritySeverity.LOW
                    }
                    
                    findings.append(SecurityFinding(
                        id=f"security_hub_{sh_finding['Id']}",
                        resource_id=sh_finding.get('Resources', [{}])[0].get('Id', ''),
                        resource_type=sh_finding.get('ProductFields', {}).get('ResourceType', ''),
                        account_id=account.account_id,
                        region=sh_finding.get('Region', ''),
                        rule_id=sh_finding.get('GeneratorId', ''),
                        title=sh_finding.get('Title', ''),
                        description=sh_finding.get('Description', ''),
                        severity=severity_map.get(sh_finding.get('Severity', {}).get('Label', 'LOW'), SecuritySeverity.LOW),
                        category=SecurityCategory.CONFIGURATION,
                        remediation=sh_finding.get('Remediation', {}).get('Recommendation', {}).get('Text', ''),
                        evidence={
                            'aws_security_hub_finding': sh_finding
                        },
                        detected_at=datetime.utcnow()
                    ))
            
            except Exception as e:
                # Security Hub might not be enabled
                pass
            
            return findings
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check_security_hub)
    
    async def _run_cross_account_checks(self, accounts) -> List[SecurityFinding]:
        """Run security checks that span multiple accounts."""
        findings = []
        
        # Check for cross-account IAM trust relationships that are overly permissive
        # This would require analyzing IAM roles across accounts
        
        return findings
    
    def _is_admin_policy(self, policy_arn, iam_client) -> bool:
        """Check if an IAM policy has admin privileges."""
        try:
            policy = iam_client.get_policy(PolicyArn=policy_arn)['Policy']
            policy_version = iam_client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=policy['DefaultVersionId']
            )
            
            policy_document = policy_version['PolicyVersion']['Document']
            statements = policy_document.get('Statement', [])
            
            for statement in statements:
                if isinstance(statement, dict):
                    action = statement.get('Action', [])
                    effect = statement.get('Effect', 'Allow')
                    
                    # Check for admin-like permissions
                    if effect == 'Allow':
                        if action == '*' or (isinstance(action, list) and '*' in action):
                            return True
                        if 'iam:*' in action or (isinstance(action, list) and any('iam:*' in a for a in action)):
                            return True
        
        except Exception:
            return False
        
        return False
    
    def _is_public_s3_policy(self, policy_json: dict) -> bool:
        """Check if S3 bucket policy allows public access."""
        statements = policy_json.get('Statement', [])
        
        for statement in statements:
            if isinstance(statement, dict):
                effect = statement.get('Effect', '')
                principal = statement.get('Principal', {})
                action = statement.get('Action', [])
                
                # Check for public access
                if effect == 'Allow':
                    # Check if principal is public
                    if principal == '*' or (isinstance(principal, dict) and principal.get('AWS') == '*'):
                        # Check if actions allow public access
                        actions = [action] if isinstance(action, str) else action
                        public_actions = {'s3:GetObject', 's3:PutObject', 's3:*'}
                        
                        if any(a in public_actions for a in actions):
                            return True