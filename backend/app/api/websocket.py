from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
import asyncio
from datetime import datetime
from app.auth.dependencies import decode_access_token

router = APIRouter()

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def broadcast(self, message: dict):
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    
    try:
        # Initial handshake
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to CloudIntelligence real-time updates",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Send initial data
        await websocket.send_json({
            "type": "initial_data",
            "data": {
                "connected_accounts": 3,
                "total_resources": 156,
                "active_alerts": 2,
                "recent_changes": []
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and send periodic updates
        while True:
            # Wait for client message (heartbeat)
            data = await websocket.receive_text()
            
            # Parse message
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message.get("type") == "subscribe":
                    # Handle subscription requests
                    await websocket.send_json({
                        "type": "subscribed",
                        "channels": message.get("channels", []),
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            except json.JSONDecodeError:
                # Invalid JSON, ignore
                pass
            
            # Send mock real-time updates (in production, these would come from Kafka)
            await asyncio.sleep(10)  # Send update every 10 seconds
            
            # Simulate real-time resource changes
            import random
            changes = [
                {
                    "id": f"change_{random.randint(1000, 9999)}",
                    "resource_type": random.choice(["ec2", "s3", "rds", "lambda"]),
                    "action": random.choice(["created", "modified", "deleted"]),
                    "resource_name": f"resource-{random.randint(1, 100)}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "impact": random.choice(["low", "medium", "high"])
                }
            ]
            
            await websocket.send_json({
                "type": "resource_change",
                "changes": changes,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    except WebSocketDisconnect:
        # Handle disconnection
        print("Client disconnected")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()

@router.websocket("/ws/secure")
async def secure_websocket_endpoint(websocket: WebSocket):
    """Secure WebSocket endpoint with authentication."""
    # Get token from query parameters
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=1008)  # Policy violation
        return
    
    # Verify token
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=1008)
        return
    
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Process incoming messages
            try:
                message = json.loads(data)
                await handle_secure_message(message, user_id, websocket)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "error": "Invalid JSON",
                    "type": "error"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

async def handle_secure_message(message: dict, user_id: str, websocket: WebSocket):
    """Handle incoming WebSocket messages."""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        # Handle subscription to channels
        channels = message.get("channels", [])
        await websocket.send_json({
            "type": "subscription_confirmed",
            "channels": channels,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif message_type == "unsubscribe":
        # Handle unsubscription
        await websocket.send_json({
            "type": "unsubscribed",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif message_type == "request_data":
        # Handle data requests
        data_type = message.get("data_type")
        
        if data_type == "alerts":
            await send_alerts(websocket)
        elif data_type == "metrics":
            await send_metrics(websocket)
        elif data_type == "recommendations":
            await send_recommendations(websocket)

async def send_alerts(websocket: WebSocket):
    """Send current alerts."""
    alerts = [
        {
            "id": "alert_1",
            "severity": "high",
            "type": "security",
            "title": "Public S3 bucket detected",
            "description": "Bucket 'logs-backup' is publicly accessible",
            "resource_id": "bucket-123",
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "id": "alert_2",
            "severity": "medium",
            "type": "cost",
            "title": "High spend detected",
            "description": "EC2 instance 'web-server-1' costing $450/month",
            "resource_id": "i-1234567890",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]
    
    await websocket.send_json({
        "type": "alerts",
        "alerts": alerts,
        "timestamp": datetime.utcnow().isoformat()
    })

async def send_metrics(websocket: WebSocket):
    """Send current metrics."""
    import random
    
    metrics = {
        "cpu_usage": random.randint(10, 90),
        "memory_usage": random.randint(20, 80),
        "network_in": random.randint(100, 1000),
        "network_out": random.randint(100, 1000),
        "active_connections": random.randint(50, 200)
    }
    
    await websocket.send_json({
        "type": "metrics",
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    })

async def send_recommendations(websocket: WebSocket):
    """Send AI recommendations."""
    recommendations = [
        {
            "id": "rec_1",
            "priority": "high",
            "type": "cost",
            "title": "Resize EC2 instance",
            "description": "Instance t3.large is underutilized (15% CPU)",
            "estimated_savings": 120,
            "action": "resize_instance",
            "resources": ["i-1234567890"]
        }
    ]
    
    await websocket.send_json({
        "type": "recommendations",
        "recommendations": recommendations,
        "timestamp": datetime.utcnow().isoformat()
    })