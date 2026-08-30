"""
Video domain stub — branch feature/video-platform
Import Base from database; merge into models.py when ready.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Movie(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    genre: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False, unique=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500))
    duration: Mapped[Optional[int]] = mapped_column(Integer)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("idx_movie_genre", "genre"), Index("idx_movie_featured", "featured"))

class Series(Base):
    __tablename__ = "series"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    genre: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Episode(Base):
    __tablename__ = "episodes"
    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, default=1)
    episode: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False, unique=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer)
