"""
Admin Admins API — Manage admin users (SUPER_ADMIN only)
"""
from datetime import datetime
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..database import get_db
from ..models import AdminUser, User as UserModel
from ..auth import require_admin
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


def _super_admin_check(admin_rec: Optional[AdminUser]):
    if not admin_rec or admin_rec.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="SUPER_ADMIN role required")
    return admin_rec


async def require_super_admin(current_user: UserModel = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> AdminUser:
    """Require SUPER_ADMIN role. Returns the AdminUser record."""
    result = await db.execute(select(AdminUser).where(AdminUser.telegram_id == current_user.telegram_id))
    admin_rec = result.scalar_one_or_none()
    return _super_admin_check(admin_rec)


@router.get("")
async def list_admins(
    page: int = 1,
    per_page: int = 50,
    db: AsyncSession = Depends(get_db),
    admin_rec: AdminUser = Depends(require_super_admin),
):
    """List all admin users (SUPER_ADMIN only)."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(AdminUser).order_by(AdminUser.created_at.desc()).offset(offset).limit(per_page)
    )
    admins = result.scalars().all()

    owner_id = admin_rec.id
    return [
        {**a.__dict__, "is_owner": a.id == owner_id} for a in admins
    ]


@router.post("", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    payload: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_rec: AdminUser = Depends(require_super_admin),
):
    """Add a new admin (SUPER_ADMIN only). Verify via bot first."""
    if payload.role not in ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {ROLES}")

    if payload.role == "SUPER_ADMIN":
        can_manage_bots, can_manage_accounts, can_manage_admins = True, True, True
    else:
        can_manage_bots = payload.can_manage_bots
        can_manage_accounts = payload.can_manage_accounts
        can_manage_admins = payload.can_manage_admins

    existing = await db.execute(select(AdminUser).where(AdminUser.telegram_id == payload.telegram_id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Admin with telegram_id {payload.telegram_id} already exists")

    username, first_name, last_name = None, None, None
    try:
        if tg_client:
            user = await tg_client.get_users(payload.telegram_id)
            username, first_name, last_name = user.username, user.first_name, user.last_name
    except Exception as e:
        logger.warning(f"Could not fetch user info for {payload.telegram_id}: {e}")

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
        created_by=admin_rec.id,
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
    admin_rec: AdminUser = Depends(require_super_admin),
):
    """Update admin user (SUPER_ADMIN only)."""
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(404, "Admin not found")

    if admin.id == admin_rec.id:
        if payload.role and payload.role != "SUPER_ADMIN":
            cnt = await db.execute(select(AdminUser).where(AdminUser.role == "SUPER_ADMIN", AdminUser.is_active == True))
            if len(cnt.scalars().all()) <= 1:
                raise HTTPException(400, "Cannot demote the only SUPER_ADMIN")
        if payload.can_manage_admins is False and admin.can_manage_admins:
            cnt = await db.execute(select(AdminUser).where(AdminUser.can_manage_admins == True, AdminUser.is_active == True))
            if len(cnt.scalars().all()) <= 1:
                raise HTTPException(400, "Cannot remove admin management from the only SUPER_ADMIN")

    if payload.role == "SUPER_ADMIN":
        payload.can_manage_bots = True
        payload.can_manage_accounts = True
        payload.can_manage_admins = True

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(admin, field, value)

    await db.commit()
    await db.refresh(admin)
    return admin


@router.delete("/{admin_id}")
async def delete_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    admin_rec: AdminUser = Depends(require_super_admin),
):
    """Delete an admin user (SUPER_ADMIN only)."""
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(404, "Admin not found")

    if admin.id == admin_rec.id:
        raise HTTPException(400, "Cannot delete yourself")
    if admin.role == "SUPER_ADMIN":
        raise HTTPException(400, "Cannot delete SUPER_ADMIN. Demote first.")

    await db.delete(admin)
    await db.commit()
    return {"ok": True, "message": f"Admin {admin.telegram_id} deleted"}


@router.post("/verify-telegram-id")
async def verify_telegram_id(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    admin_rec: AdminUser = Depends(require_super_admin),
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
        return {"valid": False, "error": str(e)}
