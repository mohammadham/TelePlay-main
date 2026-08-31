"""
Admin Admins API — Manage admin users (SUPER_ADMIN only)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
import logging

from ..database import get_db
from ..models import AdminUser
from ..auth import require_admin, get_current_user
from ..config import get_settings
from ..patch import Client
from ..telegram import tg_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/admins", tags=["Admin Admins"])

ROLES = ["SUPER_ADMIN", "ADMIN", "MODERATOR"]

class AdminCreateRequest(BaseModel):
    telegram_id: int
    role: str = "ADMIN"
    can_manage_bots: bool = False
    can_manage_accounts: bool = False
    can_manage_admins: bool = False
    is_active: bool = True

class AdminUpdateRequest(BaseModel):
    role: Optional[str] = None
    can_manage_bots: Optional[bool] = None
    can_manage_accounts: Optional[bool] = None
    can_manage_admins: Optional[bool] = None
    is_active: Optional[bool] = None

class AdminResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_active: bool
    can_manage_bots: bool
    can_manage_accounts: bool
    can_manage_admins: bool
    created_by: Optional[int] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

def require_super_admin(current_user: AdminUser = Depends(require_admin)):
    """Dependency to require SUPER_ADMIN role."""
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SUPER_ADMIN role required"
        )
    return current_user

@router.get("", response_model=List[AdminResponse])
async def list_admins(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    """List all admin users (SUPER_ADMIN only)."""
    result = await db.execute(select(AdminUser).order_by(AdminUser.created_at.desc()))
    admins = result.scalars().all()
    return admins

@router.post("", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    payload: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_super_admin),
):
    """Add a new admin (SUPER_ADMIN only). Verify via bot first."""
    if payload.role not in ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {ROLES}")
    
    # Only SUPER_ADMIN can create SUPER_ADMIN
    if payload.role == "SUPER_ADMIN" and current_user.role != "SUPER_ADMIN":
        raise HTTPException(403, "Only SUPER_ADMIN can create SUPER_ADMIN")
    
    # Check telegram_id uniqueness
    existing = await db.execute(select(AdminUser).where(AdminUser.telegram_id == payload.telegram_id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Admin with telegram_id {payload.telegram_id} already exists")
    
    # Verify the Telegram ID exists and get user info via bot
    username = None
    first_name = None
    last_name = None
    
    try:
        if tg_client:
            user = await tg_client.get_users(payload.telegram_id)
            username = user.username
            first_name = user.first_name
            last_name = user.last_name
    except Exception as e:
        logger.warning(f"Could not fetch user info for {payload.telegram_id}: {e}")
        # Continue anyway - user might not have started the bot yet
    
    # Set permissions based on role
    if payload.role == "SUPER_ADMIN":
        can_manage_bots = True
        can_manage_accounts = True
        can_manage_admins = True
    else:
        can_manage_bots = payload.can_manage_bots
        can_manage_accounts = payload.can_manage_accounts
        can_manage_admins = payload.can_manage_admins
    
    admin = AdminUser(
        telegram_id=payload.telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        role=payload.role,
        is_active=payload.is_active,
        can_manage_bots=can_manage_bots,
        can_manage_accounts=can_manage_accounts,
        can_manage_admins=can_manage_admins,
        created_by=current_user.id,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    
    return admin

@router.put("/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    payload: AdminUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_super_admin),
):
    """Update admin user (SUPER_ADMIN only)."""
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(404, "Admin not found")
    
    # Prevent self-modification of role to non-SUPER_ADMIN if you're the only SUPER_ADMIN
    if admin.id == current_user.id:
        if payload.role and payload.role != "SUPER_ADMIN":
            super_count = await db.execute(
                select(AdminUser).where(AdminUser.role == "SUPER_ADMIN", AdminUser.is_active == True)
            )
            if len(super_count.scalars().all()) <= 1:
                raise HTTPException(400, "Cannot demote the only SUPER_ADMIN")
        if payload.can_manage_admins is False and admin.can_manage_admins:
            super_count = await db.execute(
                select(AdminUser).where(AdminUser.can_manage_admins == True, AdminUser.is_active == True)
            )
            if len(super_count.scalars().all()) <= 1:
                raise HTTPException(400, "Cannot remove admin management from the only SUPER_ADMIN")
    
    # Only SUPER_ADMIN can create/modify SUPER_ADMIN
    if payload.role == "SUPER_ADMIN" and current_user.role != "SUPER_ADMIN":
        raise HTTPException(403, "Only SUPER_ADMIN can assign SUPER_ADMIN role")
    
    if payload.role and payload.role not in ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {ROLES}")
    
    update_data = payload.model_dump(exclude_unset=True)
    
    # Auto-set permissions for SUPER_ADMIN
    if "role" in update_data and update_data["role"] == "SUPER_ADMIN":
        update_data["can_manage_bots"] = True
        update_data["can_manage_accounts"] = True
        update_data["can_manage_admins"] = True
    
    for field, value in update_data.items():
        setattr(admin, field, value)
    
    await db.commit()
    await db.refresh(admin)
    
    return admin

@router.delete("/{admin_id}")
async def delete_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_super_admin),
):
    """Delete an admin user (SUPER_ADMIN only)."""
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(404, "Admin not found")
    
    # Cannot delete self
    if admin.id == current_user.id:
        raise HTTPException(400, "Cannot delete yourself")
    
    # Cannot delete other SUPER_ADMIN
    if admin.role == "SUPER_ADMIN":
        raise HTTPException(400, "Cannot delete SUPER_ADMIN. Demote first.")
    
    await db.delete(admin)
    await db.commit()
    
    return {"ok": True, "message": f"Admin {admin.telegram_id} deleted"}

@router.post("/verify-telegram-id")
async def verify_telegram_id(
    telegram_id: int,
    current_user: AdminUser = Depends(require_super_admin),
):
    """Verify a Telegram ID exists and get user info (for admin creation)."""
    try:
        if not tg_client:
            raise HTTPException(503, "Bot client not available")
        
        user = await tg_client.get_users(telegram_id)
        return {
            "valid": True,
            "telegram_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    except Exception as e:
        logger.warning(f"Telegram ID verification failed for {telegram_id}: {e}")
        return {
            "valid": False,
            "error": str(e),
        }

# Imports
from pydantic import BaseModel, ConfigDict
from datetime import datetime