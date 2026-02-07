from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

class BudgetPeriod(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"

class AlertThreshold(Enum):
    ACTUAL = "actual"
    FORECASTED = "forecasted"

@dataclass
class Budget:
    id: str
    name: str
    period: BudgetPeriod
    amount: float
    start_date: datetime
    end_date: datetime
    categories: List[str]  # services, accounts, etc.
    alert_thresholds: Dict[str, float]  # percentage thresholds
    status: str  # active, paused, completed

@dataclass
class BudgetAlert:
    id: str
    budget_id: str
    type: str  # threshold_exceeded, forecast_exceeded, etc.
    severity: str  # info, warning, critical
    message: str
    actual_amount: float
    threshold_amount: float
    triggered_at: datetime

class BudgetManager:
    """Manage budgets and alerts for cloud costs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_budget(
        self,
        organization_id: str,
        name: str,
        amount: float,
        period: BudgetPeriod = BudgetPeriod.MONTHLY,
        categories: Optional[List[str]] = None,
        alert_thresholds: Optional[Dict[str, float]] = None
    ) -> Budget:
        """Create a new budget."""
        from app.models.budget import Budget as BudgetModel
        
        if alert_thresholds is None:
            alert_thresholds = {'50': 0.5, '80': 0.8, '100': 1.0}
        
        if categories is None:
            categories = ['all']
        
        # Calculate dates based on period
        start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if period == BudgetPeriod.MONTHLY:
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        elif period == BudgetPeriod.QUARTERLY:
            end_date = (start_date + timedelta(days=93)).replace(day=1) - timedelta(seconds=1)
        else:  # annual
            end_date = start_date.replace(year=start_date.year + 1) - timedelta(seconds=1)
        
        budget = BudgetModel(
            organization_id=organization_id,
            name=name,
            period=period.value,
            amount=amount,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            alert_thresholds=alert_thresholds,
            status='active'
        )
        
        self.db.add(budget)
        await self.db.commit()
        await self.db.refresh(budget)
        
        return Budget(
            id=str(budget.id),
            name=budget.name,
            period=BudgetPeriod(budget.period),
            amount=budget.amount,
            start_date=budget.start_date,
            end_date=budget.end_date,
            categories=budget.categories,
            alert_thresholds=budget.alert_thresholds,
            status=budget.status
        )
    
    async def check_budgets(self, organization_id: str) -> List[BudgetAlert]:
        """Check all budgets and generate alerts if needed."""
        from app.models.budget import Budget as BudgetModel
        
        result = await self.db.execute(
            select(BudgetModel).where(
                and_(
                    BudgetModel.organization_id == organization_id,
                    BudgetModel.status == 'active'
                )
            )
        )
        budgets = result.scalars().all()
        
        alerts = []
        
        for budget_model in budgets:
            # Get actual spend for budget period
            actual_spend = await self._get_actual_spend(
                organization_id,
                budget_model.start_date,
                budget_model.end_date,
                budget_model.categories
            )
            
            # Check threshold alerts
            for threshold_name, threshold_percent in budget_model.alert_thresholds.items():
                threshold_amount = budget_model.amount * threshold_percent
                
                if actual_spend >= threshold_amount:
                    # Check if alert already exists
                    existing_alert = await self._check_existing_alert(
                        budget_model.id,
                        f"threshold_{threshold_name}",
                        budget_model.start_date
                    )
                    
                    if not existing_alert:
                        alert = BudgetAlert(
                            id=f"alert_{budget_model.id}_{threshold_name}",
                            budget_id=str(budget_model.id),
                            type=f"threshold_{threshold_name}",
                            severity=self._get_alert_severity(threshold_percent),
                            message=f"Budget '{budget_model.name}' has reached {int(threshold_percent*100)}% of limit (${actual_spend:,.2f} / ${budget_model.amount:,.2f})",
                            actual_amount=actual_spend,
                            threshold_amount=threshold_amount,
                            triggered_at=datetime.utcnow()
                        )
                        
                        alerts.append(alert)
                        
                        # Save alert to database
                        await self._save_alert(alert, organization_id)
            
            # Check forecast exceed
            forecast = await self._get_forecast_spend(
                organization_id,
                budget_model.end_date,
                budget_model.categories
            )
            
            if forecast > budget_model.amount:
                alert = BudgetAlert(
                    id=f"alert_{budget_model.id}_forecast",
                    budget_id=str(budget_model.id),
                    type="forecast_exceeded",
                    severity="critical",
                    message=f"Budget '{budget_model.name}' forecasted to exceed by ${forecast - budget_model.amount:,.2f}",
                    actual_amount=forecast,
                    threshold_amount=budget_model.amount,
                    triggered_at=datetime.utcnow()
                )
                
                alerts.append(alert)
                await self._save_alert(alert, organization_id)
        
        return alerts
    
    async def _get_actual_spend(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        categories: List[str]
    ) -> float:
        """Get actual spend for the given period and categories."""
        # This would query the time-series database
        # For now, return mock data
        
        # Calculate days in period
        days = (end_date - start_date).days
        
        # Base cost with some randomness
        base_cost = 5000
        cost = base_cost * (days / 30)  # Scale by days
        
        return cost
    
    async def _get_forecast_spend(
        self,
        organization_id: str,
        end_date: datetime,
        categories: List[str]
    ) -> float:
        """Get forecasted spend until end date."""
        days_remaining = (end_date - datetime.utcnow()).days
        
        if days_remaining <= 0:
            return 0
        
        # Get current monthly spend
        current_monthly = 10000  # Mock value
        
        # Project for remaining days
        return current_monthly * (days_remaining / 30)
    
    def _get_alert_severity(self, threshold_percent: float) -> str:
        """Determine alert severity based on threshold."""
        if threshold_percent >= 1.0:
            return "critical"
        elif threshold_percent >= 0.8:
            return "warning"
        else:
            return "info"
    
    async def _check_existing_alert(
        self,
        budget_id: str,
        alert_type: str,
        period_start: datetime
    ) -> bool:
        """Check if alert already exists for this period."""
        # Query database for existing alerts
        return False  # Simplified for now
    
    async def _save_alert(self, alert: BudgetAlert, organization_id: str):
        """Save alert to database."""
        from app.models.budget import BudgetAlert as BudgetAlertModel
        
        alert_model = BudgetAlertModel(
            organization_id=organization_id,
            budget_id=alert.budget_id,
            type=alert.type,
            severity=alert.severity,
            message=alert.message,
            actual_amount=alert.actual_amount,
            threshold_amount=alert.threshold_amount
        )
        
        self.db.add(alert_model)
        await self.db.commit()
    
    async def get_budget_health(self, organization_id: str) -> Dict[str, Any]:
        """Get overall budget health for the organization."""
        from app.models.budget import Budget as BudgetModel
        
        result = await self.db.execute(
            select(BudgetModel).where(
                and_(
                    BudgetModel.organization_id == organization_id,
                    BudgetModel.status == 'active'
                )
            )
        )
        budgets = result.scalars().all()
        
        total_budget = sum(b.amount for b in budgets)
        total_forecast = 0
        total_actual = 0
        
        healthy_budgets = 0
        at_risk_budgets = 0
        exceeded_budgets = 0
        
        budget_details = []
        
        for budget in budgets:
            actual_spend = await self._get_actual_spend(
                organization_id,
                budget.start_date,
                budget.end_date,
                budget.categories
            )
            
            forecast_spend = await self._get_forecast_spend(
                organization_id,
                budget.end_date,
                budget.categories
            )
            
            utilization = (actual_spend / budget.amount) * 100 if budget.amount > 0 else 0
            
            status = "healthy"
            if forecast_spend > budget.amount:
                status = "exceeded"
                exceeded_budgets += 1
            elif utilization > 80:
                status = "at_risk"
                at_risk_budgets += 1
            else:
                healthy_budgets += 1
            
            budget_details.append({
                'id': str(budget.id),
                'name': budget.name,
                'period': budget.period,
                'amount': budget.amount,
                'actual_spend': actual_spend,
                'forecast_spend': forecast_spend,
                'utilization_percent': utilization,
                'status': status,
                'days_remaining': (budget.end_date - datetime.utcnow()).days
            })
            
            total_actual += actual_spend
            total_forecast += forecast_spend
        
        overall_utilization = (total_actual / total_budget) * 100 if total_budget > 0 else 0
        
        return {
            'total_budgets': len(budgets),
            'total_budget_amount': total_budget,
            'total_actual_spend': total_actual,
            'total_forecast_spend': total_forecast,
            'overall_utilization_percent': overall_utilization,
            'budget_health': {
                'healthy': healthy_budgets,
                'at_risk': at_risk_budgets,
                'exceeded': exceeded_budgets
            },
            'budgets': budget_details,
            'last_updated': datetime.utcnow().isoformat()
        }