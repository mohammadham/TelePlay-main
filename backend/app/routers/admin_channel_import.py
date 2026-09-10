"""
Admin Channel Import Router - Import files from storage channel history.
Admin-only endpoints for managing channel import jobs.
"""
import asyncio
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ChannelImportJob, UserAccount, Folder, AdminUser, User
from ..auth import require_admin
from ..services import run_import_job, preview_import
from ..config import get_settings

router = APIRouter(prefix="/admin/channel-import", tags=["Admin Channel Import"])
settings = get_settings()


class StartImportRequest(BaseModel):
    file_types: List[str] = Field(default=["video", "audio", "document", "image"])
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    target_folder_id: Optional[int] = None
    user_account_id: Optional[int] = None


class ImportJobResponse(BaseModel):
    id: int
    admin_id: int
    status: str
    file_types: List[str]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    target_folder_id: Optional[int]
    user_account_id: Optional[int]
    total_scanned: int
    total_imported: int
    total_skipped: int
    total_errors: int
    last_message_id: Optional[int]
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class PreviewRequest(BaseModel):
    file_types: List[str] = Field(default=["video", "audio", "document", "image"])
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    user_account_id: Optional[int] = None


@router.post("/start", response_model=ImportJobResponse)
async def start_import(
    payload: StartImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    request: Request = None,
):
    """Start a new channel import job."""
    # Verify storage channel is configured
    if settings.telegram_storage_channel_id <= 0:
        raise HTTPException(status_code=400, detail="Storage channel not configured")
    
    # Verify at least one user account exists
    account_count = (await db.execute(select(func.count()).select_from(UserAccount))).scalar() or 0
    if account_count == 0:
        raise HTTPException(status_code=400, detail="No MTProto user accounts configured. Add one in Accounts panel first.")
    
    # Verify user_account_id if provided
    if payload.user_account_id:
        account = (await db.execute(select(UserAccount).where(UserAccount.id == payload.user_account_id))).scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="User account not found")
        if not account.is_active:
            raise HTTPException(status_code=400, detail="Selected user account is not active")
    
    # Verify target_folder_id if provided
    if payload.target_folder_id:
        folder = (await db.execute(select(Folder).where(Folder.id == payload.target_folder_id))).scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=404, detail="Target folder not found")
    
    # Create job
    job = ChannelImportJob(
        admin_id=admin.id,
        status="pending",
        file_types=json.dumps(payload.file_types),
        date_from=payload.date_from,
        date_to=payload.date_to,
        target_folder_id=payload.target_folder_id,
        user_account_id=payload.user_account_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Start background task
    background_tasks.add_task(run_import_job, job.id)
    
    return ImportJobResponse(
        id=job.id,
        admin_id=job.admin_id,
        status=job.status,
        file_types=json.loads(job.file_types),
        date_from=job.date_from,
        date_to=job.date_to,
        target_folder_id=job.target_folder_id,
        user_account_id=job.user_account_id,
        total_scanned=job.total_scanned,
        total_imported=job.total_imported,
        total_skipped=job.total_skipped,
        total_errors=job.total_errors,
        last_message_id=job.last_message_id,
        error_message=job.error_message,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


@router.get("/jobs", response_model=dict)
async def list_import_jobs(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List channel import jobs with pagination."""
    query = select(ChannelImportJob).order_by(ChannelImportJob.created_at.desc())
    if status:
        query = query.where(ChannelImportJob.status == status)
    
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(query)).scalars().all()
    
    return {
        "jobs": [
            ImportJobResponse(
                id=j.id,
                admin_id=j.admin_id,
                status=j.status,
                file_types=json.loads(j.file_types),
                date_from=j.date_from,
                date_to=j.date_to,
                target_folder_id=j.target_folder_id,
                user_account_id=j.user_account_id,
                total_scanned=j.total_scanned,
                total_imported=j.total_imported,
                total_skipped=j.total_skipped,
                total_errors=j.total_errors,
                last_message_id=j.last_message_id,
                error_message=j.error_message,
                started_at=j.started_at,
                finished_at=j.finished_at,
                created_at=j.created_at,
            ) for j in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
async def get_import_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get status of a specific import job (for polling)."""
    job = (await db.execute(select(ChannelImportJob).where(ChannelImportJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return ImportJobResponse(
        id=job.id,
        admin_id=job.admin_id,
        status=job.status,
        file_types=json.loads(job.file_types),
        date_from=job.date_from,
        date_to=job.date_to,
        target_folder_id=job.target_folder_id,
        user_account_id=job.user_account_id,
        total_scanned=job.total_scanned,
        total_imported=job.total_imported,
        total_skipped=job.total_skipped,
        total_errors=job.total_errors,
        last_message_id=job.last_message_id,
        error_message=job.error_message,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


@router.post("/jobs/{job_id}/cancel")
async def cancel_import_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    request: Request = None,
):
    """Cancel a running import job."""
    from sqlalchemy import update
    from ..models import AuditLog
    
    job = (await db.execute(select(ChannelImportJob).where(ChannelImportJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job.status}")
    
    ip = request.client.host if request and request.client else None
    db.add(AuditLog(user_id=admin.id, action="cancel_channel_import", target=str(job_id), ip_address=ip))
    
    await db.execute(update(ChannelImportJob).where(ChannelImportJob.id == job_id).values(status="cancelled", finished_at=datetime.utcnow()))
    await db.commit()
    
    return {"ok": True, "message": "Job cancelled"}


@router.post("/preview", response_model=dict)
async def preview_import_endpoint(
    payload: PreviewRequest,
    admin: User = Depends(require_admin),
):
    """Preview import - estimate counts without importing."""
    if settings.telegram_storage_channel_id <= 0:
        raise HTTPException(status_code=400, detail="Storage channel not configured")
    
    result = await preview_import(
        user_account_id=payload.user_account_id,
        file_types=payload.file_types,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/accounts", response_model=List[dict])
async def get_available_accounts(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get available MTProto user accounts for import."""
    accounts = (await db.execute(select(UserAccount).where(UserAccount.is_active == True))).scalars().all()
    return [
        {
            "id": acc.id,
            "name": acc.name,
            "username": acc.username,
            "purpose": acc.purpose,
            "flood_wait_until": acc.flood_wait_until,
            "last_used": acc.last_used,
        }
        for acc in accounts
    ]


@router.get("/folders", response_model=List[dict])
async def get_available_folders(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get available folders (admin's folders) for import target."""
    admin_user = (await db.execute(select(AdminUser).where(AdminUser.id == admin.id))).scalar_one_or_none()
    if not admin_user:
        return []
    
    user = (await db.execute(select(User).where(User.telegram_id == admin_user.telegram_id))).scalar_one_or_none()
    if not user:
        return []
    
    folders = (await db.execute(select(Folder).where(Folder.user_id == user.id).order_by(Folder.name))).scalars().all()
    return [
        {"id": f.id, "name": f.name, "parent_id": f.parent_id}
        for f in folders
    ]