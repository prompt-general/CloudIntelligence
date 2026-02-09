from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.models.cloud_account import CloudAccount
from app.services.gcp.scanner import GCPScanner
from pydantic import BaseModel
import uuid
from datetime import datetime

router = APIRouter(prefix="/gcp", tags=["gcp"])

class GCPAccountCreate(BaseModel):
    project_id: str
    account_name: str
    credentials_json: Optional[str] = None  # In production, use encrypted secret storage

@router.post("/accounts")
async def connect_gcp_account(
    account: GCPAccountCreate,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Connect a new GCP account/project."""
    
    new_account = CloudAccount(
        id=str(uuid.uuid4()),
        organization_id=organization.id,
        name=account.account_name,
        provider="gcp",
        account_ref=account.project_id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.add(new_account)
    await db.commit()
    
    return {
        "status": "connected",
        "account_id": new_account.id,
        "project_id": account.project_id
    }

@router.get("/accounts")
async def list_gcp_accounts(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """List all connected GCP accounts."""
    from sqlalchemy import select
    result = await db.execute(
        select(CloudAccount).where(
            CloudAccount.organization_id == organization.id,
            CloudAccount.provider == "gcp"
        )
    )
    accounts = result.scalars().all()
    return accounts
