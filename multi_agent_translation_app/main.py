"""Main application for the Multi-Agent Document Translation App."""

import asyncio
import sys
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents import OrchestratorAgent
from config.settings import settings
from utils import GCSHelper


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format=settings.LOG_FORMAT,
    level=settings.LOG_LEVEL,
    colorize=True
)


class TranslationRequest(BaseModel):
    """Request model for document translation."""
    document_path: str
    target_language: str
    source_language: str = "auto"
    job_id: Optional[str] = None


class TranslationResponse(BaseModel):
    """Response model for document translation."""
    success: bool
    job_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DocumentTranslationApp:
    """Main application class for document translation."""
    
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.gcs_helper = GCSHelper()
        self.app = FastAPI(
            title="Multi-Agent Document Translation App",
            description="Translate documents while preserving layout using multi-agent system",
            version="1.0.0"
        )
        self.setup_routes()
        
    def setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def root():
            return {"message": "Multi-Agent Document Translation App", "version": "1.0.0"}
            
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "agents": ["orchestrator", "conversion", "translation", "validation"]}
            
        @self.app.post("/translate", response_model=TranslationResponse)
        async def translate_document(request: TranslationRequest):
            """Translate a document."""
            try:
                logger.info(f"Received translation request: {request.dict()}")
                
                # Validate target language
                if request.target_language not in settings.SUPPORTED_LANGUAGES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported target language: {request.target_language}"
                    )
                    
                # Start orchestrator
                await self.orchestrator.start()
                
                # Process translation request
                result = await self.orchestrator.process(request.dict())
                
                if result.success:
                    return TranslationResponse(
                        success=True,
                        job_id=result.data["job_id"],
                        status=result.data["status"],
                        message="Translation completed successfully",
                        data=result.data
                    )
                else:
                    return TranslationResponse(
                        success=False,
                        job_id=request.job_id or "unknown",
                        status="failed",
                        message="Translation failed",
                        error=result.error
                    )
                    
            except Exception as e:
                logger.error(f"Translation request failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/upload")
        async def upload_document(file: UploadFile = File(...)):
            """Upload a document for translation."""
            try:
                # Validate file type
                allowed_extensions = ['.pdf', '.pptx', '.ppt', '.docx', '.doc']
                file_extension = Path(file.filename).suffix.lower()
                
                if file_extension not in allowed_extensions:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported file type: {file_extension}"
                    )
                    
                # Upload to GCS
                gcs_path = f"{settings.GCS_INPUT_FOLDER}/{file.filename}"
                
                # Save file temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    content = await file.read()
                    temp_file.write(content)
                    temp_file.flush()
                    
                    # Upload to GCS
                    gcs_uri = self.gcs_helper.upload_file(temp_file.name, gcs_path)
                    
                    # Clean up temp file
                    import os
                    os.unlink(temp_file.name)
                    
                return {
                    "success": True,
                    "message": "File uploaded successfully",
                    "document_path": gcs_uri,
                    "filename": file.filename
                }
                
            except Exception as e:
                logger.error(f"File upload failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/job/{job_id}")
        async def get_job_status(job_id: str):
            """Get the status of a translation job."""
            try:
                job = self.orchestrator.get_job_status(job_id)
                
                if not job:
                    raise HTTPException(status_code=404, detail="Job not found")
                    
                return {
                    "job_id": job.job_id,
                    "status": job.status,
                    "document_path": job.document_path,
                    "target_language": job.target_language,
                    "source_language": job.source_language,
                    "pages_processed": len(job.page_images) if job.page_images else 0,
                    "pages_translated": len(job.translated_images) if job.translated_images else 0,
                    "output_document": job.output_document,
                    "quality_scores": job.quality_scores,
                    "error_message": job.error_message
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Job status request failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/jobs")
        async def list_jobs():
            """List all active translation jobs."""
            try:
                jobs = self.orchestrator.list_active_jobs()
                
                return {
                    "jobs": [
                        {
                            "job_id": job.job_id,
                            "status": job.status,
                            "target_language": job.target_language,
                            "pages_processed": len(job.page_images) if job.page_images else 0
                        }
                        for job in jobs
                    ],
                    "total_jobs": len(jobs)
                }
                
            except Exception as e:
                logger.error(f"Jobs list request failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/languages")
        async def get_supported_languages():
            """Get list of supported languages."""
            return {
                "supported_languages": settings.SUPPORTED_LANGUAGES,
                "default_source": settings.DEFAULT_SOURCE_LANGUAGE
            }
            
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the FastAPI server."""
        import uvicorn
        
        logger.info(f"Starting Multi-Agent Document Translation App on {host}:{port}")
        
        # Start orchestrator
        await self.orchestrator.start()
        
        # Start server
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level=settings.LOG_LEVEL.lower()
        )
        server = uvicorn.Server(config)
        await server.serve()


async def main():
    """Main entry point."""
    app = DocumentTranslationApp()
    await app.start_server()


if __name__ == "__main__":
    asyncio.run(main())

