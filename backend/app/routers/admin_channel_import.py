"""
Admin Channel Import Router - Import files from storage channel history.
Admin-only endpoints for managing channel import jobs.
"""
import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, WebSocket, WebSocketDisconnect
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

# WebSocket connection manager for real-time progress updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, job_id: int):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, job_id: int):
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
    
    async def broadcast(self, job_id: int, message: dict):
        if job_id in self.active_connections:
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()


class StartImportRequest(BaseModel):
    file_types: List[str] = Field(default=["video", "audio", "document", "image"])
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    target_folder_id: Optional[int] = None
    user_account_id: Optional[int] = None
    # Advanced filters
    min_file_size: Optional[int] = Field(default=None, ge=0, description="Minimum file size in bytes")
    max_file_size: Optional[int] = Field(default=None, ge=0, description="Maximum file size in bytes")
    filename_regex: Optional[str] = Field(default=None, description="Regex pattern to match filename")
    caption_regex: Optional[str] = Field(default=None, description="Regex pattern to match caption")


class ImportJobResponse(BaseModel):
    id: int
    admin_id: int
    admin_username: Optional[str] = None
    admin_first_name: Optional[str] = None
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
    # Advanced filters
    min_file_size: Optional[int] = Field(default=None, ge=0, description="Minimum file size in bytes")
    max_file_size: Optional[int] = Field(default=None, ge=0, description="Maximum file size in bytes")
    filename_regex: Optional[str] = Field(default=None, description="Regex pattern to match filename")
    caption_regex: Optional[str] = Field(default=None, description="Regex pattern to match caption")


def _job_to_response(job: ChannelImportJob, admin: Optional[AdminUser] = None) -> ImportJobResponse:
    """Convert ChannelImportJob to ImportJobResponse with admin info."""
    return ImportJobResponse(
        id=job.id,
        admin_id=job.admin_id,
        admin_username=admin.username if admin else None,
        admin_first_name=admin.first_name if admin else None,
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


@router.post("/start", response_model=ImportJobResponse)
async def start_import(
    payload: StartImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
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
    
    # Check for concurrent jobs on the same account
    if payload.user_account_id:
        existing_job = await db.execute(
            select(ChannelImportJob).where(
                ChannelImportJob.user_account_id == payload.user_account_id,
                ChannelImportJob.status.in_(["pending", "running"])
            )
        )
        if existing_job.scalar_one_or_none():
            raise HTTPException(
                status_code=400, 
                detail="This account is already running an import job. Wait for it to complete or cancel it first."
            )
    
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
        min_file_size=payload.min_file_size,
        max_file_size=payload.max_file_size,
        filename_regex=payload.filename_regex,
        caption_regex=payload.caption_regex,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Start background task
    background_tasks.add_task(run_import_job, job.id)
    
    return _job_to_response(job, admin)


@router.get("/jobs", response_model=dict)
async def list_import_jobs(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """List channel import jobs with pagination."""
    # Join with AdminUser to get admin info
    from sqlalchemy.orm import joinedload
    query = select(ChannelImportJob).options(joinedload(ChannelImportJob.admin)).order_by(ChannelImportJob.created_at.desc())
    if status:
        query = query.where(ChannelImportJob.status == status)
    
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(query)).scalars().all()
    
    return {
        "jobs": [
            _job_to_response(j, j.admin) for j in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
async def get_import_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Get status of a specific import job (for polling)."""
    from sqlalchemy.orm import joinedload
    job = (await db.execute(
        select(ChannelImportJob)
        .options(joinedload(ChannelImportJob.admin))
        .where(ChannelImportJob.id == job_id)
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return _job_to_response(job, job.admin)


@router.post("/jobs/{job_id}/cancel")
async def cancel_import_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
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
    db.add(AuditLog(user_id=None, action="cancel_channel_import", target=f"admin:{admin.id}:job:{job_id}", ip_address=ip))
    
    await db.execute(update(ChannelImportJob).where(ChannelImportJob.id == job_id).values(status="cancelled", finished_at=datetime.utcnow()))
    await db.commit()
    
    return {"ok": True, "message": "Job cancelled"}


@router.post("/preview", response_model=dict)
async def preview_import_endpoint(
    payload: PreviewRequest,
    admin: AdminUser = Depends(require_admin),
):
    """Preview import - estimate counts without importing."""
    if settings.telegram_storage_channel_id <= 0:
        raise HTTPException(status_code=400, detail="Storage channel not configured")
    
    result = await preview_import(
        user_account_id=payload.user_account_id,
        file_types=payload.file_types,
        date_from=payload.date_from,
        date_to=payload.date_to,
        min_file_size=payload.min_file_size,
        max_file_size=payload.max_file_size,
        filename_regex=payload.filename_regex,
        caption_regex=payload.caption_regex,
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/accounts", response_model=List[dict])
async def get_available_accounts(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
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
    admin: AdminUser = Depends(require_admin),
):
    """Get available folders (admin's folders) for import target."""
    user = (await db.execute(select(User).where(User.telegram_id == admin.telegram_id))).scalar_one_or_none()
    if not user:
        return []
    
    folders = (await db.execute(select(Folder).where(Folder.user_id == user.id).order_by(Folder.name))).scalars().all()
    return [
        {"id": f.id, "name": f.name, "parent_id": f.parent_id}
        for f in folders
    ]


@router.websocket("/jobs/{job_id}/ws")
async def job_progress_websocket(websocket: WebSocket, job_id: int):
    """WebSocket endpoint for real-time job progress updates."""
    # Verify job exists
    from ..database import async_session
    from ..models import ChannelImportJob
    from ..auth import get_current_user_ws
    
    async with async_session() as db:
        job = await db.execute(select(ChannelImportJob).where(ChannelImportJob.id == job_id))
        job = job.scalar_one_or_none()
        if not job:
            await websocket.close(code=4004, reason="Job not found")
            return
    
    await manager.connect(websocket, job_id)
    try:
        # Send initial status
        async with async_session() as db:
            job = await db.execute(select(ChannelImportJob).where(ChannelImportJob.id == job_id))
            job = job.scalar_one_or_none()
            if job:
                await websocket.send_json({
                    "type": "status",
                    "job_id": job.id,
                    "status": job.status,
                    "total_scanned": job.total_scanned,
                    "total_imported": job.total_imported,
                    "total_skipped": job.total_skipped,
                    "total_errors": job.total_errors,
                    "last_message_id": job.last_message_id,
                })
        
        # Keep connection alive and listen for close
        while True:
            try:
                data = await websocket.receive_text()
                # Handle ping/pong or client messages if needed
            except WebSocketDisconnect:
                break
    except Exception:
        pass
    finally:
        manager.disconnect(websocket, job_id)