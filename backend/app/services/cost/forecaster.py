from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

logger = logging.getLogger(__name__)

class CostForecaster:
    """AI-powered cost forecasting and anomaly detection."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Prophet model would be initialized here in production
        self.models = {}

    async def forecast(self, organization_id: str, periods: int = 30, frequency: str = "daily") -> List[Dict[str, Any]]:
        """Generate cost forecast for the given organization."""
        # Get historical data
        df = await self._get_historical_cost_data(organization_id)
        if df.empty:
            return []
            
        # Mock forecasting logic
        last_date = df['ds'].max()
        last_val = df['y'].iloc[-1]
        
        forecast = []
        for i in range(1, periods + 1):
            next_date = last_date + timedelta(days=i)
            # Add some linear growth and randomness
            val = last_val * (1 + (0.002 * i)) + (np.random.normal(0, last_val * 0.05))
            forecast.append({
                "ds": next_date.isoformat(),
                "yhat": float(val),
                "yhat_lower": float(val * 0.9),
                "yhat_upper": float(val * 1.1)
            })
            
        return forecast

    async def _get_historical_cost_data(self, organization_id: str) -> pd.DataFrame:
        """Fetch historical cost data from database."""
        # Mock historical data
        dates = pd.date_range(end=datetime.utcnow(), periods=90)
        base_cost = 500
        costs = [base_cost * (1.001 ** i) + np.random.normal(0, 20) for i in range(90)]
        
        return pd.DataFrame({
            'ds': dates,
            'y': costs
        })

    async def detect_anomalies(self, organization_id: str, confidence_level: float = 0.95) -> List[Dict[str, Any]]:
        """Detect cost anomalies in historical data."""
        df = await self._get_historical_cost_data(organization_id)
        if df.empty:
            return []
            
        # Z-score based anomaly detection
        mean = df['y'].mean()
        std = df['y'].std()
        
        anomalies = []
        for i, row in df.iterrows():
            z_score = abs(row['y'] - mean) / std if std > 0 else 0
            if z_score > 3:  # 3 standard deviations
                anomalies.append({
                    "date": row['ds'].isoformat(),
                    "actual": float(row['y']),
                    "expected": float(mean),
                    "severity": "high" if z_score > 5 else "medium",
                    "z_score": float(z_score)
                })
                
        return anomalies

    async def what_if_analysis(self, organization_id: str, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform what-if analysis for different cost reduction or growth scenarios."""
        results = {}
        for scenario in scenarios:
            name = scenario.get("name", "Unnamed Scenario")
            # Calculate impact of scenario
            results[name] = {
                "original_forecast": 15000,
                "scenario_forecast": 15000 * (1 - scenario.get("impact", 0)),
                "estimated_savings": 15000 * scenario.get("impact", 0)
            }
        return results

    async def predict_resource_cost_30d(self, resource_id: str, current_daily_cost: float) -> float:
        """Predict the cost of a specific resource for the next 30 days based on trends."""
        growth_factor = 1.02
        predicted_total = 0
        for day in range(1, 31):
            daily_cost = current_daily_cost * (1 + (day * 0.001)) 
            predicted_total += daily_cost
        return float(predicted_total)

    async def generate_intelligence_profile(self, resource_id: str, organization_id: str) -> Dict[str, Any]:
        """Generate a complete intelligence profile for a resource."""
        current_daily = 10.5 
        predicted_30d = await self.predict_resource_cost_30d(resource_id, current_daily)
        all_anomalies = await self.detect_anomalies(organization_id)
        resource_anomalies = [a for a in all_anomalies if a.get("resource_id") == resource_id]
        return {
            "resource_id": resource_id,
            "predicted_cost_30d": predicted_30d,
            "anomalies_detected": len(resource_anomalies),
            "cost_trend": "stable" if len(resource_anomalies) == 0 else "volatile",
            "confidence_score": 0.85
        }