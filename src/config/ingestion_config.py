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


class PathConfig(BaseModel):

    raw_pdf_dir: str
    raw_audio_dir: str
    raw_video_dir: str
    processed_pdf_dir: str
    processed_transcript_dir: str

    class Config:
        frozen = True

class IngestionConfig(BaseModel):
    """Combined ingestion configuration"""
    pdf: PDFChunkingConfig
    paths: PathConfig

    class Config:
        frozen = True


def get_ingestion_config() -> IngestionConfig:
    """Create ingestion config from main settings"""
    settings = get_settings()

    pdf_config = PDFChunkingConfig(
        chunk_size=settings.pdf_chunk_size,
        chunk_overlap=settings.pdf_chunk_overlap,
        parent_size=settings.pdf_parent_size,
        child_size=settings.pdf_child_size,
    )


    path_config = PathConfig(
        raw_pdf_dir=settings.raw_pdf_dir,
        raw_audio_dir=settings.raw_audio_dir,
        raw_video_dir=settings.raw_video_dir,
        processed_pdf_dir=settings.processed_pdf_dir,
        processed_transcript_dir=settings.processed_transcript_dir
    )

    return IngestionConfig(
        pdf=pdf_config,
        paths=path_config
    )


# Singleton
_ingestion_config = None


def get_config() -> IngestionConfig:
    """Get or create ingestion config singleton"""
    global _ingestion_config
    if _ingestion_config is None:
        _ingestion_config = get_ingestion_config()
    return _ingestion_config