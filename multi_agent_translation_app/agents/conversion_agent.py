"""Conversion Agent for converting documents to high-resolution page images."""

import os
import tempfile
from typing import Dict, Any, List
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
from google.cloud import storage
from loguru import logger

from .base_agent import BaseAgent, AgentResult
from config.settings import settings, get_gcs_config


class ConversionAgent(BaseAgent):
    """
    Conversion Agent converts source documents into high-resolution page images.
    
    Responsibilities:
    - Convert PDF, PPTX, and other document formats to page images
    - Ensure high resolution for accurate OCR
    - Upload page images to Google Cloud Storage
    - Return list of image URIs for further processing
    """
    
    def __init__(self):
        super().__init__("conversion_agent", "ConversionAgent")
        self.gcs_client = storage.Client()
        self.gcs_config = get_gcs_config()
        self.bucket = self.gcs_client.bucket(self.gcs_config["bucket_name"])
        
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate conversion input data."""
        required_fields = ["document_path", "job_id"]
        return all(field in input_data for field in required_fields)
        
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Convert document to page images."""
        try:
            if not await self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    error="Invalid input data. Required: document_path, job_id"
                )
                
            document_path = input_data["document_path"]
            job_id = input_data["job_id"]
            
            self.logger.info(f"Starting document conversion for job {job_id}")
            
            # Download document from GCS if it's a GCS URI
            local_document_path = await self.download_document(document_path)
            
            # Determine document type and convert accordingly
            file_extension = Path(local_document_path).suffix.lower()
            
            if file_extension == '.pdf':
                page_images = await self.convert_pdf_to_images(local_document_path, job_id)
            elif file_extension in ['.pptx', '.ppt']:
                page_images = await self.convert_pptx_to_images(local_document_path, job_id)
            elif file_extension in ['.docx', '.doc']:
                page_images = await self.convert_docx_to_images(local_document_path, job_id)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unsupported document format: {file_extension}"
                )
                
            # Upload page images to GCS
            page_image_uris = await self.upload_page_images(page_images, job_id)
            
            # Clean up local files
            await self.cleanup_local_files([local_document_path] + page_images)
            
            self.logger.info(f"Conversion completed: {len(page_image_uris)} pages")
            
            return AgentResult(
                success=True,
                data={
                    "page_images": page_image_uris,
                    "pages_count": len(page_image_uris),
                    "job_id": job_id
                },
                metadata={
                    "document_type": file_extension,
                    "original_document": document_path
                }
            )
            
        except Exception as e:
            self.logger.error(f"Document conversion failed: {str(e)}")
            return AgentResult(success=False, error=str(e))
            
    async def download_document(self, document_path: str) -> str:
        """Download document from GCS or return local path."""
        if document_path.startswith("gs://"):
            # Parse GCS URI
            path_parts = document_path.replace("gs://", "").split("/", 1)
            bucket_name = path_parts[0]
            blob_name = path_parts[1]
            
            # Download to temporary file
            bucket = self.gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            # Create temporary file with appropriate extension
            file_extension = Path(blob_name).suffix
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
            temp_file.close()
            
            blob.download_to_filename(temp_file.name)
            self.logger.info(f"Downloaded document from GCS: {document_path}")
            return temp_file.name
        else:
            # Local file path
            if not os.path.exists(document_path):
                raise FileNotFoundError(f"Document not found: {document_path}")
            return document_path
            
    async def convert_pdf_to_images(self, pdf_path: str, job_id: str) -> List[str]:
        """Convert PDF to high-resolution page images."""
        try:
            self.logger.info(f"Converting PDF to images: {pdf_path}")
            
            # Convert PDF pages to images
            images = convert_from_path(
                pdf_path,
                dpi=settings.IMAGE_DPI,
                fmt=settings.IMAGE_FORMAT.lower()
            )
            
            # Save images to temporary files
            image_paths = []
            for i, image in enumerate(images):
                # Resize if image is too large
                if image.size[0] > settings.MAX_IMAGE_SIZE[0] or image.size[1] > settings.MAX_IMAGE_SIZE[1]:
                    image.thumbnail(settings.MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
                    
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=f".{settings.IMAGE_FORMAT.lower()}",
                    prefix=f"{job_id}_page_{i+1:03d}_"
                )
                temp_file.close()
                
                image.save(temp_file.name, settings.IMAGE_FORMAT)
                image_paths.append(temp_file.name)
                
            self.logger.info(f"Converted {len(image_paths)} PDF pages to images")
            return image_paths
            
        except Exception as e:
            raise Exception(f"PDF conversion failed: {str(e)}")
            
    async def convert_pptx_to_images(self, pptx_path: str, job_id: str) -> List[str]:
        """Convert PowerPoint to page images."""
        try:
            from pptx import Presentation
            import io
            
            self.logger.info(f"Converting PPTX to images: {pptx_path}")
            
            # This is a simplified implementation
            # In a real scenario, you might use libraries like python-pptx with additional tools
            # or convert PPTX to PDF first, then to images
            
            # For now, we'll create a placeholder implementation
            # that would need to be enhanced with proper PPTX to image conversion
            
            prs = Presentation(pptx_path)
            image_paths = []
            
            # Placeholder: In reality, you'd need to render each slide to an image
            # This might involve using libraries like aspose-slides or converting to PDF first
            for i, slide in enumerate(prs.slides):
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=f".{settings.IMAGE_FORMAT.lower()}",
                    prefix=f"{job_id}_slide_{i+1:03d}_"
                )
                temp_file.close()
                
                # Placeholder: Create a blank image for now
                # In reality, you'd render the slide content
                placeholder_image = Image.new('RGB', (1920, 1080), color='white')
                placeholder_image.save(temp_file.name, settings.IMAGE_FORMAT)
                image_paths.append(temp_file.name)
                
            self.logger.warning("PPTX conversion is using placeholder implementation")
            return image_paths
            
        except Exception as e:
            raise Exception(f"PPTX conversion failed: {str(e)}")
            
    async def convert_docx_to_images(self, docx_path: str, job_id: str) -> List[str]:
        """Convert Word document to page images."""
        try:
            self.logger.info(f"Converting DOCX to images: {docx_path}")
            
            # This is a placeholder implementation
            # In reality, you'd need to use libraries like python-docx2pdf or similar
            # to convert DOCX to PDF first, then to images
            
            # For now, create a single placeholder image
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f".{settings.IMAGE_FORMAT.lower()}",
                prefix=f"{job_id}_page_001_"
            )
            temp_file.close()
            
            # Placeholder: Create a blank image
            placeholder_image = Image.new('RGB', (2480, 3508), color='white')  # A4 size at 300 DPI
            placeholder_image.save(temp_file.name, settings.IMAGE_FORMAT)
            
            self.logger.warning("DOCX conversion is using placeholder implementation")
            return [temp_file.name]
            
        except Exception as e:
            raise Exception(f"DOCX conversion failed: {str(e)}")
            
    async def upload_page_images(self, image_paths: List[str], job_id: str) -> List[str]:
        """Upload page images to Google Cloud Storage."""
        try:
            image_uris = []
            
            for i, image_path in enumerate(image_paths):
                # Generate blob name
                filename = f"{job_id}_page_{i+1:03d}.{settings.IMAGE_FORMAT.lower()}"
                blob_name = f"{self.gcs_config['pages_folder']}/{filename}"
                
                # Upload to GCS
                blob = self.bucket.blob(blob_name)
                blob.upload_from_filename(image_path)
                
                # Generate GCS URI
                image_uri = f"gs://{self.gcs_config['bucket_name']}/{blob_name}"
                image_uris.append(image_uri)
                
                self.logger.debug(f"Uploaded page image: {image_uri}")
                
            self.logger.info(f"Uploaded {len(image_uris)} page images to GCS")
            return image_uris
            
        except Exception as e:
            raise Exception(f"Image upload failed: {str(e)}")
            
    async def cleanup_local_files(self, file_paths: List[str]):
        """Clean up temporary local files."""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up file {file_path}: {str(e)}")
                
    def get_supported_formats(self) -> List[str]:
        """Get list of supported document formats."""
        return ['.pdf', '.pptx', '.ppt', '.docx', '.doc']

