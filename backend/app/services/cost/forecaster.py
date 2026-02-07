import pandas as pd
import numpy as np
from prophet import Prophet
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CostForecaster:
    """Time-series forecasting for cloud costs using Facebook Prophet."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.models: Dict[str, Prophet] = {}
    
    async def train_models(self, organization_id: str) -> Dict[str, Any]:
        """Train forecasting models for the organization."""
        # Get historical cost data
        historical_data = await self._get_historical_cost_data(organization_id, days=365)
        
        if len(historical_data) < 30:
            logger.warning(f"Insufficient data for training: {len(historical_data)} days")
            return {"status": "insufficient_data", "days": len(historical_data)}
        
        # Convert to DataFrame
        df = pd.DataFrame(historical_data)
        df['ds'] = pd.to_datetime(df['date'])
        df['y'] = df['cost']
        
        # Train overall cost model
        overall_model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode='multiplicative'
        )
        
        # Add custom seasonality for month ends
        overall_model.add_seasonality(
            name='monthly',
            period=30.5,
            fourier_order=5
        )
        
        overall_model.fit(df[['ds', 'y']])
        
        # Train service-specific models
        service_models = {}
        services = df['service'].unique()
        
        for service in services[:5]:  # Limit to top 5 services
            service_df = df[df['service'] == service]
            if len(service_df) > 30:
                service_model = Prophet(
                    yearly_seasonality=True,
                    weekly_seasonality=True,
                    daily_seasonality=False
                )
                service_model.fit(service_df[['ds', 'y']])
                service_models[service] = service_model
        
        # Store models
        self.models[f"org_{organization_id}_overall"] = overall_model
        for service, model in service_models.items():
            self.models[f"org_{organization_id}_{service}"] = model
        
        return {
            "status": "trained",
            "models_trained": len(service_models) + 1,
            "training_days": len(df),
            "services_modeled": list(service_models.keys())
        }
    
    async def forecast(
        self,
        organization_id: str,
        periods: int = 30,
        frequency: str = 'D'
    ) -> Dict[str, Any]:
        """Generate cost forecast for the organization."""
        model_key = f"org_{organization_id}_overall"
        
        if model_key not in self.models:
            await self.train_models(organization_id)
        
        model = self.models.get(model_key)
        if not model:
            return {"error": "Model not available"}
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=periods, freq=frequency)
        
        # Generate forecast
        forecast = model.predict(future)
        
        # Calculate confidence intervals
        forecast_result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
        
        # Convert to list of dicts
        forecast_data = []
        for _, row in forecast_result.iterrows():
            forecast_data.append({
                'date': row['ds'].isoformat(),
                'forecast': float(row['yhat']),
                'lower_bound': float(row['yhat_lower']),
                'upper_bound': float(row['yhat_upper'])
            })
        
        # Calculate forecast summary
        total_forecast = sum(row['forecast'] for row in forecast_data)
        
        # Get actual data for comparison
        actual_data = await self._get_historical_cost_data(organization_id, days=30)
        total_actual = sum(row['cost'] for row in actual_data)
        
        growth_rate = ((total_forecast / 30) - (total_actual / 30)) / (total_actual / 30) * 100
        
        # Generate service-level forecasts
        service_forecasts = {}
        for key in self.models.keys():
            if key.startswith(f"org_{organization_id}_") and key != model_key:
                service = key.split('_')[-1]
                service_model = self.models[key]
                
                service_future = service_model.make_future_dataframe(periods=periods, freq=frequency)
                service_forecast = service_model.predict(service_future)
                
                service_total = service_forecast['yhat'].tail(periods).sum()
                service_forecasts[service] = float(service_total)
        
        return {
            'forecast_period': periods,
            'frequency': frequency,
            'total_forecast': total_forecast,
            'daily_forecast': total_forecast / periods,
            'growth_rate_percent': growth_rate,
            'confidence_interval': {
                'lower': forecast_result['yhat_lower'].mean(),
                'upper': forecast_result['yhat_upper'].mean()
            },
            'forecast_data': forecast_data,
            'service_breakdown': service_forecasts,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    async def detect_anomalies(
        self,
        organization_id: str,
        confidence_level: float = 0.95
    ) -> List[Dict[str, Any]]:
        """Detect cost anomalies using forecast models."""
        model_key = f"org_{organization_id}_overall"
        
        if model_key not in self.models:
            await self.train_models(organization_id)
        
        model = self.models.get(model_key)
        if not model:
            return []
        
        # Get recent actual data
        recent_data = await self._get_historical_cost_data(organization_id, days=7)
        
        if not recent_data:
            return []
        
        # Create dataframe for prediction
        df = pd.DataFrame(recent_data)
        df['ds'] = pd.to_datetime(df['date'])
        
        # Predict for recent dates
        predictions = model.predict(df[['ds']])
        
        anomalies = []
        z_score_threshold = 2.0  # 2 standard deviations
        
        for i, row in df.iterrows():
            actual = row['cost']
            predicted = predictions.iloc[i]['yhat']
            std_dev = (predictions.iloc[i]['yhat_upper'] - predictions.iloc[i]['yhat_lower']) / 2
            
            if std_dev > 0:
                z_score = abs(actual - predicted) / std_dev
                
                if z_score > z_score_threshold:
                    anomalies.append({
                        'date': row['date'].isoformat(),
                        'actual_cost': actual,
                        'predicted_cost': predicted,
                        'deviation_percent': ((actual - predicted) / predicted) * 100,
                        'z_score': z_score,
                        'severity': 'high' if z_score > 3 else 'medium',
                        'service': row.get('service', 'overall')
                    })
        
        return anomalies
    
    async def _get_historical_cost_data(
        self,
        organization_id: str,
        days: int = 365
    ) -> List[Dict[str, Any]]:
        """Get historical cost data from database."""
        # This would query the time-series database
        # For now, generate mock data
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        mock_services = ["Amazon EC2", "Amazon S3", "Amazon RDS", "AWS Lambda"]
        
        data = []
        current_date = start_date
        
        # Generate trend with some randomness
        base_cost = 1000
        trend = 1.01  # 1% daily growth
        seasonality = lambda d: np.sin(d * 2 * np.pi / 30) * 0.2  # Monthly seasonality
        
        day_count = 0
        while current_date < end_date:
            trend_factor = trend ** day_count
            seasonal_factor = 1 + seasonality(day_count)
            noise = np.random.normal(1, 0.1)  # 10% random noise
            
            total_daily_cost = base_cost * trend_factor * seasonal_factor * noise
            
            # Distribute among services
            service_weights = np.random.dirichlet(np.ones(len(mock_services)))
            
            for i, service in enumerate(mock_services):
                service_cost = total_daily_cost * service_weights[i]
                
                data.append({
                    'date': current_date,
                    'service': service,
                    'cost': float(service_cost),
                    'organization_id': organization_id
                })
            
            current_date += timedelta(days=1)
            day_count += 1
        
        return data
    
    async def what_if_analysis(
        self,
        organization_id: str,
        scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform what-if analysis for different cost scenarios."""
        results = {}
        
        for scenario in scenarios:
            scenario_name = scenario.get('name', 'unknown')
            
            if scenario['type'] == 'resource_change':
                # Simulate adding/removing resources
                resource_cost = scenario.get('monthly_cost', 0)
                count = scenario.get('count', 1)
                action = scenario.get('action', 'add')  # add or remove
                
                # Get current forecast
                current_forecast = await self.forecast(organization_id, periods=30)
                current_monthly = current_forecast['total_forecast']
                
                # Calculate new forecast
                if action == 'add':
                    new_monthly = current_monthly + (resource_cost * count)
                else:
                    new_monthly = max(0, current_monthly - (resource_cost * count))
                
                results[scenario_name] = {
                    'current_monthly': current_monthly,
                    'new_monthly': new_monthly,
                    'change_amount': new_monthly - current_monthly,
                    'change_percent': ((new_monthly - current_monthly) / current_monthly) * 100,
                    'roi_months': scenario.get('roi_months', None),
                    'breakdown': scenario
                }
            
            elif scenario['type'] == 'pricing_change':
                # Simulate pricing changes (e.g., Reserved Instances)
                discount = scenario.get('discount_percent', 0) / 100
                affected_services = scenario.get('affected_services', ['Amazon EC2'])
                
                # Get service breakdown
                current_forecast = await self.forecast(organization_id, periods=30)
                service_breakdown = current_forecast.get('service_breakdown', {})
                
                # Calculate savings
                total_savings = 0
                for service, cost in service_breakdown.items():
                    if service in affected_services:
                        total_savings += cost * discount
                
                results[scenario_name] = {
                    'monthly_savings': total_savings,
                    'annual_savings': total_savings * 12,
                    'affected_services': affected_services,
                    'discount_percent': scenario['discount_percent'],
                    'payback_months': scenario.get('payback_months', 0)
                }
        
        return results