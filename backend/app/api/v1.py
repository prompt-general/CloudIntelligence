from fastapi import APIRouter
from typing import List, Dict, Any, Optional
from app.api import dashboard, cost, security, compliance, aws, remediation, websocket, gcp, azure

router = APIRouter()

router.include_router(dashboard.router)
router.include_router(cost.router)
router.include_router(security.router)
router.include_router(compliance.router)
router.include_router(aws.router)
router.include_router(remediation.router)
router.include_router(websocket.router)
router.include_router(gcp.router)
router.include_router(azure.router)
