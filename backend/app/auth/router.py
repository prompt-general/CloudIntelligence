from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional
import jwt
from app.database import get_db
from app.models.user import User
from app.models.organization import Organization, UserOrganization
from app.schemas.auth import Token, UserCreate, UserResponse, OrganizationCreate
from app.utils.security import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    get_current_user,
    get_current_active_user
)
from app.config import settings

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    organization_data: Optional[OrganizationCreate] = None,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user and create their first organization."""
    # Check if user exists
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization if provided
    organization = None
    if organization_data:
        organization = Organization(
            name=organization_data.name,
            slug=organization_data.name.lower().replace(" ", "-"),
            description=organization_data.description
        )
        db.add(organization)
        await db.flush()  # Get ID without committing
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True
    )
    db.add(user)
    await db.flush()
    
    # Link user to organization as owner
    if organization:
        user_org = UserOrganization(
            user_id=user.id,
            organization_id=organization.id,
            role="owner"
        )
        db.add(user_org)
    
    await db.commit()
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at
    )

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """OAuth2 compatible token login."""
    from sqlalchemy import select
    
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Get user's organizations
    org_result = await db.execute(
        select(Organization).join(UserOrganization).where(UserOrganization.user_id == user.id)
    )
    organizations = org_result.scalars().all()
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "organizations": [str(org.id) for org in organizations]
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "organizations": [{"id": str(org.id), "name": org.name} for org in organizations]
        }
    }

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user

@router.post("/organizations", response_model=dict)
async def create_organization(
    organization_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new organization for current user."""
    # Check if organization name exists
    from sqlalchemy import select
    result = await db.execute(
        select(Organization).where(Organization.name == organization_data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already exists"
        )
    
    organization = Organization(
        name=organization_data.name,
        slug=organization_data.name.lower().replace(" ", "-"),
        description=organization_data.description
    )
    db.add(organization)
    await db.flush()
    
    # Add user as owner
    user_org = UserOrganization(
        user_id=current_user.id,
        organization_id=organization.id,
        role="owner"
    )
    db.add(user_org)
    
    await db.commit()
    
    return {
        "id": str(organization.id),
        "name": organization.name,
        "slug": organization.slug,
        "message": "Organization created successfully"
    }