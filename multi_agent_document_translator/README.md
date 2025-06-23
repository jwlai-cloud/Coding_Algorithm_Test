# Multi-Agent Document Translation App

A sophisticated document translation system that preserves layout integrity using Google's Agent Development Kit (ADK) and A2A protocol.

## Overview

This application solves the common problem of layout destruction in document translation by using a multi-agent architecture where each agent performs specialized tasks while maintaining the original document's visual integrity.

## Architecture

### Agent 1: Document-to-Image Converter
- Converts PDF pages to high-quality images
- Maintains original resolution and formatting
- Handles various document formats

### Agent 2: Multimodal Translation Agent
- Uses Google Gemini Vision API for image-based translation
- Preserves layout, fonts, and visual elements
- Translates text while maintaining spatial relationships

### Agent 3: Quality Validation Agent
- Validates translation accuracy
- Checks layout preservation
- Provides quality metrics and feedback

## Features

- **Layout Preservation**: Maintains original document formatting
- **Multi-format Support**: PDF, DOCX, and other document formats
- **Quality Assurance**: Built-in validation and quality checks
- **Scalable Architecture**: Agent-based system for easy extension
- **Google AI Integration**: Leverages Gemini's multimodal capabilities

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from multi_agent_translator import MultiAgentTranslator

translator = MultiAgentTranslator()
result = translator.translate_document(
    document_path="input.pdf",
    target_language="Spanish",
    output_path="translated_output.pdf"
)
```

## Requirements

- Python 3.8+
- Google Cloud credentials
- Gemini API access
- Required Python packages (see requirements.txt)

