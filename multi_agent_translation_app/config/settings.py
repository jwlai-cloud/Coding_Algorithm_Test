"""Configuration settings for the Multi-Agent Document Translation App."""

import os
from typing import Dict, Any
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Google Cloud Configuration
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    # Cloud Storage
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "document-translation-bucket")
    GCS_INPUT_FOLDER: str = "input_documents"
    GCS_PAGES_FOLDER: str = "page_images"
    GCS_TRANSLATED_FOLDER: str = "translated_images"
    GCS_OUTPUT_FOLDER: str = "output_documents"
    
    # Image Processing
    IMAGE_DPI: int = 300
    IMAGE_FORMAT: str = "PNG"
    MAX_IMAGE_SIZE: tuple = (3000, 3000)
    
    # Translation
    DEFAULT_SOURCE_LANGUAGE: str = "auto"
    SUPPORTED_LANGUAGES: list = [
        "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", "ar"
    ]
    
    # Agent Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    TIMEOUT_SECONDS: int = 300
    
    # Quality Validation
    MIN_QUALITY_SCORE: float = 0.7
    SSIM_THRESHOLD: float = 0.8
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_agent_config() -> Dict[str, Any]:
    """Get configuration for ADK agents."""
    return {
        "project_id": settings.GOOGLE_CLOUD_PROJECT,
        "location": "us-central1",
        "max_retries": settings.MAX_RETRIES,
        "timeout": settings.TIMEOUT_SECONDS,
    }


def get_gcs_config() -> Dict[str, str]:
    """Get Google Cloud Storage configuration."""
    return {
        "bucket_name": settings.GCS_BUCKET_NAME,
        "input_folder": settings.GCS_INPUT_FOLDER,
        "pages_folder": settings.GCS_PAGES_FOLDER,
        "translated_folder": settings.GCS_TRANSLATED_FOLDER,
        "output_folder": settings.GCS_OUTPUT_FOLDER,
    }

