"""
Multi-Agent Document Translation App

A sophisticated document translation system that preserves layout and visual integrity 
using Google's Agent Development Kit (ADK) and A2A protocol.

This package provides a multi-agent system for translating documents while maintaining
their original layout, visual elements, and formatting. It uses specialized agents for
document conversion, image translation, and quality validation.

Main Components:
- OrchestratorAgent: Manages the overall workflow
- ConversionAgent: Converts documents to page images  
- ImageTranslationAgent: Performs OCR, translation, and text re-rendering
- ValidationAgent: Assesses translation quality and layout preservation

Usage:
    from multi_agent_translation_app import DocumentTranslationApp
    
    app = DocumentTranslationApp()
    await app.start_server()

Author: AI Assistant
Version: 1.0.0
"""

from .main import DocumentTranslationApp
from .agents import (
    OrchestratorAgent,
    ConversionAgent, 
    ImageTranslationAgent,
    ValidationAgent
)
from .config import settings

__version__ = "1.0.0"
__author__ = "AI Assistant"

__all__ = [
    "DocumentTranslationApp",
    "OrchestratorAgent",
    "ConversionAgent",
    "ImageTranslationAgent", 
    "ValidationAgent",
    "settings"
]

