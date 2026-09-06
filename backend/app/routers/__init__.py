"""
Router package initialization.
"""
from .files import router as files_router
from .folders import router as folders_router
from .streaming import router as streaming_router
from .auth import router as auth_router
from .tv import router as tv_router
from .music import router as music_router
from .admin import router as admin_router
from .ads import router as ads_router
from .video import router as video_router

__all__ = ["files_router", "folders_router", "streaming_router", "auth_router", "tv_router", "music_router", "admin_router", "ads_router", "video_router"]

