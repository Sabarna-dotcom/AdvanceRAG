# config/ingestion_config.py
"""
Configuration specific to the ingestion/chunking module.
"""

from pydantic import BaseModel
from src.config.settings import get_settings


class PDFChunkingConfig(BaseModel):
    """Configuration for PDF chunking"""
    chunk_size: int
    chunk_overlap: int
    enable_parent_child: bool
    parent_size: int
    child_size: int

    class Config:
        frozen = True


class VideoChunkingConfig(BaseModel):
    """Configuration for video transcript chunking"""
    chunk_duration: int  # seconds
    min_chunk_length: int  # characters
    enable_parent_child: bool

    class Config:
        frozen = True


class IngestionConfig(BaseModel):
    """Combined ingestion configuration"""
    pdf: PDFChunkingConfig
    video: VideoChunkingConfig

    class Config:
        frozen = True


def get_ingestion_config() -> IngestionConfig:
    """Create ingestion config from main settings"""
    settings = get_settings()

    pdf_config = PDFChunkingConfig(
        chunk_size=settings.pdf_chunk_size,
        chunk_overlap=settings.pdf_chunk_overlap,
        enable_parent_child=settings.pdf_enable_parent_child,
        parent_size=settings.pdf_parent_size,
        child_size=settings.pdf_child_size
    )

    video_config = VideoChunkingConfig(
        chunk_duration=settings.video_chunk_duration,
        min_chunk_length=settings.video_min_chunk_length,
        enable_parent_child=settings.video_enable_parent_child
    )

    return IngestionConfig(
        pdf=pdf_config,
        video=video_config
    )


# Singleton
_ingestion_config = None


def get_config() -> IngestionConfig:
    """Get or create ingestion config singleton"""
    global _ingestion_config
    if _ingestion_config is None:
        _ingestion_config = get_ingestion_config()
    return _ingestion_config