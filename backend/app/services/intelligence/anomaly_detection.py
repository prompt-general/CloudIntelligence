from typing import List, Dict, Any
import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """AI-powered anomaly detection for cloud events and costs."""
    
    def __init__(self):
        self.event_model = IsolationForest(contamination=0.05, random_state=42)
        self.cost_model = IsolationForest(contamination=0.1, random_state=42)

    async def detect_change_anomalies(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect unusual patterns in cloud change events."""
        if len(events) < 10:
            return []
            
        # Feature engineering from events
        # features: [hour_of_day, day_of_week, resource_type_id, action_id]
        data = []
        for event in events:
            ts = datetime.fromisoformat(event["timestamp"])
            data.append([
                ts.hour,
                ts.weekday(),
                self._map_res_type(event["resource_type"]),
                self._map_action(event["action"])
            ])
            
        X = np.array(data)
        predictions = self.event_model.fit_predict(X)
        
        anomalies = []
        for i, pred in enumerate(predictions):
            if pred == -1:  # Anomaly
                anomalies.append({
                    **events[i],
                    "anomaly_score": float(self.event_model.decision_function(X[i:i+1])[0]),
                    "detection_type": "event_pattern"
                })
                
        return sorted(anomalies, key=lambda x: x["anomaly_score"])

    def _map_res_type(self, res_type: str) -> int:
        mapping = {
            "ec2": 1, "s3": 2, "rds": 3, "lambda": 4, "iam": 5, 
            "gce": 6, "gcs": 7,
            "azure_vm": 8, "azure_storage": 9
        }
        return mapping.get(res_type.lower(), 0)

    def _map_action(self, action: str) -> int:
        mapping = {"created": 1, "modified": 2, "deleted": 3, "accessed": 4}
        return mapping.get(action.lower(), 0)

    async def detect_cost_spike(self, daily_costs: List[float]) -> bool:
        """Simple statistical anomaly detection for cost spikes."""
        if len(daily_costs) < 7:
            return False
            
        mean = np.mean(daily_costs[:-1])
        std = np.std(daily_costs[:-1])
        current = daily_costs[-1]
        
        # Z-score > 3 is considered a significant spike
        if std > 0:
            z_score = (current - mean) / std
            return z_score > 3
        return False
