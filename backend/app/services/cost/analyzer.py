from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

class CostGranularity(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class CostCategory(Enum):
    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"
    NETWORK = "network"
    OTHER = "other"

@dataclass
class CostAnalysis:
    total_cost: float
    period_start: datetime
    period_end: datetime
    by_service: Dict[str, float]
    by_region: Dict[str, float]
    by_account: Dict[str, float]
    trend_percentage: float
    forecast_30d: float
    anomalies: List[Dict[str, Any]]

@dataclass
class CostRecommendation:
    id: str
    title: str
    description: str
    resource_type: str
    resource_id: str
    estimated_savings: float
    implementation_effort: str  # low, medium, high
    risk: str  # low, medium, high
    action_type: str  # resize, shutdown, delete, purchase_reserved

class CostAnalyzer:
    """AI-powered cost analysis and optimization engine."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cost_thresholds = {
            'high_cost_instance': 1000,  # Monthly cost per instance
            'idle_instance_cpu': 10,  # CPU utilization percentage
            'unused_storage_gb': 100,  # Unused storage in GB
            'reserved_instance_savings': 0.4,  # 40% savings
        }
    
    async def analyze_cost(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        granularity: CostGranularity = CostGranularity.DAILY
    ) -> CostAnalysis:
        """Analyze cost data for the given period."""
        
        # Get all cloud accounts for the organization
        from app.models.cloud_account import CloudAccount
        result = await self.db.execute(
            select(CloudAccount).where(
                CloudAccount.organization_id == organization_id,
                CloudAccount.is_active == True
            )
        )
        accounts = result.scalars().all()
        
        # Collect cost data from all accounts
        all_cost_data = []
        for account in accounts:
            if account.provider == "aws":
                cost_data = await self._get_aws_cost_data(account, start_date, end_date)
                all_cost_data.extend(cost_data)
        
        # Calculate totals and breakdowns
        total_cost = sum(item['cost'] for item in all_cost_data)
        
        by_service = self._group_by(all_cost_data, 'service')
        by_region = self._group_by(all_cost_data, 'region')
        by_account = self._group_by(all_cost_data, 'account_id')
        
        # Calculate trend
        previous_period_start = start_date - (end_date - start_date)
        previous_period_end = start_date
        previous_cost = await self._get_previous_period_cost(
            organization_id, previous_period_start, previous_period_end
        )
        
        trend_percentage = 0
        if previous_cost > 0:
            trend_percentage = ((total_cost - previous_cost) / previous_cost) * 100
        
        # Generate forecast
        forecast_30d = await self._forecast_cost(organization_id, total_cost, 30)
        
        # Detect anomalies
        anomalies = await self._detect_cost_anomalies(all_cost_data)
        
        return CostAnalysis(
            total_cost=total_cost,
            period_start=start_date,
            period_end=end_date,
            by_service=by_service,
            by_region=by_region,
            by_account=by_account,
            trend_percentage=trend_percentage,
            forecast_30d=forecast_30d,
            anomalies=anomalies
        )
    
    async def _get_aws_cost_data(
        self,
        account,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get cost data from AWS Cost Explorer."""
        # This would make actual AWS API calls
        # For now, return mock data
        
        mock_services = [
            "Amazon EC2", "Amazon S3", "Amazon RDS", "Amazon CloudFront",
            "AWS Lambda", "Amazon DynamoDB", "Amazon EKS", "AWS Data Transfer"
        ]
        
        mock_regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        
        cost_data = []
        current_date = start_date
        
        while current_date < end_date:
            for service in mock_services:
                for region in mock_regions:
                    cost = Decimal(str(100 + (hash(service + region + current_date.isoformat()) % 900)))
                    cost_data.append({
                        'date': current_date,
                        'service': service,
                        'region': region,
                        'account_id': account.account_id,
                        'cost': float(cost),
                        'usage_type': 'OnDemand',
                        'unit': 'USD'
                    })
            current_date += timedelta(days=1)
        
        return cost_data
    
    def _group_by(self, data: List[Dict], key: str) -> Dict[str, float]:
        """Group cost data by key."""
        grouped = {}
        for item in data:
            group_key = item.get(key, 'Unknown')
            grouped[group_key] = grouped.get(group_key, 0) + item['cost']
        return grouped
    
    async def _get_previous_period_cost(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Get cost for previous period from database."""
        # In production, this would query the time-series database
        # For now, return mock data
        return 15000.0
    
    async def _forecast_cost(
        self,
        organization_id: str,
        current_cost: float,
        days: int = 30
    ) -> float:
        """Forecast future costs using time-series analysis."""
        # Simple forecasting model (would be replaced with Prophet/LSTM)
        from app.models.resource import Resource
        from app.models.cloud_account import CloudAccount
        
        # Get resource growth trend
        result = await self.db.execute(
            select(func.count(Resource.id)).join(
                CloudAccount, Resource.cloud_account_id == CloudAccount.id
            ).where(
                CloudAccount.organization_id == organization_id
            )
        )
        resource_count = result.scalar()
        
        # Simple linear forecast based on resource growth
        growth_rate = 0.1  # 10% monthly growth
        forecast = current_cost * (1 + growth_rate)
        
        return forecast
    
    async def _detect_cost_anomalies(self, cost_data: List[Dict]) -> List[Dict[str, Any]]:
        """Detect cost anomalies using statistical methods."""
        anomalies = []
        
        # Group by service and date
        service_daily = {}
        for item in cost_data:
            key = f"{item['service']}_{item['date'].strftime('%Y-%m-%d')}"
            if key not in service_daily:
                service_daily[key] = 0
            service_daily[key] += item['cost']
        
        # Calculate moving averages and detect spikes
        service_groups = {}
        for key, cost in service_daily.items():
            service, date_str = key.split('_')
            if service not in service_groups:
                service_groups[service] = []
            service_groups[service].append((date_str, cost))
        
        for service, data in service_groups.items():
            if len(data) < 7:
                continue
                
            # Get last 7 days
            recent_data = sorted(data, key=lambda x: x[0])[-7:]
            costs = [cost for _, cost in recent_data]
            
            # Calculate mean and standard deviation
            mean = sum(costs) / len(costs)
            variance = sum((x - mean) ** 2 for x in costs) / len(costs)
            std_dev = variance ** 0.5
            
            # Check last day for anomaly
            last_cost = costs[-1]
            if std_dev > 0 and abs(last_cost - mean) > 2 * std_dev:
                anomalies.append({
                    'service': service,
                    'date': recent_data[-1][0],
                    'cost': last_cost,
                    'expected': mean,
                    'deviation': (last_cost - mean) / mean * 100,
                    'severity': 'high' if (last_cost - mean) > 3 * std_dev else 'medium'
                })
        
        return anomalies
    
    async def generate_recommendations(
        self,
        organization_id: str,
        limit: int = 10
    ) -> List[CostRecommendation]:
        """Generate cost optimization recommendations."""
        from app.models.resource import Resource
        from app.models.cloud_account import CloudAccount
        
        recommendations = []
        
        # Get EC2 instances for analysis
        result = await self.db.execute(
            select(Resource).join(
                CloudAccount, Resource.cloud_account_id == CloudAccount.id
            ).where(
                and_(
                    CloudAccount.organization_id == organization_id,
                    Resource.resource_type == 'AWS::EC2::Instance',
                    Resource.status == 'running'
                )
            )
        )
        instances = result.scalars().all()
        
        for instance in instances:
            # Check for idle instances
            if instance.metadata.get('avg_cpu_utilization', 0) < self.cost_thresholds['idle_instance_cpu']:
                recommendations.append(CostRecommendation(
                    id=f"idle_instance_{instance.id}",
                    title="Idle EC2 Instance",
                    description=f"Instance {instance.name or instance.resource_id} has low CPU utilization ({instance.metadata.get('avg_cpu_utilization', 0)}%)",
                    resource_type="AWS::EC2::Instance",
                    resource_id=instance.resource_id,
                    estimated_savings=instance.cost_estimate * 0.8,  # 80% savings if stopped
                    implementation_effort="low",
                    risk="low",
                    action_type="shutdown"
                ))
            
            # Check for over-provisioned instances
            instance_type = instance.metadata.get('instance_type', '')
            if instance_type and self._is_over_provisioned(instance):
                recommendations.append(CostRecommendation(
                    id=f"oversized_{instance.id}",
                    title="Over-provisioned EC2 Instance",
                    description=f"Instance {instance.name or instance.resource_id} ({instance_type}) is over-provisioned for its workload",
                    resource_type="AWS::EC2::Instance",
                    resource_id=instance.resource_id,
                    estimated_savings=instance.cost_estimate * 0.3,  # 30% savings if downsized
                    implementation_effort="medium",
                    risk="low",
                    action_type="resize"
                ))
            
            # Check for reserved instance opportunities
            if instance.cost_estimate > self.cost_thresholds['high_cost_instance']:
                if not instance.metadata.get('is_reserved', False):
                    recommendations.append(CostRecommendation(
                        id=f"ri_opportunity_{instance.id}",
                        title="Reserved Instance Opportunity",
                        description=f"High-cost instance {instance.name or instance.resource_id} could benefit from Reserved Instance pricing",
                        resource_type="AWS::EC2::Instance",
                        resource_id=instance.resource_id,
                        estimated_savings=instance.cost_estimate * self.cost_thresholds['reserved_instance_savings'],
                        implementation_effort="medium",
                        risk="low",
                        action_type="purchase_reserved"
                    ))
        
        # Get storage resources
        result = await self.db.execute(
            select(Resource).join(
                CloudAccount, Resource.cloud_account_id == CloudAccount.id
            ).where(
                and_(
                    CloudAccount.organization_id == organization_id,
                    Resource.resource_type.in_(['AWS::S3::Bucket', 'AWS::EBS::Volume'])
                )
            )
        )
        storage_resources = result.scalars().all()
        
        for resource in storage_resources:
            if resource.resource_type == 'AWS::S3::Bucket':
                size_gb = resource.metadata.get('size_gb', 0)
                access_count = resource.metadata.get('access_count_30d', 0)
                
                if size_gb > self.cost_thresholds['unused_storage_gb'] and access_count < 10:
                    recommendations.append(CostRecommendation(
                        id=f"unused_storage_{resource.id}",
                        title="Unused S3 Storage",
                        description=f"S3 bucket {resource.name or resource.resource_id} has {size_gb}GB of infrequently accessed data",
                        resource_type="AWS::S3::Bucket",
                        resource_id=resource.resource_id,
                        estimated_savings=size_gb * 0.02 * 12,  # $0.02/GB/month annualized
                        implementation_effort="low",
                        risk="low",
                        action_type="lifecycle_policy"
                    ))
            
            elif resource.resource_type == 'AWS::EBS::Volume':
                if not resource.metadata.get('is_attached', False):
                    recommendations.append(CostRecommendation(
                        id=f"unattached_volume_{resource.id}",
                        title="Unattached EBS Volume",
                        description=f"EBS volume {resource.name or resource.resource_id} is not attached to any instance",
                        resource_type="AWS::EBS::Volume",
                        resource_id=resource.resource_id,
                        estimated_savings=resource.cost_estimate,
                        implementation_effort="low",
                        risk="low",
                        action_type="delete"
                    ))
        
        return recommendations[:limit]
    
    def _is_over_provisioned(self, instance) -> bool:
        """Check if an EC2 instance is over-provisioned."""
        cpu_util = instance.metadata.get('avg_cpu_utilization', 0)
        mem_util = instance.metadata.get('avg_memory_utilization', 0)
        
        # If both CPU and memory utilization are below 30%, likely over-provisioned
        return cpu_util < 30 and mem_util < 30
    
    async def calculate_savings_opportunity(self, organization_id: str) -> Dict[str, Any]:
        """Calculate total savings opportunity across all recommendations."""
        recommendations = await self.generate_recommendations(organization_id)
        
        total_savings = sum(r.estimated_savings for r in recommendations)
        
        # Categorize by resource type
        by_type = {}
        by_effort = {'low': 0, 'medium': 0, 'high': 0}
        by_risk = {'low': 0, 'medium': 0, 'high': 0}
        
        for rec in recommendations:
            by_type[rec.resource_type] = by_type.get(rec.resource_type, 0) + rec.estimated_savings
            by_effort[rec.implementation_effort] += rec.estimated_savings
            by_risk[rec.risk] += rec.estimated_savings
        
        return {
            'total_opportunity': total_savings,
            'recommendation_count': len(recommendations),
            'by_resource_type': by_type,
            'by_implementation_effort': by_effort,
            'by_risk': by_risk,
            'recommendations': [
                {
                    'id': r.id,
                    'title': r.title,
                    'description': r.description,
                    'estimated_savings': r.estimated_savings,
                    'implementation_effort': r.implementation_effort,
                    'risk': r.risk,
                    'action_type': r.action_type
                }
                for r in recommendations
            ]
        }