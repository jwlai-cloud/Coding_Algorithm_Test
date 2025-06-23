"""Orchestrator Agent for managing the document translation workflow."""

import asyncio
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from google.cloud import storage, translate_v2 as translate
from loguru import logger

from .base_agent import BaseAgent, AgentResult, AgentStatus
from config.settings import settings, get_gcs_config


@dataclass
class TranslationJob:
    """Represents a document translation job."""
    job_id: str
    document_path: str
    target_language: str
    source_language: str = "auto"
    status: str = "pending"
    page_images: List[str] = None
    translated_images: List[str] = None
    output_document: Optional[str] = None
    quality_scores: List[float] = None
    error_message: Optional[str] = None


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent manages the overall workflow and coordinates other agents.
    
    Responsibilities:
    - Receive document translation requests
    - Detect source language automatically
    - Coordinate with Conversion, Translation, and Validation agents
    - Assemble final translated document
    - Handle errors and retries
    """
    
    def __init__(self):
        super().__init__("orchestrator", "OrchestratorAgent")
        self.gcs_client = storage.Client()
        self.translate_client = translate.Client()
        self.gcs_config = get_gcs_config()
        self.active_jobs: Dict[str, TranslationJob] = {}
        
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate orchestrator input data."""
        required_fields = ["document_path", "target_language"]
        return all(field in input_data for field in required_fields)
        
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process a document translation request."""
        try:
            if not await self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    error="Invalid input data. Required: document_path, target_language"
                )
                
            job_id = input_data.get("job_id", f"job_{asyncio.get_event_loop().time()}")
            document_path = input_data["document_path"]
            target_language = input_data["target_language"]
            source_language = input_data.get("source_language", "auto")
            
            # Create translation job
            job = TranslationJob(
                job_id=job_id,
                document_path=document_path,
                target_language=target_language,
                source_language=source_language,
                page_images=[],
                translated_images=[],
                quality_scores=[]
            )
            
            self.active_jobs[job_id] = job
            self.logger.info(f"Starting translation job {job_id}")
            
            # Step 1: Auto-detect language if needed
            if source_language == "auto":
                detected_language = await self.detect_language(document_path)
                job.source_language = detected_language
                self.logger.info(f"Detected source language: {detected_language}")
                
            # Step 2: Convert document to page images
            conversion_result = await self.invoke_conversion_agent(job)
            if not conversion_result.success:
                job.status = "failed"
                job.error_message = conversion_result.error
                return conversion_result
                
            job.page_images = conversion_result.data["page_images"]
            job.status = "converting"
            
            # Step 3: Translate each page image
            translation_results = []
            for i, page_image_uri in enumerate(job.page_images):
                self.logger.info(f"Translating page {i+1}/{len(job.page_images)}")
                
                translation_result = await self.invoke_translation_agent({
                    "image_uri": page_image_uri,
                    "target_language": job.target_language,
                    "source_language": job.source_language,
                    "page_number": i + 1
                })
                
                if not translation_result.success:
                    self.logger.error(f"Failed to translate page {i+1}: {translation_result.error}")
                    continue
                    
                translation_results.append(translation_result.data)
                job.translated_images.append(translation_result.data["translated_image_uri"])
                
            job.status = "translating"
            
            # Step 4: Validate translation quality
            validation_results = []
            for i, (original_uri, translated_uri) in enumerate(zip(job.page_images, job.translated_images)):
                validation_result = await self.invoke_validation_agent({
                    "original_image_uri": original_uri,
                    "translated_image_uri": translated_uri,
                    "page_number": i + 1
                })
                
                if validation_result.success:
                    quality_score = validation_result.data.get("quality_score", 0.0)
                    job.quality_scores.append(quality_score)
                    validation_results.append(validation_result.data)
                    
            job.status = "validating"
            
            # Step 5: Assemble final document
            if job.translated_images:
                final_document_result = await self.assemble_final_document(job)
                if final_document_result.success:
                    job.output_document = final_document_result.data["output_document_uri"]
                    job.status = "completed"
                else:
                    job.status = "failed"
                    job.error_message = final_document_result.error
                    
            # Calculate overall quality score
            overall_quality = sum(job.quality_scores) / len(job.quality_scores) if job.quality_scores else 0.0
            
            return AgentResult(
                success=job.status == "completed",
                data={
                    "job_id": job_id,
                    "status": job.status,
                    "output_document": job.output_document,
                    "pages_processed": len(job.page_images),
                    "pages_translated": len(job.translated_images),
                    "overall_quality_score": overall_quality,
                    "individual_quality_scores": job.quality_scores
                },
                error=job.error_message,
                metadata={
                    "source_language": job.source_language,
                    "target_language": job.target_language,
                    "validation_results": validation_results
                }
            )
            
        except Exception as e:
            self.logger.error(f"Orchestrator processing failed: {str(e)}")
            return AgentResult(success=False, error=str(e))
            
    async def detect_language(self, document_path: str) -> str:
        """Detect the source language of the document."""
        try:
            # For now, we'll use a simple text extraction and detection
            # In a real implementation, you might extract text from the first page
            # and use Google Translate API to detect the language
            
            # Placeholder implementation
            result = self.translate_client.detect_language("Sample text from document")
            detected_language = result["language"]
            confidence = result["confidence"]
            
            self.logger.info(f"Language detection: {detected_language} (confidence: {confidence})")
            return detected_language
            
        except Exception as e:
            self.logger.warning(f"Language detection failed: {str(e)}, defaulting to 'en'")
            return "en"
            
    async def invoke_conversion_agent(self, job: TranslationJob) -> AgentResult:
        """Invoke the Conversion Agent to convert document to page images."""
        try:
            # Simulate agent invocation using ADK A2A protocol
            message = await self.send_message(
                receiver="conversion_agent",
                message_type="convert_document",
                payload={
                    "document_path": job.document_path,
                    "job_id": job.job_id
                },
                correlation_id=job.job_id
            )
            
            # In a real implementation, this would wait for the agent's response
            # For now, we'll simulate the conversion process
            from .conversion_agent import ConversionAgent
            conversion_agent = ConversionAgent()
            
            result = await conversion_agent.process({
                "document_path": job.document_path,
                "job_id": job.job_id
            })
            
            return result
            
        except Exception as e:
            return AgentResult(success=False, error=f"Conversion agent invocation failed: {str(e)}")
            
    async def invoke_translation_agent(self, input_data: Dict[str, Any]) -> AgentResult:
        """Invoke the Image Translation Agent."""
        try:
            from .image_translation_agent import ImageTranslationAgent
            translation_agent = ImageTranslationAgent()
            
            result = await translation_agent.process(input_data)
            return result
            
        except Exception as e:
            return AgentResult(success=False, error=f"Translation agent invocation failed: {str(e)}")
            
    async def invoke_validation_agent(self, input_data: Dict[str, Any]) -> AgentResult:
        """Invoke the Validation Agent."""
        try:
            from .validation_agent import ValidationAgent
            validation_agent = ValidationAgent()
            
            result = await validation_agent.process(input_data)
            return result
            
        except Exception as e:
            return AgentResult(success=False, error=f"Validation agent invocation failed: {str(e)}")
            
    async def assemble_final_document(self, job: TranslationJob) -> AgentResult:
        """Assemble the final translated document from page images."""
        try:
            # This would typically convert the translated page images back to a PDF
            # For now, we'll create a simple implementation
            
            output_filename = f"translated_{job.job_id}.pdf"
            output_path = f"{self.gcs_config['output_folder']}/{output_filename}"
            
            # Placeholder: In a real implementation, you would:
            # 1. Download all translated page images
            # 2. Convert them back to a PDF using a library like img2pdf
            # 3. Upload the final PDF to Cloud Storage
            
            self.logger.info(f"Assembling final document: {output_path}")
            
            return AgentResult(
                success=True,
                data={
                    "output_document_uri": f"gs://{self.gcs_config['bucket_name']}/{output_path}",
                    "pages_count": len(job.translated_images)
                }
            )
            
        except Exception as e:
            return AgentResult(success=False, error=f"Document assembly failed: {str(e)}")
            
    def get_job_status(self, job_id: str) -> Optional[TranslationJob]:
        """Get the status of a translation job."""
        return self.active_jobs.get(job_id)
        
    def list_active_jobs(self) -> List[TranslationJob]:
        """List all active translation jobs."""
        return list(self.active_jobs.values())

