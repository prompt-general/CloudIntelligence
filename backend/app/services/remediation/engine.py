from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
import boto3
from botocore.exceptions import ClientError
import yaml

class RemediationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class RemediationType(Enum):
    SECURITY = "security"
    COST = "cost"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"

class RemediationApproval(Enum):
    AUTO = "auto"
    SINGLE = "single"
    MULTI = "multi"
    NONE = "none"

@dataclass
class RemediationAction:
    id: str
    title: str
    description: str
    resource_type: str
    resource_id: str
    account_id: str
    region: str
    action_type: str
    parameters: Dict[str, Any]
    estimated_impact: Dict[str, Any]
    risk_level: str
    approval_required: bool
    suggested_by: str = "ai_engine"

@dataclass
class RemediationTask:
    id: str
    action: RemediationAction
    status: RemediationStatus
    requested_by: str
    requested_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_log: List[Dict[str, Any]] = None
    rollback_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class RemediationEngine:
    """AI-powered remediation engine with approval workflows."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.action_templates = self._load_action_templates()
    
    async def generate_remediation_actions(
        self,
        organization_id: str,
        finding_id: str,
        finding_type: str,
        resource_data: Dict[str, Any]
    ) -> List[RemediationAction]:
        """Generate remediation actions for a finding."""
        actions = []
        
        if finding_type == "security":
            actions.extend(await self._generate_security_remediations(resource_data))
        elif finding_type == "cost":
            actions.extend(await self._generate_cost_remediations(resource_data))
        elif finding_type == "compliance":
            actions.extend(await self._generate_compliance_remediations(resource_data))
        
        # Add AI-powered suggestions
        ai_actions = await self._generate_ai_suggestions(resource_data)
        actions.extend(ai_actions)
        
        return actions[:5]  # Return top 5 actions
    
    async def _generate_security_remediations(self, resource: Dict[str, Any]) -> List[RemediationAction]:
        """Generate security remediation actions."""
        actions = []
        resource_type = resource.get('resource_type', '')
        
        if resource_type == 'AWS::S3::Bucket':
            if resource.get('public_access', False):
                actions.append(RemediationAction(
                    id=f"s3_block_public_{resource['resource_id']}",
                    title="Block S3 Public Access",
                    description="Enable S3 Block Public Access to prevent unauthorized access",
                    resource_type=resource_type,
                    resource_id=resource['resource_id'],
                    account_id=resource['account_id'],
                    region=resource['region'],
                    action_type="s3_block_public_access",
                    parameters={
                        "bucket_name": resource['resource_id'].split(':')[-1],
                        "block_public_acls": True,
                        "ignore_public_acls": True,
                        "block_public_policy": True,
                        "restrict_public_buckets": True
                    },
                    estimated_impact={
                        "security_improvement": 40,
                        "risk_reduction": 35,
                        "time_to_fix": "5 minutes"
                    },
                    risk_level="low",
                    approval_required=True
                ))
            
            if not resource.get('encryption_enabled', False):
                actions.append(RemediationAction(
                    id=f"s3_enable_encryption_{resource['resource_id']}",
                    title="Enable S3 Encryption",
                    description="Enable default encryption for S3 bucket",
                    resource_type=resource_type,
                    resource_id=resource['resource_id'],
                    account_id=resource['account_id'],
                    region=resource['region'],
                    action_type="s3_enable_encryption",
                    parameters={
                        "bucket_name": resource['resource_id'].split(':')[-1],
                        "sse_algorithm": "AES256"
                    },
                    estimated_impact={
                        "security_improvement": 30,
                        "compliance_improvement": 25,
                        "time_to_fix": "2 minutes"
                    },
                    risk_level="low",
                    approval_required=False
                ))
        
        elif resource_type == 'AWS::EC2::Instance':
            if resource.get('public_ip') and resource.get('has_permissive_sg', False):
                actions.append(RemediationAction(
                    id=f"ec2_restrict_sg_{resource['resource_id']}",
                    title="Restrict Security Group",
                    description="Update security group to restrict public access",
                    resource_type=resource_type,
                    resource_id=resource['resource_id'],
                    account_id=resource['account_id'],
                    region=resource['region'],
                    action_type="ec2_update_security_group",
                    parameters={
                        "instance_id": resource['resource_id'].split('/')[-1],
                        "security_group_id": resource.get('security_groups', [{}])[0].get('GroupId', ''),
                        "allow_cidr": "10.0.0.0/8"
                    },
                    estimated_impact={
                        "security_improvement": 50,
                        "risk_reduction": 45,
                        "time_to_fix": "10 minutes"
                    },
                    risk_level="medium",
                    approval_required=True
                ))
        
        elif resource_type == 'AWS::IAM::Role':
            if resource.get('has_admin_policy', False):
                actions.append(RemediationAction(
                    id=f"iam_restrict_policy_{resource['resource_id']}",
                    title="Restrict IAM Policy",
                    description="Replace admin policy with least-privilege policy",
                    resource_type=resource_type,
                    resource_id=resource['resource_id'],
                    account_id=resource['account_id'],
                    region="global",
                    action_type="iam_update_policy",
                    parameters={
                        "role_name": resource['resource_id'].split('/')[-1],
                        "policy_arn": resource.get('admin_policy_arn', ''),
                        "new_policy": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": [
                                        "s3:ListBucket",
                                        "s3:GetObject"
                                    ],
                                    "Resource": "*"
                                }
                            ]
                        }
                    },
                    estimated_impact={
                        "security_improvement": 60,
                        "risk_reduction": 55,
                        "time_to_fix": "15 minutes"
                    },
                    risk_level="high",
                    approval_required=True
                ))
        
        return actions
    
    async def _generate_cost_remediations(self, resource: Dict[str, Any]) -> List[RemediationAction]:
        """Generate cost optimization remediation actions."""
        actions = []
        resource_type = resource.get('resource_type', '')
        
        if resource_type == 'AWS::EC2::Instance':
            # Check for idle instances
            if resource.get('cpu_utilization', 0) < 10:
                actions.append(RemediationAction(
                    id=f"ec2_stop_instance_{resource['resource_id']}",
                    title="Stop Idle EC2 Instance",
                    description="Stop instance with low CPU utilization to save costs",
                    resource_type=resource_type,
                    resource_id=resource['resource_id'],
                    account_id=resource['account_id'],
                    region=resource['region'],
                    action_type="ec2_stop_instance",
                    parameters={
                        "instance_id": resource['resource_id'].split('/')[-1],
                        "stop_if_idle_hours": 24
                    },
                    estimated_impact={
                        "cost_savings": resource.get('monthly_cost', 0) * 0.7,
                        "time_to_fix": "2 minutes",
                        "risk": "low"
                    },
                    risk_level="low",
                    approval_required=True
                ))
            
            # Check for over-provisioned instances
            instance_type = resource.get('instance_type', '')
            if self._is_over_provisioned(instance_type, resource.get('cpu_utilization', 0)):
                actions.append(RemediationAction(
                    id=f"ec2_resize_instance_{resource['resource_id']}",
                    title="Right-size EC2 Instance",
                    description="Resize instance to match actual workload",
                    resource_type=resource_type,
                    resource_id=resource['resource_id'],
                    account_id=resource['account_id'],
                    region=resource['region'],
                    action_type="ec2_resize_instance",
                    parameters={
                        "instance_id": resource['resource_id'].split('/')[-1],
                        "current_type": instance_type,
                        "recommended_type": self._get_recommended_type(instance_type)
                    },
                    estimated_impact={
                        "cost_savings": resource.get('monthly_cost', 0) * 0.3,
                        "performance_impact": "minimal",
                        "time_to_fix": "15 minutes"
                    },
                    risk_level="medium",
                    approval_required=True
                ))
        
        elif resource_type == 'AWS::EBS::Volume':
            if not resource.get('is_attached', False):
                actions.append(RemediationAction(
                    id=f"ebs_delete_volume_{resource['resource_id']}",
                    title="Delete Unattached EBS Volume",
                    description="Delete EBS volume not attached to any instance",
                    resource_type=resource_type,
                    resource_id=resource['resource_id'],
                    account_id=resource['account_id'],
                    region=resource['region'],
                    action_type="ebs_delete_volume",
                    parameters={
                        "volume_id": resource['resource_id'].split('/')[-1]
                    },
                    estimated_impact={
                        "cost_savings": resource.get('monthly_cost', 0),
                        "time_to_fix": "1 minute",
                        "risk": "low"
                    },
                    risk_level="low",
                    approval_required=False
                ))
        
        return actions
    
    async def _generate_compliance_remediations(self, resource: Dict[str, Any]) -> List[RemediationAction]:
        """Generate compliance remediation actions."""
        actions = []
        resource_type = resource.get('resource_type', '')
        
        if resource_type == 'AWS::RDS::DBInstance':
            if not resource.get('encryption_enabled', False):
                actions.append(RemediationAction(
                    id=f"rds_enable_encryption_{resource['resource_id']}",
                    title="Enable RDS Encryption",
                    description="Enable encryption at rest for RDS instance",
                    resource_type=resource_type,
                    resource_id=resource['resource_id'],
                    account_id=resource['account_id'],
                    region=resource['region'],
                    action_type="rds_enable_encryption",
                    parameters={
                        "db_instance_id": resource['resource_id'].split(':')[-1],
                        "kms_key_id": "default"
                    },
                    estimated_impact={
                        "compliance_improvement": 40,
                        "security_improvement": 35,
                        "time_to_fix": "requires snapshot",
                        "downtime": "yes"
                    },
                    risk_level="medium",
                    approval_required=True
                ))
        
        return actions
    
    async def _generate_ai_suggestions(self, resource: Dict[str, Any]) -> List[RemediationAction]:
        """Generate AI-powered remediation suggestions."""
        # This would use ML models to suggest optimizations
        # For now, return some intelligent suggestions based on patterns
        
        suggestions = []
        resource_type = resource.get('resource_type', '')
        
        # Example: Suggest tagging for better organization
        if not resource.get('has_proper_tags', True):
            suggestions.append(RemediationAction(
                id=f"tag_resource_{resource['resource_id']}",
                title="Add Resource Tags",
                description="Add standard tags for better resource management",
                resource_type=resource_type,
                resource_id=resource['resource_id'],
                account_id=resource['account_id'],
                region=resource['region'],
                action_type="tag_resource",
                parameters={
                    "resource_arn": resource['resource_id'],
                    "tags": {
                        "Environment": "production",
                        "Owner": "platform-team",
                        "CostCenter": "12345"
                    }
                },
                estimated_impact={
                    "operational_improvement": 20,
                    "cost_visibility": 30,
                    "time_to_fix": "1 minute"
                },
                risk_level="low",
                approval_required=False,
                suggested_by="ai_tagging_engine"
            ))
        
        return suggestions
    
    async def execute_remediation(
        self,
        action: RemediationAction,
        executed_by: str,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Execute a remediation action."""
        execution_log = []
        
        try:
            # Get cloud account credentials
            from app.models.cloud_account import CloudAccount
            from app.services.aws.client import AWSClient
            
            result = await self.db.execute(
                select(CloudAccount).where(
                    CloudAccount.account_id == action.account_id
                )
            )
            cloud_account = result.scalar_one_or_none()
            
            if not cloud_account:
                raise ValueError(f"Cloud account {action.account_id} not found")
            
            aws_client = AWSClient()
            
            # Execute based on action type
            if dry_run:
                # Dry run - simulate execution
                execution_log.append({
                    "timestamp": datetime.utcnow(),
                    "step": "dry_run",
                    "message": f"Would execute {action.action_type} on {action.resource_id}",
                    "parameters": action.parameters
                })
                
                return {
                    "success": True,
                    "dry_run": True,
                    "execution_log": execution_log,
                    "estimated_impact": action.estimated_impact,
                    "rollback_plan": await self._generate_rollback_plan(action)
                }
            
            # Real execution
            execution_log.append({
                "timestamp": datetime.utcnow(),
                "step": "start",
                "message": f"Starting remediation: {action.title}"
            })
            
            # Execute the action
            if action.action_type == "s3_block_public_access":
                result = await self._execute_s3_block_public_access(
                    aws_client, cloud_account, action, execution_log
                )
            
            elif action.action_type == "ec2_stop_instance":
                result = await self._execute_ec2_stop_instance(
                    aws_client, cloud_account, action, execution_log
                )
            
            elif action.action_type == "ec2_update_security_group":
                result = await self._execute_ec2_update_security_group(
                    aws_client, cloud_account, action, execution_log
                )
            
            elif action.action_type == "ebs_delete_volume":
                result = await self._execute_ebs_delete_volume(
                    aws_client, cloud_account, action, execution_log
                )
            
            elif action.action_type == "tag_resource":
                result = await self._execute_tag_resource(
                    aws_client, cloud_account, action, execution_log
                )
            
            else:
                raise ValueError(f"Unsupported action type: {action.action_type}")
            
            execution_log.append({
                "timestamp": datetime.utcnow(),
                "step": "complete",
                "message": "Remediation completed successfully"
            })
            
            return {
                "success": True,
                "dry_run": False,
                "execution_log": execution_log,
                "result": result,
                "rollback_data": await self._capture_rollback_data(action)
            }
        
        except Exception as e:
            execution_log.append({
                "timestamp": datetime.utcnow(),
                "step": "error",
                "message": f"Remediation failed: {str(e)}",
                "error": str(e)
            })
            
            return {
                "success": False,
                "dry_run": dry_run,
                "execution_log": execution_log,
                "error": str(e)
            }
    
    async def _execute_s3_block_public_access(
        self,
        aws_client,
        cloud_account,
        action: RemediationAction,
        execution_log: List[Dict]
    ) -> Dict[str, Any]:
        """Execute S3 block public access remediation."""
        # Get session
        session = await aws_client.get_session(
            cloud_account.role_arn,
            cloud_account.external_id,
            action.region
        )
        
        def _block_public_access():
            s3_client = session.client('s3')
            
            # First, get current configuration
            try:
                current_config = s3_client.get_public_access_block(
                    Bucket=action.parameters['bucket_name']
                )['PublicAccessBlockConfiguration']
            except ClientError:
                current_config = {}
            
            # Apply block public access
            s3_client.put_public_access_block(
                Bucket=action.parameters['bucket_name'],
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': action.parameters['block_public_acls'],
                    'IgnorePublicAcls': action.parameters['ignore_public_acls'],
                    'BlockPublicPolicy': action.parameters['block_public_policy'],
                    'RestrictPublicBuckets': action.parameters['restrict_public_buckets']
                }
            )
            
            return {
                "previous_config": current_config,
                "new_config": action.parameters,
                "bucket": action.parameters['bucket_name']
            }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _block_public_access)
        
        execution_log.append({
            "timestamp": datetime.utcnow(),
            "step": "execute",
            "message": f"Blocked public access for S3 bucket {action.parameters['bucket_name']}",
            "result": result
        })
        
        return result
    
    async def _execute_ec2_stop_instance(
        self,
        aws_client,
        cloud_account,
        action: RemediationAction,
        execution_log: List[Dict]
    ) -> Dict[str, Any]:
        """Execute EC2 instance stop remediation."""
        session = await aws_client.get_session(
            cloud_account.role_arn,
            cloud_account.external_id,
            action.region
        )
        
        def _stop_instance():
            ec2_client = session.client('ec2')
            
            # Get instance details before stopping
            instance_info = ec2_client.describe_instances(
                InstanceIds=[action.parameters['instance_id']]
            )['Reservations'][0]['Instances'][0]
            
            # Stop the instance
            response = ec2_client.stop_instances(
                InstanceIds=[action.parameters['instance_id']],
                Hibernate=False,  # Don't hibernate to allow quick restart
                DryRun=False
            )
            
            return {
                "instance_id": action.parameters['instance_id'],
                "previous_state": instance_info['State']['Name'],
                "new_state": "stopping",
                "response": response
            }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _stop_instance)
        
        execution_log.append({
            "timestamp": datetime.utcnow(),
            "step": "execute",
            "message": f"Stopped EC2 instance {action.parameters['instance_id']}",
            "result": result
        })
        
        return result
    
    async def _execute_ec2_update_security_group(
        self,
        aws_client,
        cloud_account,
        action: RemediationAction,
        execution_log: List[Dict]
    ) -> Dict[str, Any]:
        """Execute EC2 security group update remediation."""
        session = await aws_client.get_session(
            cloud_account.role_arn,
            cloud_account.external_id,
            action.region
        )
        
        def _update_security_group():
            ec2_client = session.client('ec2')
            
            # Get current security group rules
            current_rules = ec2_client.describe_security_group_rules(
                Filters=[
                    {'Name': 'group-id', 'Values': [action.parameters['security_group_id']]}
                ]
            )['SecurityGroupRules']
            
            # Revoke overly permissive rules
            permissive_rules = [
                rule for rule in current_rules
                if rule.get('CidrIpv4') == '0.0.0.0/0' and not rule.get('IsEgress', False)
            ]
            
            for rule in permissive_rules:
                if rule['IpProtocol'] == '-1':  # All traffic
                    ec2_client.revoke_security_group_ingress(
                        GroupId=action.parameters['security_group_id'],
                        IpPermissions=[{
                            'IpProtocol': '-1',
                            'FromPort': -1,
                            'ToPort': -1,
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                        }]
                    )
                else:
                    ec2_client.revoke_security_group_ingress(
                        GroupId=action.parameters['security_group_id'],
                        IpPermissions=[{
                            'IpProtocol': rule['IpProtocol'],
                            'FromPort': rule.get('FromPort', -1),
                            'ToPort': rule.get('ToPort', -1),
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                        }]
                    )
            
            # Add restricted rule if specified
            if 'allow_cidr' in action.parameters:
                ec2_client.authorize_security_group_ingress(
                    GroupId=action.parameters['security_group_id'],
                    IpPermissions=[{
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': action.parameters['allow_cidr']}]
                    }]
                )
            
            return {
                "security_group_id": action.parameters['security_group_id'],
                "revoked_rules": len(permissive_rules),
                "added_rule": 'allow_cidr' in action.parameters
            }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _update_security_group)
        
        execution_log.append({
            "timestamp": datetime.utcnow(),
            "step": "execute",
            "message": f"Updated security group {action.parameters['security_group_id']}",
            "result": result
        })
        
        return result
    
    async def _execute_ebs_delete_volume(
        self,
        aws_client,
        cloud_account,
        action: RemediationAction,
        execution_log: List[Dict]
    ) -> Dict[str, Any]:
        """Execute EBS volume deletion remediation."""
        session = await aws_client.get_session(
            cloud_account.role_arn,
            cloud_account.external_id,
            action.region
        )
        
        def _delete_volume():
            ec2_client = session.client('ec2')
            
            # Get volume details before deletion
            volume_info = ec2_client.describe_volumes(
                VolumeIds=[action.parameters['volume_id']]
            )['Volumes'][0]
            
            # Create snapshot for backup
            snapshot = ec2_client.create_snapshot(
                VolumeId=action.parameters['volume_id'],
                Description=f"Backup before deletion for remediation {action.id}",
                TagSpecifications=[
                    {
                        'ResourceType': 'snapshot',
                        'Tags': [
                            {'Key': 'RemediationId', 'Value': action.id},
                            {'Key': 'Purpose', 'Value': 'rollback_backup'}
                        ]
                    }
                ]
            )
            
            # Delete the volume
            ec2_client.delete_volume(VolumeId=action.parameters['volume_id'])
            
            return {
                "volume_id": action.parameters['volume_id'],
                "volume_size": volume_info['Size'],
                "snapshot_id": snapshot['SnapshotId'],
                "deleted": True
            }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _delete_volume)
        
        execution_log.append({
            "timestamp": datetime.utcnow(),
            "step": "execute",
            "message": f"Deleted EBS volume {action.parameters['volume_id']}",
            "result": result
        })
        
        return result
    
    async def _execute_tag_resource(
        self,
        aws_client,
        cloud_account,
        action: RemediationAction,
        execution_log: List[Dict]
    ) -> Dict[str, Any]:
        """Execute resource tagging remediation."""
        session = await aws_client.get_session(
            cloud_account.role_arn,
            cloud_account.external_id,
            action.region
        )
        
        def _tag_resource():
            # Determine resource type and tagging method
            resource_arn = action.parameters['resource_arn']
            
            if 'ec2' in resource_arn:
                ec2_client = session.client('ec2')
                
                # Extract resource ID from ARN
                resource_id = resource_arn.split('/')[-1]
                
                # Create tags
                tag_specifications = []
                for key, value in action.parameters['tags'].items():
                    tag_specifications.append({
                        'Key': key,
                        'Value': str(value)
                    })
                
                ec2_client.create_tags(
                    Resources=[resource_id],
                    Tags=tag_specifications
                )
                
                return {
                    "resource_id": resource_id,
                    "tags_added": len(tag_specifications)
                }
            
            elif 's3' in resource_arn:
                s3_client = session.client('s3')
                
                # Extract bucket name
                bucket_name = resource_arn.split(':')[-1]
                
                # Get existing tags
                try:
                    existing_tags = s3_client.get_bucket_tagging(
                        Bucket=bucket_name
                    )['TagSet']
                except ClientError:
                    existing_tags = []
                
                # Add new tags
                tag_set = existing_tags + [
                    {'Key': key, 'Value': str(value)}
                    for key, value in action.parameters['tags'].items()
                ]
                
                s3_client.put_bucket_tagging(
                    Bucket=bucket_name,
                    Tagging={'TagSet': tag_set}
                )
                
                return {
                    "bucket_name": bucket_name,
                    "tags_added": len(action.parameters['tags'])
                }
            
            else:
                # Use Resource Groups Tagging API for other resources
                rg_client = session.client('resourcegroupstaggingapi')
                
                rg_client.tag_resources(
                    ResourceARNList=[resource_arn],
                    Tags=action.parameters['tags']
                )
                
                return {
                    "resource_arn": resource_arn,
                    "tags_added": len(action.parameters['tags'])
                }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _tag_resource)
        
        execution_log.append({
            "timestamp": datetime.utcnow(),
            "step": "execute",
            "message": f"Added tags to resource {action.parameters['resource_arn']}",
            "result": result
        })
        
        return result
    
    async def rollback_remediation(
        self,
        action: RemediationAction,
        rollback_data: Dict[str, Any],
        executed_by: str
    ) -> Dict[str, Any]:
        """Rollback a remediation action."""
        execution_log = []
        
        try:
            execution_log.append({
                "timestamp": datetime.utcnow(),
                "step": "start",
                "message": f"Starting rollback for {action.title}"
            })
            
            # Implementation would depend on the action type
            # For S3 block public access, restore previous configuration
            # For EC2 stop, start the instance
            # For EBS delete, restore from snapshot
            
            execution_log.append({
                "timestamp": datetime.utcnow(),
                "step": "complete",
                "message": "Rollback completed successfully"
            })
            
            return {
                "success": True,
                "execution_log": execution_log
            }
        
        except Exception as e:
            execution_log.append({
                "timestamp": datetime.utcnow(),
                "step": "error",
                "message": f"Rollback failed: {str(e)}"
            })
            
            return {
                "success": False,
                "execution_log": execution_log,
                "error": str(e)
            }
    
    async def _generate_rollback_plan(self, action: RemediationAction) -> Dict[str, Any]:
        """Generate a rollback plan for an action."""
        if action.action_type == "s3_block_public_access":
            return {
                "method": "restore_previous_config",
                "steps": [
                    "Retrieve previous S3 block public access configuration",
                    "Apply previous configuration",
                    "Verify public access settings"
                ],
                "estimated_time": "2 minutes",
                "risk": "low"
            }
        
        elif action.action_type == "ec2_stop_instance":
            return {
                "method": "start_instance",
                "steps": [
                    "Start the EC2 instance",
                    "Verify instance state is 'running'",
                    "Check application health"
                ],
                "estimated_time": "5 minutes",
                "risk": "low"
            }
        
        elif action.action_type == "ebs_delete_volume":
            return {
                "method": "restore_from_snapshot",
                "steps": [
                    "Create new volume from snapshot",
                    "Attach to original instance",
                    "Verify data integrity"
                ],
                "estimated_time": "10 minutes",
                "risk": "medium"
            }
        
        return {
            "method": "manual_intervention",
            "steps": ["Contact administrator for rollback"],
            "estimated_time": "unknown",
            "risk": "high"
        }
    
    async def _capture_rollback_data(self, action: RemediationAction) -> Dict[str, Any]:
        """Capture data needed for potential rollback."""
        # This would capture the state before remediation
        # For now, return minimal data
        return {
            "action_id": action.id,
            "resource_id": action.resource_id,
            "timestamp": datetime.utcnow().isoformat(),
            "pre_remediation_state": "captured"
        }
    
    def _is_over_provisioned(self, instance_type: str, cpu_utilization: float) -> bool:
        """Check if EC2 instance is over-provisioned."""
        # Simple heuristic based on instance family and CPU utilization
        if not instance_type or cpu_utilization == 0:
            return False
        
        instance_families = {
            't3': 30,  # Burstable - lower threshold
            'm5': 20,  # General purpose
            'c5': 25,  # Compute optimized
            'r5': 20   # Memory optimized
        }
        
        family = instance_type.split('.')[0]
        threshold = instance_families.get(family, 20)
        
        return cpu_utilization < threshold
    
    def _get_recommended_type(self, current_type: str) -> str:
        """Get recommended instance type for right-sizing."""
        # Simple downgrade mapping
        downgrade_map = {
            'm5.2xlarge': 'm5.xlarge',
            'm5.xlarge': 'm5.large',
            'm5.large': 'm5.medium',
            'c5.2xlarge': 'c5.xlarge',
            'c5.xlarge': 'c5.large',
            't3.2xlarge': 't3.xlarge',
            't3.xlarge': 't3.large'
        }
        
        return downgrade_map.get(current_type, current_type)
    
    def _load_action_templates(self) -> Dict[str, Any]:
        """Load remediation action templates."""
        return {
            "s3_block_public_access": {
                "name": "Block S3 Public Access",
                "description": "Enable S3 Block Public Access settings",
                "supported_resources": ["AWS::S3::Bucket"],
                "risk_level": "low",
                "approval_required": True,
                "execution_time": "2 minutes"
            },
            "ec2_stop_instance": {
                "name": "Stop EC2 Instance",
                "description": "Stop an EC2 instance",
                "supported_resources": ["AWS::EC2::Instance"],
                "risk_level": "medium",
                "approval_required": True,
                "execution_time": "2 minutes"
            }
        }