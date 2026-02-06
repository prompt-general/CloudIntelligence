from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization, CloudAccount, Resource
from app.services.aws.client import AWSClient

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard overview data."""
    
    # Get cloud accounts
    accounts_result = await db.execute(
        select(CloudAccount)
        .where(CloudAccount.organization_id == organization.id)
        .order_by(CloudAccount.created_at.desc())
    )
    cloud_accounts = accounts_result.scalars().all()
    
    # Get resources
    resources_result = await db.execute(
        select(Resource)
        .join(CloudAccount, Resource.cloud_account_id == CloudAccount.id)
        .where(CloudAccount.organization_id == organization.id)
        .order_by(Resource.created_at.desc())
        .limit(50)
    )
    resources = resources_result.scalars().all()
    
    # Calculate metrics
    total_resources = len(resources)
    
    # Calculate total cost (mock for now)
    total_cost = sum(
        float(resource.cost_estimate or 0) 
        for resource in resources
    )
    
    # Calculate average security score
    security_scores = [
        resource.security_score or 0 
        for resource in resources 
        if resource.security_score is not None
    ]
    avg_security_score = sum(security_scores) / len(security_scores) if security_scores else 0
    
    # Calculate average optimization score
    optimization_scores = [
        resource.optimization_score or 0 
        for resource in resources 
        if resource.optimization_score is not None
    ]
    avg_optimization_score = sum(optimization_scores) / len(optimization_scores) if optimization_scores else 0
    
    # Get recent activities (mock for now)
    recent_activities = [
        {
            "id": "1",
            "action": "resource_created",
            "resource_type": "ec2",
            "resource_name": "web-server-1",
            "actor": "system",
            "timestamp": datetime.utcnow().isoformat(),
            "details": "EC2 instance created"
        },
        {
            "id": "2",
            "action": "security_alert",
            "resource_type": "s3",
            "resource_name": "logs-bucket",
            "actor": "security_scanner",
            "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "details": "Public bucket detected"
        },
        {
            "id": "3",
            "action": "cost_alert",
            "resource_type": "rds",
            "resource_name": "prod-database",
            "actor": "cost_analyzer",
            "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "details": "High monthly cost detected"
        }
    ]
    
    return {
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "slug": organization.slug
        },
        "cloud_accounts": [
            {
                "id": str(account.id),
                "provider": account.provider,
                "account_id": account.account_id,
                "account_alias": account.account_alias,
                "status": "connected" if account.is_active else "disconnected",
                "connected_at": account.created_at.isoformat(),
                "resource_count": 0  # Would be calculated
            }
            for account in cloud_accounts
        ],
        "resources": [
            {
                "id": str(resource.id),
                "name": resource.name or resource.resource_id,
                "type": resource.resource_type,
                "provider": resource.provider,
                "region": resource.region,
                "cost": float(resource.cost_estimate or 0),
                "security_score": resource.security_score or 0,
                "optimization_score": resource.optimization_score or 0,
                "status": resource.status or "unknown",
                "last_seen": resource.last_seen_at.isoformat() if resource.last_seen_at else None
            }
            for resource in resources
        ],
        "metrics": {
            "total_resources": total_resources,
            "total_cost": total_cost,
            "security_score": round(avg_security_score, 1),
            "optimization_score": round(avg_optimization_score, 1)
        },
        "recent_activities": recent_activities
    }

@router.get("/metrics")
async def get_dashboard_metrics(
    time_range: str = "7d",
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get time-series metrics for dashboard charts."""
    
    # Calculate date range
    end_date = datetime.utcnow()
    if time_range == "24h":
        start_date = end_date - timedelta(days=1)
        interval = "hour"
    elif time_range == "7d":
        start_date = end_date - timedelta(days=7)
        interval = "day"
    elif time_range == "30d":
        start_date = end_date - timedelta(days=30)
        interval = "day"
    else:
        start_date = end_date - timedelta(days=7)
        interval = "day"
    
    # Generate mock time-series data
    # In production, this would query the time-series database
    
    days = (end_date - start_date).days
    cost_data = []
    security_data = []
    resource_data = []
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        cost_data.append({
            "date": date.isoformat(),
            "cost": 1000 + (i * 50)  # Mock increasing cost
        })
        security_data.append({
            "date": date.isoformat(),
            "score": 85 + (i % 10)  # Mock fluctuating score
        })
        resource_data.append({
            "date": date.isoformat(),
            "count": 500 + (i * 20)  # Mock increasing resource count
        })
    
    return {
        "cost_trend": cost_data,
        "security_trend": security_data,
        "resource_trend": resource_data,
        "interval": interval,
        "time_range": time_range
    }

@router.get("/recommendations")
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get AI-powered recommendations."""
    
    recommendations = [
        {
            "id": "1",
            "type": "cost",
            "severity": "high",
            "title": "Right-size EC2 instances",
            "description": "3 EC2 instances are over-provisioned and could be downsized",
            "estimated_savings": 450,
            "impact": "medium",
            "resources_affected": 3
        },
        {
            "id": "2",
            "type": "security",
            "severity": "critical",
            "title": "Secure public S3 bucket",
            "description": "S3 bucket 'logs-bucket' is publicly accessible",
            "estimated_savings": 0,
            "impact": "high",
            "resources_affected": 1
        },
        {
            "id": "3",
            "type": "compliance",
            "severity": "medium",
            "title": "Enable encryption at rest",
            "description": "2 RDS instances don't have encryption enabled",
            "estimated_savings": 50,
            "impact": "medium",
            "resources_affected": 2
        },
        {
            "id": "4",
            "type": "optimization",
            "severity": "low",
            "title": "Delete unused EBS volumes",
            "description": "5 EBS volumes are unattached and incurring costs",
            "estimated_savings": 120,
            "impact": "low",
            "resources_affected": 5
        }
    ]
    
    return {
        "recommendations": recommendations,
        "total": len(recommendations),
        "high_priority": len([r for r in recommendations if r["severity"] == "high" or r["severity"] == "critical"])
    }