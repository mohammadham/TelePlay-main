"""
Add MY_MUSIC_ENABLED to admin settings template.
Run: python -c "from app.config import mark_db_ready; from app.main import app; print('ok')"
"""
import sys
sys.path.insert(0, "D:/filmchi_tel/TelePlay-main/backend")

from sqlalchemy import select
from app.database import async_session
from app.models import AppSetting

async def add_my_music_setting():
    async with async_session() as db:
        row = (await db.execute(select(AppSetting).where(AppSetting.key == "MY_MUSIC_ENABLED"))).scalar_one_or_none()
        if not row:
            db.add(AppSetting(key="MY_MUSIC_ENABLED", value="true", description="Enable My Music section for users"))
            await db.commit()
            print("Added MY_MUSIC_ENABLED=true")
        else:
            print(f"MY_MUSIC_ENABLED already exists: {row.value}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(add_my_music_setting())
