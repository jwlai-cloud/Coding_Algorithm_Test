"""Document to Image Converter Agent."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List
import tempfile
import os

from pdf2image import convert_from_path
from PIL import Image
import PyPDF2
from docx import Document

from .base_agent import BaseAgent, AgentResult


class DocumentConverterAgent(BaseAgent):
    """Agent responsible for converting documents to images."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("document_converter", config)
        self.supported_formats = ['.pdf', '.docx', '.doc', '.txt']
        self.temp_dir = None
    
    async def _initialize(self):
        """Initialize the document converter agent."""
        self.temp_dir = self._create_temp_dir()
        self.logger.info("Document converter agent initialized")
    
    async def _cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
        self.logger.info("Document converter agent cleaned up")
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Convert document to images."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate input
            if not self._validate_input(input_data, ['document_path']):
                return AgentResult(
                    success=False,
                    error="Missing required field: document_path"
                )
            
            document_path = Path(input_data['document_path'])
            
            if not document_path.exists():
                return AgentResult(
                    success=False,
                    error=f"Document not found: {document_path}"
                )
            
            # Check file size
            file_size_mb = document_path.stat().st_size / (1024 * 1024)
            max_size = self.config.get('max_file_size_mb', 50)
            
            if file_size_mb > max_size:
                return AgentResult(
                    success=False,
                    error=f"File size ({file_size_mb:.1f}MB) exceeds maximum ({max_size}MB)"
                )
            
            # Convert based on file type
            file_extension = document_path.suffix.lower()
            
            if file_extension == '.pdf':
                images = await self._convert_pdf_to_images(document_path)
            elif file_extension in ['.docx', '.doc']:
                images = await self._convert_docx_to_images(document_path)
            elif file_extension == '.txt':
                images = await self._convert_txt_to_images(document_path)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unsupported file format: {file_extension}"
                )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return AgentResult(
                success=True,
                data={
                    'images': images,
                    'page_count': len(images),
                    'original_format': file_extension,
                    'file_size_mb': file_size_mb
                },
                metadata={
                    'agent_id': self.agent_id,
                    'conversion_method': f'{file_extension}_to_images'
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Error converting document: {str(e)}")
            return AgentResult(
                success=False,
                error=f"Document conversion failed: {str(e)}"
            )
    
    async def _convert_pdf_to_images(self, pdf_path: Path) -> List[str]:
        """Convert PDF to images."""
        self.logger.info(f"Converting PDF to images: {pdf_path}")
        
        dpi = self.config.get('image_dpi', 300)
        image_format = self.config.get('image_format', 'PNG')
        
        # Convert PDF pages to images
        images = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            output_folder=str(self.temp_dir),
            fmt=image_format.lower()
        )
        
        image_paths = []
        for i, image in enumerate(images):
            image_path = self.temp_dir / f"page_{i+1:03d}.{image_format.lower()}"
            image.save(str(image_path), image_format)
            image_paths.append(str(image_path))
            
        self.logger.info(f"Converted {len(images)} pages to images")
        return image_paths
    
    async def _convert_docx_to_images(self, docx_path: Path) -> List[str]:
        """Convert DOCX to images."""
        self.logger.info(f"Converting DOCX to images: {docx_path}")
        
        # For DOCX, we'll need to convert to PDF first, then to images
        # This is a simplified approach - in production, you might want to use
        # more sophisticated document rendering libraries
        
        try:
            # Read DOCX content
            doc = Document(str(docx_path))
            
            # Extract text and create a simple image representation
            # This is a basic implementation - you might want to use libraries
            # like python-docx2txt or docx2pdf for better conversion
            
            text_content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            # Create image from text (simplified approach)
            image_paths = await self._text_to_image(text_content)
            
            return image_paths
            
        except Exception as e:
            self.logger.error(f"Error converting DOCX: {str(e)}")
            raise
    
    async def _convert_txt_to_images(self, txt_path: Path) -> List[str]:
        """Convert text file to images."""
        self.logger.info(f"Converting TXT to images: {txt_path}")
        
        with open(txt_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Split content into pages (simple approach)
        lines_per_page = 50
        lines = content.split('\n')
        pages = [lines[i:i+lines_per_page] for i in range(0, len(lines), lines_per_page)]
        
        image_paths = []
        for i, page_lines in enumerate(pages):
            image_path = await self._text_to_image(['\n'.join(page_lines)], page_num=i+1)
            image_paths.extend(image_path)
        
        return image_paths
    
    async def _text_to_image(self, text_content: List[str], page_num: int = 1) -> List[str]:
        """Convert text content to image."""
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a white background image
        width, height = 2480, 3508  # A4 size at 300 DPI
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        try:
            # Try to use a system font
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Draw text on image
        y_position = 50
        line_height = 30
        
        for text in text_content:
            # Wrap text to fit image width
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] <= width - 100:  # Leave margin
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw lines
            for line in lines:
                if y_position > height - 100:  # Leave bottom margin
                    break
                draw.text((50, y_position), line, fill='black', font=font)
                y_position += line_height
        
        # Save image
        image_path = self.temp_dir / f"page_{page_num:03d}.png"
        image.save(str(image_path), 'PNG')
        
        return [str(image_path)]

