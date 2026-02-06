import boto3
from botocore.config import Config
from typing import Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.config import settings

class AWSClient:
    """Async AWS client wrapper."""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.config = Config(
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            },
            connect_timeout=10,
            read_timeout=30
        )
    
    async def assume_role(
        self,
        role_arn: str,
        external_id: str,
        session_name: str = "CloudIntelligenceSession"
    ) -> Dict[str, Any]:
        """Assume IAM role for cross-account access."""
        loop = asyncio.get_event_loop()
        
        def _assume_role():
            sts_client = boto3.client('sts', config=self.config)
            response = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=session_name,
                ExternalId=external_id,
                DurationSeconds=3600
            )
            return response['Credentials']
        
        credentials = await loop.run_in_executor(self.executor, _assume_role)
        return credentials
    
    async def get_session(
        self,
        role_arn: str,
        external_id: str,
        region: str = settings.AWS_DEFAULT_REGION
    ):
        """Get boto3 session with assumed role credentials."""
        credentials = await self.assume_role(role_arn, external_id)
        
        def _create_session():
            return boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=region
            )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _create_session)
    
    async def list_resources(
        self,
        role_arn: str,
        external_id: str,
        region: str,
        resource_types: Optional[list] = None
    ) -> Dict[str, Any]:
        """List AWS resources using Resource Explorer."""
        session = await self.get_session(role_arn, external_id, region)
        
        def _list_resources():
            resource_client = session.client('resource-explorer-2')
            ec2_client = session.client('ec2')
            
            # First, get view ARN
            views = resource_client.list_views()
            if not views['Views']:
                return {"resources": [], "error": "No Resource Explorer views found"}
            
            view_arn = views['Views'][0]
            
            # Search for resources
            search_filters = []
            if resource_types:
                search_filters.append({
                    "FilterString": f"resourceType:{' OR '.join(resource_types)}"
                })
            
            response = resource_client.search(
                ViewArn=view_arn,
                MaxResults=1000,
                QueryString="*"  # Match all resources
            )
            
            resources = []
            for resource in response.get('Resources', []):
                resources.append({
                    "arn": resource['Arn'],
                    "resource_type": resource['ResourceType'],
                    "region": resource.get('Region', region),
                    "last_reported_at": resource.get('LastReportedAt'),
                    "properties": resource.get('Properties', {})
                })
            
            # Also get EC2 instances directly (as backup)
            ec2_response = ec2_client.describe_instances()
            for reservation in ec2_response['Reservations']:
                for instance in reservation['Instances']:
                    resources.append({
                        "arn": f"arn:aws:ec2:{region}:{instance.get('OwnerId')}:instance/{instance['InstanceId']}",
                        "resource_type": "AWS::EC2::Instance",
                        "region": region,
                        "last_reported_at": instance.get('LaunchTime').isoformat(),
                        "properties": {
                            "instance_type": instance.get('InstanceType'),
                            "state": instance.get('State', {}).get('Name'),
                            "tags": instance.get('Tags', [])
                        }
                    })
            
            return {"resources": resources, "count": len(resources)}
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _list_resources)
    
    async def get_cost_data(
        self,
        role_arn: str,
        external_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Get cost data from AWS Cost Explorer."""
        session = await self.get_session(role_arn, external_id)
        
        def _get_cost_data():
            ce_client = session.client('ce')
            
            response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'REGION'}
                ]
            )
            
            results = []
            for result in response['ResultsByTime']:
                for group in result.get('Groups', []):
                    results.append({
                        "period": result['TimePeriod'],
                        "service": group['Keys'][0],
                        "region": group['Keys'][1],
                        "cost": group['Metrics']['BlendedCost']['Amount'],
                        "unit": group['Metrics']['BlendedCost']['Unit'],
                        "usage": group['Metrics']['UsageQuantity']['Amount']
                    })
            
            return {
                "cost_data": results,
                "total_cost": sum(float(r['cost']) for r in results)
            }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _get_cost_data)