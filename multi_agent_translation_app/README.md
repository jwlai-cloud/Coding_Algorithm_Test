# Multi-Agent Document Translation App

A sophisticated document translation system that preserves layout and visual integrity using Google's Agent Development Kit (ADK) and A2A protocol.

## Overview

Standard document translation tools often fail with visually complex documents (technical manuals, marketing brochures, academic papers with diagrams). They extract text, translate it, and try to reflow it into the document, which breaks the original layout, misplaces captions, and destroys visual integrity.

This app solves this problem using a multi-agent system where each agent performs a specialized task, preserving the document's original layout with high fidelity.

## Architecture

### Agent System Design

The application consists of four main agents:

#### 1. Orchestrator Agent
- **Purpose**: Manages overall workflow and coordinates other agents
- **Responsibilities**:
  - Receives document translation requests
  - Auto-detects source language
  - Coordinates with other agents
  - Assembles final translated document
  - Handles errors and retries

#### 2. Conversion Agent
- **Purpose**: Converts documents to high-resolution page images
- **Responsibilities**:
  - Supports PDF, PPTX, DOCX formats
  - Converts each page to high-resolution PNG/JPEG
  - Uploads images to Google Cloud Storage
  - Returns list of image URIs

#### 3. Image Translation Agent
- **Purpose**: Performs OCR, translation, and text re-rendering
- **Responsibilities**:
  - Extracts text and bounding boxes using Google Cloud Vision API
  - Groups text into logical blocks
  - Creates clean image by masking original text
  - Translates text using Google Cloud Translation API
  - Re-renders translated text preserving layout and style

#### 4. Validation Agent
- **Purpose**: Assesses translation quality and layout preservation
- **Responsibilities**:
  - Performs semantic validation through back-translation
  - Checks layout consistency using image comparison
  - Verifies completeness of text translation
  - Generates quality scores and issue reports

## Features

- **Layout Preservation**: Maintains original document layout and visual elements
- **Multi-Format Support**: PDF, PPTX, DOCX document formats
- **High-Quality OCR**: Uses Google Cloud Vision API for accurate text extraction
- **Semantic Validation**: Back-translation for quality assurance
- **Visual Consistency**: SSIM-based layout comparison
- **Scalable Architecture**: Multi-agent system with async processing
- **RESTful API**: Easy integration with web applications
- **Quality Metrics**: Comprehensive validation and scoring

## Installation

### Prerequisites

- Python 3.8+
- Google Cloud Project with enabled APIs:
  - Cloud Vision API
  - Cloud Translation API
  - Cloud Storage API
- Service Account with appropriate permissions

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd multi_agent_translation_app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Google Cloud settings
   ```

4. **Set up Google Cloud credentials**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

5. **Create GCS bucket**:
   ```bash
   gsutil mb gs://your-document-translation-bucket
   ```

## Usage

### Starting the Application

```bash
python main.py
```

The application will start on `http://localhost:8000`

### API Endpoints

#### Upload Document
```bash
POST /upload
Content-Type: multipart/form-data

# Upload a document file
curl -X POST "http://localhost:8000/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"
```

#### Translate Document
```bash
POST /translate
Content-Type: application/json

{
  "document_path": "gs://bucket/document.pdf",
  "target_language": "es",
  "source_language": "auto"
}
```

#### Check Job Status
```bash
GET /job/{job_id}
```

#### List All Jobs
```bash
GET /jobs
```

#### Get Supported Languages
```bash
GET /languages
```

### Example Usage

```python
import requests

# Upload document
with open('document.pdf', 'rb') as f:
    upload_response = requests.post(
        'http://localhost:8000/upload',
        files={'file': f}
    )

document_path = upload_response.json()['document_path']

# Start translation
translation_response = requests.post(
    'http://localhost:8000/translate',
    json={
        'document_path': document_path,
        'target_language': 'es',
        'source_language': 'auto'
    }
)

job_id = translation_response.json()['job_id']

# Check status
status_response = requests.get(f'http://localhost:8000/job/{job_id}')
print(status_response.json())
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | Google Cloud Project ID | Required |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key | Required |
| `GCS_BUCKET_NAME` | Cloud Storage bucket name | `document-translation-bucket` |
| `IMAGE_DPI` | Image resolution for conversion | `300` |
| `MAX_RETRIES` | Maximum retry attempts | `3` |
| `MIN_QUALITY_SCORE` | Minimum acceptable quality score | `0.7` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Supported Languages

The application supports translation between the following languages:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Japanese (ja)
- Korean (ko)
- Chinese (zh)
- Arabic (ar)

## Quality Metrics

The validation agent provides several quality metrics:

- **Layout Consistency Score**: Measures preservation of visual layout
- **Structural Similarity Score**: SSIM-based comparison of document structure
- **Semantic Consistency Score**: Back-translation accuracy
- **Text Completeness Score**: Ensures all text blocks are translated
- **Overall Quality Score**: Weighted average of all metrics

## Testing

Run the test suite:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=agents --cov-report=html
```

## Development

### Project Structure

```
multi_agent_translation_app/
├── agents/                 # Agent implementations
│   ├── base_agent.py      # Base agent class
│   ├── orchestrator_agent.py
│   ├── conversion_agent.py
│   ├── image_translation_agent.py
│   └── validation_agent.py
├── config/                # Configuration
│   └── settings.py
├── utils/                 # Utility functions
│   └── gcs_helper.py
├── tests/                 # Test suite
├── main.py               # Main application
├── requirements.txt      # Dependencies
└── README.md            # This file
```

### Adding New Agents

1. Inherit from `BaseAgent`
2. Implement required methods:
   - `validate_input()`
   - `process()`
3. Add agent to orchestrator workflow
4. Write tests

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## Limitations

- Currently supports PDF, PPTX, and DOCX formats
- PPTX and DOCX conversion use placeholder implementations
- Font matching is basic and may need enhancement
- Complex layouts with overlapping elements may have issues

## Future Enhancements

- Support for more document formats
- Advanced font matching and styling
- Integration with Vision Language Models for better validation
- Real-time processing status updates
- Batch processing capabilities
- Custom translation models

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information

## Acknowledgments

- Google Cloud Platform for AI/ML services
- pdf2image library for PDF conversion
- OpenCV and scikit-image for image processing
- FastAPI for the web framework

