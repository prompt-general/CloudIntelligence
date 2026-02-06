from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.models.cloud_account import CloudAccount
from app.schemas.cloud_account import (
    CloudAccountCreate,
    CloudAccountResponse,
    AWSOnboardingResponse,
    ResourceListResponse
)
from app.services.aws.iam_generator import IAMGenerator
from app.services.aws.client import AWSClient
from datetime import datetime, timedelta

router = APIRouter(prefix="/aws", tags=["aws"])

@router.post("/onboarding/generate", response_model=AWSOnboardingResponse)
async def generate_aws_onboarding_template(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """Generate AWS IAM role templates for onboarding."""
    external_id = IAMGenerator.generate_external_id()
    
    # Store external ID in database for later verification
    # This would typically be stored in a CloudAccount record
    
    return AWSOnboardingResponse(
        external_id=external_id,
        cloudformation_template=IAMGenerator.generate_cloudformation_template(external_id),
        terraform_config=IAMGenerator.generate_terraform_config(external_id),
        manual_instructions={
            "steps": [
                "1. Deploy the CloudFormation template or Terraform configuration in your AWS account",
                "2. Copy the generated Role ARN",
                "3. Provide the Role ARN and External ID when connecting your account in CloudIntelligence"
            ]
        }
    )

@router.post("/accounts/connect", response_model=CloudAccountResponse)
async def connect_aws_account(
    account_data: CloudAccountCreate,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Connect an AWS account using IAM role ARN."""
    # Validate the connection by trying to assume the role
    aws_client = AWSClient()
    
    try:
        # Test role assumption
        credentials = await aws_client.assume_role(
            role_arn=account_data.role_arn,
            external_id=account_data.external_id
        )
        
        # Get account ID from ARN
        # arn:aws:iam::123456789012:role/RoleName
        account_id = account_data.role_arn.split(":")[4]
        
        # Get account alias if possible
        session = await aws_client.get_session(
            account_data.role_arn,
            account_data.external_id
        )
        
        def _get_account_alias():
            iam_client = session.client('iam')
            aliases = iam_client.list_account_aliases()
            return aliases['AccountAliases'][0] if aliases['AccountAliases'] else f"AWS Account {account_id}"
        
        loop = asyncio.get_event_loop()
        account_alias = await loop.run_in_executor(aws_client.executor, _get_account_alias)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assume IAM role: {str(e)}"
        )
    
    # Create cloud account record
    cloud_account = CloudAccount(
        organization_id=organization.id,
        provider="aws",
        account_id=account_id,
        account_alias=account_alias,
        role_arn=account_data.role_arn,
        external_id=account_data.external_id,
        regions=account_data.regions or ["us-east-1"],
        is_active=True,
        last_synced_at=datetime.utcnow()
    )
    
    db.add(cloud_account)
    await db.commit()
    await db.refresh(cloud_account)
    
    # Trigger initial resource collection
    # This would be done as a background task
    
    return CloudAccountResponse(
        id=str(cloud_account.id),
        account_id=cloud_account.account_id,
        account_alias=cloud_account.account_alias,
        provider=cloud_account.provider,
        status="connected",
        connected_at=cloud_account.created_at
    )

@router.get("/accounts/{account_id}/resources", response_model=ResourceListResponse)
async def get_aws_resources(
    account_id: str,
    region: Optional[str] = None,
    resource_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get resources from AWS account."""
    from sqlalchemy import select
    
    # Get cloud account
    result = await db.execute(
        select(CloudAccount).where(
            CloudAccount.id == account_id,
            CloudAccount.organization_id == organization.id
        )
    )
    cloud_account = result.scalar_one_or_none()
    
    if not cloud_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cloud account not found"
        )
    
    # Get resources
    aws_client = AWSClient()
    resource_types = [resource_type] if resource_type else None
    
    resources_data = await aws_client.list_resources(
        role_arn=cloud_account.role_arn,
        external_id=cloud_account.external_id,
        region=region or cloud_account.regions[0],
        resource_types=resource_types
    )
    
    return ResourceListResponse(
        account_id=cloud_account.account_id,
        region=region or "all",
        resources=resources_data.get("resources", []),
        count=resources_data.get("count", 0),
        collected_at=datetime.utcnow()
    )

@router.get("/accounts/{account_id}/costs")
async def get_aws_costs(
    account_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get cost data from AWS account."""
    from sqlalchemy import select
    
    # Get cloud account
    result = await db.execute(
        select(CloudAccount).where(
            CloudAccount.id == account_id,
            CloudAccount.organization_id == organization.id
        )
    )
    cloud_account = result.scalar_one_or_none()
    
    if not cloud_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cloud account not found"
        )
    
    # Calculate date range
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    # Get cost data
    aws_client = AWSClient()
    cost_data = await aws_client.get_cost_data(
        role_arn=cloud_account.role_arn,
        external_id=cloud_account.external_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat()
    )
    
    return {
        "account_id": cloud_account.account_id,
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "total_cost": cost_data["total_cost"],
        "daily_costs": cost_data["cost_data"],
        "currency": "USD"
    }