"""Configuration settings for the Multi-Agent Document Translator."""

import os
from typing import Dict, Any
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Google Cloud Configuration
    google_cloud_project: str = Field(default="", env="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: str = Field(default="", env="GOOGLE_APPLICATION_CREDENTIALS")
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    
    # Agent Configuration
    max_concurrent_agents: int = Field(default=3, description="Maximum number of concurrent agents")
    agent_timeout: int = Field(default=300, description="Agent timeout in seconds")
    
    # Document Processing
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    supported_formats: list = Field(default=["pdf", "docx", "doc", "txt"])
    image_dpi: int = Field(default=300, description="DPI for PDF to image conversion")
    image_format: str = Field(default="PNG", description="Output image format")
    
    # Translation Settings
    default_source_language: str = Field(default="auto", description="Default source language")
    supported_languages: Dict[str, str] = Field(
        default={
            "en": "English",
            "es": "Spanish", 
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ar": "Arabic",
            "hi": "Hindi"
        }
    )
    
    # Quality Validation
    min_translation_confidence: float = Field(default=0.8, description="Minimum translation confidence score")
    layout_similarity_threshold: float = Field(default=0.85, description="Layout similarity threshold")
    
    # Paths
    temp_dir: str = Field(default="temp", description="Temporary files directory")
    output_dir: str = Field(default="output", description="Output files directory")
    logs_dir: str = Field(default="logs", description="Logs directory")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Get configuration for a specific agent."""
    base_config = {
        "timeout": settings.agent_timeout,
        "temp_dir": settings.temp_dir,
        "logs_dir": settings.logs_dir
    }
    
    agent_configs = {
        "document_converter": {
            **base_config,
            "image_dpi": settings.image_dpi,
            "image_format": settings.image_format,
            "max_file_size_mb": settings.max_file_size_mb
        },
        "translator": {
            **base_config,
            "gemini_api_key": settings.gemini_api_key,
            "supported_languages": settings.supported_languages,
            "default_source_language": settings.default_source_language
        },
        "validator": {
            **base_config,
            "min_confidence": settings.min_translation_confidence,
            "layout_threshold": settings.layout_similarity_threshold
        }
    }
    
    return agent_configs.get(agent_name, base_config)

