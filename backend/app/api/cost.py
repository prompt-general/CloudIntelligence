from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.services.cost.analyzer import CostAnalyzer, CostGranularity
from app.services.cost.forecaster import CostForecaster
from app.services.cost.budget_manager import BudgetManager, BudgetPeriod
from pydantic import BaseModel

router = APIRouter(prefix="/cost", tags=["cost"])

class CostAnalysisRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    granularity: str = "daily"
    group_by: List[str] = ["service"]

class BudgetCreateRequest(BaseModel):
    name: str
    amount: float
    period: str = "monthly"
    categories: Optional[List[str]] = None
    alert_thresholds: Optional[Dict[str, float]] = None

@router.get("/analysis")
async def get_cost_analysis(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    granularity: str = Query("daily", description="Granularity: daily, weekly, monthly"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get cost analysis for the organization."""
    
    # Set default dates if not provided
    if not end_date:
        end_date = datetime.utcnow()
    else:
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    if not start_date:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    
    # Validate granularity
    try:
        cost_granularity = CostGranularity(granularity)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid granularity")
    
    # Analyze cost
    analyzer = CostAnalyzer(db)
    analysis = await analyzer.analyze_cost(
        organization_id=str(organization.id),
        start_date=start_date,
        end_date=end_date,
        granularity=cost_granularity
    )
    
    # Get recommendations
    recommendations = await analyzer.generate_recommendations(str(organization.id))
    
    return {
        "period": {
            "start": analysis.period_start.isoformat(),
            "end": analysis.period_end.isoformat()
        },
        "total_cost": analysis.total_cost,
        "breakdown": {
            "by_service": analysis.by_service,
            "by_region": analysis.by_region,
            "by_account": analysis.by_account
        },
        "trend_percentage": analysis.trend_percentage,
        "forecast_30d": analysis.forecast_30d,
        "anomalies": analysis.anomalies,
        "recommendations": [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "estimated_savings": r.estimated_savings,
                "implementation_effort": r.implementation_effort,
                "risk": r.risk,
                "action_type": r.action_type,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id
            }
            for r in recommendations
        ]
    }

@router.get("/forecast")
async def get_cost_forecast(
    periods: int = Query(30, description="Forecast periods"),
    frequency: str = Query("D", description="Frequency: D (daily), W (weekly), M (monthly)"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get cost forecast for the organization."""
    
    forecaster = CostForecaster(db)
    
    # Validate frequency
    valid_frequencies = {'D': 'daily', 'W': 'weekly', 'M': 'monthly'}
    if frequency not in valid_frequencies:
        raise HTTPException(status_code=400, detail="Invalid frequency")
    
    forecast = await forecaster.forecast(
        organization_id=str(organization.id),
        periods=periods,
        frequency=valid_frequencies[frequency]
    )
    
    # Get anomalies
    anomalies = await forecaster.detect_anomalies(str(organization.id))
    
    return {
        "forecast": forecast,
        "anomalies": anomalies,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/savings-opportunity")
async def get_savings_opportunity(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get total savings opportunity."""
    
    analyzer = CostAnalyzer(db)
    savings = await analyzer.calculate_savings_opportunity(str(organization.id))
    
    return savings

@router.post("/budgets")
async def create_budget(
    request: BudgetCreateRequest,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Create a new budget."""
    
    try:
        budget_period = BudgetPeriod(request.period)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid budget period")
    
    manager = BudgetManager(db)
    budget = await manager.create_budget(
        organization_id=str(organization.id),
        name=request.name,
        amount=request.amount,
        period=budget_period,
        categories=request.categories,
        alert_thresholds=request.alert_thresholds
    )
    
    return {
        "id": budget.id,
        "name": budget.name,
        "amount": budget.amount,
        "period": budget.period.value,
        "start_date": budget.start_date.isoformat(),
        "end_date": budget.end_date.isoformat(),
        "status": budget.status,
        "message": "Budget created successfully"
    }

@router.get("/budgets")
async def get_budgets(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get all budgets for the organization."""
    
    manager = BudgetManager(db)
    budget_health = await manager.get_budget_health(str(organization.id))
    
    return budget_health

@router.post("/budgets/check")
async def check_budgets(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Check budgets and generate alerts."""
    
    manager = BudgetManager(db)
    alerts = await manager.check_budgets(str(organization.id))
    
    return {
        "alerts_generated": len(alerts),
        "alerts": [
            {
                "id": alert.id,
                "budget_id": alert.budget_id,
                "type": alert.type,
                "severity": alert.severity,
                "message": alert.message,
                "actual_amount": alert.actual_amount,
                "threshold_amount": alert.threshold_amount,
                "triggered_at": alert.triggered_at.isoformat()
            }
            for alert in alerts
        ]
    }

@router.post("/what-if")
async def what_if_analysis(
    scenarios: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Perform what-if analysis for cost scenarios."""
    
    forecaster = CostForecaster(db)
    results = await forecaster.what_if_analysis(str(organization.id), scenarios)
    
    return {
        "scenarios_analyzed": len(scenarios),
        "results": results,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/trends")
async def get_cost_trends(
    days: int = Query(90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get cost trends over time."""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    analyzer = CostAnalyzer(db)
    analysis = await analyzer.analyze_cost(
        organization_id=str(organization.id),
        start_date=start_date,
        end_date=end_date,
        granularity=CostGranularity.DAILY
    )
    
    # Generate trend data points
    trend_data = []
    current = start_date
    
    # This would come from time-series database
    # For now, generate mock trend
    base_cost = 1000
    daily_growth = 1.01  # 1% daily growth
    
    for i in range(days):
        daily_cost = base_cost * (daily_growth ** i)
        trend_data.append({
            "date": (start_date + timedelta(days=i)).isoformat(),
            "cost": daily_cost,
            "cumulative": sum(d['cost'] for d in trend_data) + daily_cost
        })
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days
        },
        "total_cost": sum(d['cost'] for d in trend_data),
        "average_daily": sum(d['cost'] for d in trend_data) / days,
        "trend_data": trend_data,
        "growth_rate_percent": (daily_growth - 1) * 100
    }