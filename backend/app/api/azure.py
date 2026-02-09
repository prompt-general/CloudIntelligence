from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.models.cloud_account import CloudAccount
from app.services.azure.scanner import AzureScanner
from pydantic import BaseModel
import uuid
from datetime import datetime

router = APIRouter(prefix="/azure", tags=["azure"])

class AzureAccountCreate(BaseModel):
    subscription_id: str
    account_name: str
    tenant_id: str
    client_id: str
    client_secret: Optional[str] = None  # In production, use encrypted secret storage

@router.post("/accounts")
async def connect_azure_account(
    account: AzureAccountCreate,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Connect a new Azure subscription."""
    
    new_account = CloudAccount(
        id=str(uuid.uuid4()),
        organization_id=organization.id,
        name=account.account_name,
        provider="azure",
        account_ref=account.subscription_id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.add(new_account)
    await db.commit()
    
    return {
        "status": "connected",
        "account_id": new_account.id,
        "subscription_id": account.subscription_id
    }

@router.get("/accounts")
async def list_azure_accounts(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """List all connected Azure subscriptions."""
    from sqlalchemy import select
    result = await db.execute(
        select(CloudAccount).where(
            CloudAccount.organization_id == organization.id,
            CloudAccount.provider == "azure"
        )
    )
    accounts = result.scalars().all()
    return accounts
