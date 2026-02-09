from typing import Dict, Any, List
from datetime import datetime
import json
import logging
from app.services.intelligence.anomaly_detection import AnomalyDetector
from app.api.websocket import manager

logger = logging.getLogger(__name__)

class IngestionEngine:
    """Engine for ingesting cloud change events and running real-time analysis."""
    
    def __init__(self, db):
        self.db = db
        self.anomaly_detector = AnomalyDetector()

    async def handle_change_event(self, event_data: Dict[str, Any], organization_id: str):
        """Process an incoming CloudChangeEvent."""
        logger.info(f"Ingesting event: {event_data.get('action')} on {event_data.get('resource_id')}")
        
        # 1. Normalize event
        event = self._normalize_event(event_data)
        
        # 2. Store event in time-series DB (Mocked for now)
        await self._store_event(event, organization_id)
        
        # 3. Run Anomaly Detection
        # In a real scenario, we'd pull recent events for this resource/account
        recent_events = await self._get_recent_events(organization_id, limit=20)
        anomalies = await self.anomaly_detector.detect_change_anomalies(recent_events + [event])
        
        # 4. If anomaly detected, trigger alerts
        is_anomalous = any(a["id"] == event["id"] for a in anomalies)
        if is_anomalous:
            await self._trigger_anomaly_alert(event, organization_id)
            
        # 5. Broadcast change via WebSocket
        await manager.broadcast({
            "type": "resource_change",
            "event": event,
            "is_anomalous": is_anomalous,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "event_id": event["id"],
            "status": "processed",
            "is_anomalous": is_anomalous
        }

    def _normalize_event(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize different provider events into CloudChangeEvent schema."""
        return {
            "id": raw_event.get("id", f"evt_{datetime.utcnow().timestamp()}"),
            "provider": raw_event.get("provider", "aws"),
            "account_id": raw_event.get("account_id"),
            "region": raw_event.get("region"),
            "resource_id": raw_event.get("resource_id"),
            "resource_type": raw_event.get("resource_type"),
            "action": raw_event.get("action"),
            "actor": raw_event.get("actor", "system"),
            "timestamp": raw_event.get("timestamp", datetime.utcnow().isoformat()),
            "diff": raw_event.get("diff", {})
        }

    async def _store_event(self, event: Dict[str, Any], organization_id: str):
        # Implementation for storing in TimescaleDB/Postgres
        pass

    async def _get_recent_events(self, organization_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        # Mock retrieval of recent events for the context of anomaly detection
        return []

    async def _trigger_anomaly_alert(self, event: Dict[str, Any], organization_id: str):
        logger.warning(f"ANOMALY DETECTED: {event['action']} on {event['resource_id']} by {event['actor']}")
        # Integration with notification service (Slack, Email, PagerDuty) would go here
