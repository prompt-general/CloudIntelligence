from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ResourceScore:
    cost_score: float  # 0-100
    security_score: float  # 0-100
    optimization_score: float  # 0-100
    compliance_score: float  # 0-100
    overall_score: float  # 0-100
    risk_level: RiskLevel
    recommendations: List[str]
    last_calculated: datetime

class ScoringEngine:
    """AI-powered resource scoring engine."""
    
    def __init__(self):
        self.cost_rules = self._load_cost_rules()
        self.security_rules = self._load_security_rules()
        self.optimization_rules = self._load_optimization_rules()
    
    async def score_resource(self, resource: Dict[str, Any]) -> ResourceScore:
        """Calculate scores for a single resource."""
        tasks = [
            self._calculate_cost_score(resource),
            self._calculate_security_score(resource),
            self._calculate_optimization_score(resource),
            self._calculate_compliance_score(resource)
        ]
        
        scores = await asyncio.gather(*tasks)
        
        # Calculate overall score (weighted average)
        weights = {
            'cost': 0.3,
            'security': 0.4,
            'optimization': 0.2,
            'compliance': 0.1
        }
        
        overall_score = (
            scores[0] * weights['cost'] +
            scores[1] * weights['security'] +
            scores[2] * weights['optimization'] +
            scores[3] * weights['compliance']
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_score, scores[1])
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(resource, scores)
        
        return ResourceScore(
            cost_score=scores[0],
            security_score=scores[1],
            optimization_score=scores[2],
            compliance_score=scores[3],
            overall_score=overall_score,
            risk_level=risk_level,
            recommendations=recommendations,
            last_calculated=datetime.utcnow()
        )
    
    async def _calculate_cost_score(self, resource: Dict[str, Any]) -> float:
        """Calculate cost efficiency score."""
        base_score = 100.0
        
        # Apply cost rules
        resource_type = resource.get('resource_type', '')
        cost = float(resource.get('cost_estimate', 0))
        
        if resource_type == 'AWS::EC2::Instance':
            # Check if instance is idle (low CPU utilization)
            if resource.get('avg_cpu_utilization', 0) < 10:
                base_score -= 30
            
            # Check if instance type is appropriate
            instance_type = resource.get('instance_type', '')
            if instance_type.startswith('t3') and resource.get('cpu_credits', 0) < 0:
                base_score -= 20
        
        elif resource_type == 'AWS::S3::Bucket':
            # Check for unused storage
            if resource.get('size_gb', 0) > 100 and resource.get('access_count_30d', 0) < 10:
                base_score -= 40
        
        elif resource_type == 'AWS::RDS::DBInstance':
            # Check for idle database
            if resource.get('connections_avg', 0) < 5:
                base_score -= 25
        
        elif resource_type == 'gcp:compute:instance':
            # Check for GCP idle instances
            if resource.get('avg_cpu_utilization', 0) < 5:
                base_score -= 30
        
        elif resource_type == 'gcp:storage:bucket':
            if resource.get('access_count_30d', 0) == 0:
                base_score -= 40
        
        # Normalize score
        return max(0.0, min(100.0, base_score))
    
    async def _calculate_security_score(self, resource: Dict[str, Any]) -> float:
        """Calculate security score."""
        base_score = 100.0
        resource_type = resource.get('resource_type', '')
        
        # Public exposure checks
        if resource.get('is_public', False):
            base_score -= 40
        
        # Encryption checks
        if not resource.get('encrypted', True):
            base_score -= 30
        
        # IAM and access control checks
        if resource_type == 'AWS::IAM::Role':
            if resource.get('has_admin_policy', False):
                base_score -= 50
            if not resource.get('requires_mfa', False):
                base_score -= 20
        
        elif resource_type == 'AWS::EC2::SecurityGroup':
            # Check for overly permissive rules
            permissive_rules = resource.get('permissive_rules', [])
            base_score -= len(permissive_rules) * 15
        
        elif resource_type == 'AWS::S3::Bucket':
            # Check for public access
            if resource.get('public_access', False):
                base_score -= 60
            # Check for versioning
            if not resource.get('versioning_enabled', False):
                base_score -= 10
        
        elif resource_type == 'gcp:compute:instance':
            if resource.get('is_public', False):
                base_score -= 50
        
        elif resource_type == 'gcp:storage:bucket':
            if not resource.get('public_access_prevention', False):
                base_score -= 40
        
        # Normalize score
        return max(0.0, min(100.0, base_score))
    
    async def _calculate_optimization_score(self, resource: Dict[str, Any]) -> float:
        """Calculate optimization score."""
        base_score = 100.0
        resource_type = resource.get('resource_type', '')
        
        # Resource utilization checks
        if resource_type == 'AWS::EC2::Instance':
            cpu_util = resource.get('avg_cpu_utilization', 0)
            mem_util = resource.get('avg_memory_utilization', 0)
            
            # Underutilized
            if cpu_util < 20 and mem_util < 20:
                base_score -= 40
            # Overutilized
            elif cpu_util > 80 or mem_util > 80:
                base_score -= 30
            
            # Check for reserved instance savings
            if not resource.get('is_reserved', False):
                base_score -= 15
        
        elif resource_type == 'AWS::RDS::DBInstance':
            # Check for idle connections
            connections = resource.get('connections_avg', 0)
            if connections < 2:
                base_score -= 35
        
        # Check for age (long-running resources might need updates)
        age_days = resource.get('age_days', 0)
        if age_days > 365:  # Older than 1 year
            base_score -= 20
        
        return max(0.0, min(100.0, base_score))
    
    async def _calculate_compliance_score(self, resource: Dict[str, Any]) -> float:
        """Calculate compliance score based on common frameworks."""
        base_score = 100.0
        compliance_violations = resource.get('compliance_violations', [])
        
        # Deduct points for each violation
        violation_weights = {
            'pci_dss': 25,
            'hipaa': 30,
            'soc2': 20,
            'iso27001': 20,
            'gdpr': 35
        }
        
        for violation in compliance_violations:
            weight = violation_weights.get(violation.get('framework', ''), 20)
            base_score -= weight
        
        return max(0.0, min(100.0, base_score))
    
    def _determine_risk_level(self, overall_score: float, security_score: float) -> RiskLevel:
        """Determine overall risk level."""
        if security_score < 40 or overall_score < 30:
            return RiskLevel.CRITICAL
        elif security_score < 60 or overall_score < 50:
            return RiskLevel.HIGH
        elif security_score < 75 or overall_score < 70:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def _generate_recommendations(self, resource: Dict[str, Any], scores: List[float]) -> List[str]:
        """Generate AI-powered recommendations."""
        recommendations = []
        resource_type = resource.get('resource_type', '')
        
        # Cost recommendations
        if scores[0] < 70:  # Poor cost score
            if resource_type == 'AWS::EC2::Instance':
                if resource.get('avg_cpu_utilization', 0) < 20:
                    recommendations.append("Consider downsizing instance type or using smaller instance")
                if not resource.get('is_reserved', False):
                    recommendations.append("Purchase Reserved Instance for cost savings")
            
            elif resource_type == 'AWS::S3::Bucket':
                if resource.get('size_gb', 0) > 100 and resource.get('access_count_30d', 0) < 10:
                    recommendations.append("Consider moving infrequently accessed data to S3 Glacier")
        
        # Security recommendations
        if scores[1] < 70:  # Poor security score
            if resource.get('is_public', False):
                recommendations.append("Remove public access and implement proper IAM controls")
            
            if not resource.get('encrypted', True):
                recommendations.append("Enable encryption at rest")
            
            if resource_type == 'AWS::IAM::Role' and resource.get('has_admin_policy', False):
                recommendations.append("Apply principle of least privilege - remove admin policies")
        
        # Optimization recommendations
        if scores[2] < 70:  # Poor optimization score
            if resource_type == 'AWS::EC2::Instance':
                if resource.get('age_days', 0) > 365:
                    recommendations.append("Consider upgrading to newer generation instance types")
            
            if resource.get('has_unused_volumes', False):
                recommendations.append("Delete unattached EBS volumes to reduce costs")
        
        # Add general recommendations if none specific
        if not recommendations:
            if overall_score < 80:
                recommendations.append("Review resource configuration for potential improvements")
        
        return recommendations
    
    def _load_cost_rules(self) -> List[Dict]:
        """Load cost optimization rules."""
        return [
            {
                "rule_id": "cost_ec2_idle",
                "resource_type": "AWS::EC2::Instance",
                "condition": "avg_cpu_utilization < 10",
                "penalty": 30,
                "recommendation": "Instance appears idle - consider stopping or terminating"
            },
            {
                "rule_id": "cost_s3_unused",
                "resource_type": "AWS::S3::Bucket",
                "condition": "size_gb > 100 AND access_count_30d < 10",
                "penalty": 40,
                "recommendation": "Large bucket with low access - consider lifecycle policies"
            }
        ]
    
    def _load_security_rules(self) -> List[Dict]:
        """Load security rules."""
        return [
            {
                "rule_id": "sec_public_resource",
                "resource_type": "*",
                "condition": "is_public == true",
                "penalty": 40,
                "recommendation": "Resource is publicly accessible"
            },
            {
                "rule_id": "sec_unencrypted",
                "resource_type": "*",
                "condition": "encrypted == false",
                "penalty": 30,
                "recommendation": "Enable encryption at rest"
            }
        ]
    
    def _load_optimization_rules(self) -> List[Dict]:
        """Load optimization rules."""
        return [
            {
                "rule_id": "opt_underutilized_ec2",
                "resource_type": "AWS::EC2::Instance",
                "condition": "avg_cpu_utilization < 20 AND avg_memory_utilization < 20",
                "penalty": 40,
                "recommendation": "Instance is underutilized - consider downsizing"
            }
        ]