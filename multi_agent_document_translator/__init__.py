"""Multi-Agent Document Translation System."""

from .orchestrator import orchestrator, TranslationOrchestrator
from .config import settings
from .agents import (
    BaseAgent,
    DocumentConverterAgent,
    TranslationAgent,
    ValidationAgent
)

__version__ = "1.0.0"
__author__ = "Multi-Agent Translation Team"
__description__ = "AI-powered document translation with layout preservation using Google's ADK and A2A protocol"

__all__ = [
    'orchestrator',
    'TranslationOrchestrator',
    'settings',
    'BaseAgent',
    'DocumentConverterAgent', 
    'TranslationAgent',
    'ValidationAgent'
]

