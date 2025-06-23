"""FastAPI web interface for the Multi-Agent Document Translator."""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import os

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .orchestrator import orchestrator
from .config import settings


# Pydantic models for API
class TranslationRequest(BaseModel):
    target_language: str
    source_language: str = "auto"
    output_format: str = "pdf"


class TranslationResponse(BaseModel):
    success: bool
    translation_id: Optional[str] = None
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SystemStatus(BaseModel):
    status: str
    session_id: str
    agents_running: Dict[str, bool]
    supported_languages: Dict[str, str]
    max_file_size_mb: int


# Initialize FastAPI app
app = FastAPI(
    title="Multi-Agent Document Translator",
    description="AI-powered document translation with layout preservation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for managing uploads and results
active_translations = {}
temp_files = {}


@app.on_event("startup")
async def startup_event():
    """Initialize the multi-agent system on startup."""
    try:
        await orchestrator.initialize()
        print("🚀 Multi-Agent Document Translator API started successfully")
    except Exception as e:
        print(f"❌ Failed to start API: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await orchestrator.shutdown()
    
    # Clean up temporary files
    for temp_file in temp_files.values():
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except:
            pass


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Multi-Agent Document Translator API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/status", response_model=SystemStatus)
async def get_status():
    """Get system status."""
    status_data = await orchestrator.get_system_status()
    
    return SystemStatus(
        status="running" if status_data["initialized"] else "initializing",
        session_id=status_data["session_id"],
        agents_running=status_data["agents"],
        supported_languages=status_data["supported_languages"],
        max_file_size_mb=status_data["max_file_size_mb"]
    )


@app.get("/languages")
async def get_supported_languages():
    """Get supported languages."""
    languages = await orchestrator.get_supported_languages()
    return {"supported_languages": languages}


@app.post("/translate", response_model=TranslationResponse)
async def translate_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_language: str = Form(...),
    source_language: str = Form("auto"),
    output_format: str = Form("pdf")
):
    """
    Translate a document using the multi-agent system.
    
    - **file**: Document file to translate (PDF, DOCX, TXT)
    - **target_language**: Target language code (e.g., 'es', 'fr', 'de')
    - **source_language**: Source language code (default: 'auto')
    - **output_format**: Output format (default: 'pdf')
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ['.pdf', '.docx', '.doc', '.txt']:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format: {file_extension}"
            )
        
        # Check file size
        file_size = 0
        content = await file.read()
        file_size = len(content) / (1024 * 1024)  # MB
        
        if file_size > settings.max_file_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size:.1f}MB) exceeds maximum ({settings.max_file_size_mb}MB)"
            )
        
        # Validate target language
        supported_languages = await orchestrator.get_supported_languages()
        if target_language not in supported_languages:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported target language: {target_language}"
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Create output path
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        output_filename = f"translated_{Path(file.filename).stem}_{target_language}.{output_format}"
        output_path = output_dir / output_filename
        
        # Start translation process
        result = await orchestrator.translate_document(
            document_path=temp_file_path,
            target_language=target_language,
            source_language=source_language,
            output_path=str(output_path)
        )
        
        # Clean up temp file
        background_tasks.add_task(cleanup_temp_file, temp_file_path)
        
        if result['success']:
            # Store result for download
            translation_id = result['translation_id']
            active_translations[translation_id] = result
            
            return TranslationResponse(
                success=True,
                translation_id=translation_id,
                message=f"Translation completed successfully in {result['processing_time']:.1f}s",
                data={
                    "page_count": result['page_count'],
                    "quality_grade": result['validation']['quality_assessment']['grade'],
                    "output_files": result['output_files'],
                    "download_url": f"/download/{translation_id}"
                }
            )
        else:
            return TranslationResponse(
                success=False,
                message="Translation failed",
                error=result['error']
            )
            
    except HTTPException:
        raise
    except Exception as e:
        return TranslationResponse(
            success=False,
            message="Internal server error",
            error=str(e)
        )


@app.get("/translation/{translation_id}")
async def get_translation_status(translation_id: str):
    """Get translation status and results."""
    if translation_id not in active_translations:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    result = active_translations[translation_id]
    
    return {
        "translation_id": translation_id,
        "success": result['success'],
        "status": "completed" if result['success'] else "failed",
        "processing_time": result['processing_time'],
        "page_count": result.get('page_count', 0),
        "quality_assessment": result.get('validation', {}).get('quality_assessment', {}),
        "output_files": result.get('output_files', []),
        "download_url": f"/download/{translation_id}" if result['success'] else None
    }


@app.get("/download/{translation_id}")
async def download_translation(translation_id: str):
    """Download translated document."""
    if translation_id not in active_translations:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    result = active_translations[translation_id]
    
    if not result['success']:
        raise HTTPException(status_code=400, detail="Translation failed")
    
    output_files = result.get('output_files', [])
    if not output_files:
        raise HTTPException(status_code=404, detail="No output files available")
    
    # Return the first output file (main translated document)
    output_file = output_files[0]
    
    if not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    filename = Path(output_file).name
    
    return FileResponse(
        path=output_file,
        filename=filename,
        media_type='application/octet-stream'
    )


@app.delete("/translation/{translation_id}")
async def delete_translation(translation_id: str):
    """Delete translation results and clean up files."""
    if translation_id not in active_translations:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    result = active_translations[translation_id]
    
    # Clean up output files
    for output_file in result.get('output_files', []):
        try:
            if os.path.exists(output_file):
                os.unlink(output_file)
        except:
            pass
    
    # Remove from active translations
    del active_translations[translation_id]
    
    return {"message": "Translation deleted successfully"}


async def cleanup_temp_file(file_path: str):
    """Background task to clean up temporary files."""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except:
        pass


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )

