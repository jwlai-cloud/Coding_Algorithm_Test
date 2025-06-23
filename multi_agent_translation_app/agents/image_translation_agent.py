"""Image Translation Agent for OCR, translation, and text re-rendering."""

import os
import tempfile
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont
from google.cloud import vision, translate_v2 as translate, storage
from loguru import logger

from .base_agent import BaseAgent, AgentResult
from config.settings import settings, get_gcs_config


class TextBlock:
    """Represents a text block with its properties."""
    def __init__(self, text: str, bounding_box: List[Tuple[int, int]], confidence: float = 1.0):
        self.text = text
        self.bounding_box = bounding_box  # List of (x, y) coordinates
        self.confidence = confidence
        self.translated_text = ""
        self.font_size = 12
        self.font_color = (0, 0, 0)  # RGB


class ImageTranslationAgent(BaseAgent):
    """
    Image Translation Agent performs OCR, translation, and text re-rendering.
    
    Responsibilities:
    - Extract text and bounding boxes using Google Cloud Vision API
    - Group text into logical blocks
    - Create clean image by masking original text
    - Translate text using Google Cloud Translation API
    - Re-render translated text preserving layout and style
    """
    
    def __init__(self):
        super().__init__("image_translation_agent", "ImageTranslationAgent")
        self.vision_client = vision.ImageAnnotatorClient()
        self.translate_client = translate.Client()
        self.gcs_client = storage.Client()
        self.gcs_config = get_gcs_config()
        self.bucket = self.gcs_client.bucket(self.gcs_config["bucket_name"])
        
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate image translation input data."""
        required_fields = ["image_uri", "target_language"]
        return all(field in input_data for field in required_fields)
        
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process image translation."""
        try:
            if not await self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    error="Invalid input data. Required: image_uri, target_language"
                )
                
            image_uri = input_data["image_uri"]
            target_language = input_data["target_language"]
            source_language = input_data.get("source_language", "auto")
            page_number = input_data.get("page_number", 1)
            
            self.logger.info(f"Starting image translation for page {page_number}")
            
            # Step 1: Download image from GCS
            local_image_path = await self.download_image(image_uri)
            
            # Step 2: Perform OCR to extract text and bounding boxes
            text_blocks = await self.extract_text_with_ocr(local_image_path)
            
            if not text_blocks:
                self.logger.warning("No text detected in image")
                return AgentResult(
                    success=True,
                    data={
                        "translated_image_uri": image_uri,  # Return original if no text
                        "text_blocks_count": 0,
                        "page_number": page_number
                    }
                )
                
            # Step 3: Group text blocks into logical units
            grouped_blocks = await self.group_text_blocks(text_blocks)
            
            # Step 4: Create clean image by masking text areas
            clean_image_path = await self.create_clean_image(local_image_path, grouped_blocks)
            
            # Step 5: Translate text blocks
            translated_blocks = await self.translate_text_blocks(grouped_blocks, target_language, source_language)
            
            # Step 6: Re-render translated text onto clean image
            final_image_path = await self.render_translated_text(clean_image_path, translated_blocks)
            
            # Step 7: Upload final translated image to GCS
            translated_image_uri = await self.upload_translated_image(final_image_path, page_number)
            
            # Clean up local files
            await self.cleanup_local_files([local_image_path, clean_image_path, final_image_path])
            
            self.logger.info(f"Image translation completed for page {page_number}")
            
            return AgentResult(
                success=True,
                data={
                    "translated_image_uri": translated_image_uri,
                    "text_blocks_count": len(text_blocks),
                    "translated_blocks_count": len(translated_blocks),
                    "page_number": page_number
                },
                metadata={
                    "original_image_uri": image_uri,
                    "source_language": source_language,
                    "target_language": target_language
                }
            )
            
        except Exception as e:
            self.logger.error(f"Image translation failed: {str(e)}")
            return AgentResult(success=False, error=str(e))
            
    async def download_image(self, image_uri: str) -> str:
        """Download image from GCS."""
        try:
            # Parse GCS URI
            path_parts = image_uri.replace("gs://", "").split("/", 1)
            bucket_name = path_parts[0]
            blob_name = path_parts[1]
            
            # Download to temporary file
            bucket = self.gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_file.close()
            
            blob.download_to_filename(temp_file.name)
            self.logger.debug(f"Downloaded image: {image_uri}")
            return temp_file.name
            
        except Exception as e:
            raise Exception(f"Image download failed: {str(e)}")
            
    async def extract_text_with_ocr(self, image_path: str) -> List[TextBlock]:
        """Extract text and bounding boxes using Google Cloud Vision API."""
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
                
            image = vision.Image(content=content)
            
            # Use DOCUMENT_TEXT_DETECTION for better layout analysis
            response = self.vision_client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")
                
            text_blocks = []
            
            # Process full text annotation
            if response.full_text_annotation:
                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        # Extract text from paragraphs in the block
                        block_text = ""
                        for paragraph in block.paragraphs:
                            for word in paragraph.words:
                                word_text = ''.join([symbol.text for symbol in word.symbols])
                                block_text += word_text + " "
                                
                        if block_text.strip():
                            # Get bounding box coordinates
                            vertices = [(vertex.x, vertex.y) for vertex in block.bounding_box.vertices]
                            
                            text_block = TextBlock(
                                text=block_text.strip(),
                                bounding_box=vertices,
                                confidence=block.confidence if hasattr(block, 'confidence') else 1.0
                            )
                            text_blocks.append(text_block)
                            
            self.logger.info(f"Extracted {len(text_blocks)} text blocks")
            return text_blocks
            
        except Exception as e:
            raise Exception(f"OCR extraction failed: {str(e)}")
            
    async def group_text_blocks(self, text_blocks: List[TextBlock]) -> List[TextBlock]:
        """Group nearby text blocks into logical units."""
        # For now, return blocks as-is
        # In a more sophisticated implementation, you could:
        # 1. Merge blocks that are close together
        # 2. Group blocks by reading order
        # 3. Separate headers, body text, captions, etc.
        
        return text_blocks
        
    async def create_clean_image(self, image_path: str, text_blocks: List[TextBlock]) -> str:
        """Create a clean image by masking text areas."""
        try:
            # Load image
            image = cv2.imread(image_path)
            
            for text_block in text_blocks:
                # Create mask for text area
                points = np.array(text_block.bounding_box, np.int32)
                
                # Use inpainting to fill the text area
                mask = np.zeros(image.shape[:2], dtype=np.uint8)
                cv2.fillPoly(mask, [points], 255)
                
                # Simple inpainting - fill with surrounding color
                # In a more sophisticated approach, you could use cv2.inpaint
                image = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
                
            # Save clean image
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_file.close()
            
            cv2.imwrite(temp_file.name, image)
            self.logger.debug("Created clean image")
            return temp_file.name
            
        except Exception as e:
            raise Exception(f"Clean image creation failed: {str(e)}")
            
    async def translate_text_blocks(self, text_blocks: List[TextBlock], target_language: str, source_language: str) -> List[TextBlock]:
        """Translate text blocks."""
        try:
            translated_blocks = []
            
            for text_block in text_blocks:
                # Translate text
                if source_language == "auto":
                    result = self.translate_client.translate(
                        text_block.text,
                        target_language=target_language
                    )
                else:
                    result = self.translate_client.translate(
                        text_block.text,
                        target_language=target_language,
                        source_language=source_language
                    )
                    
                # Create translated block
                translated_block = TextBlock(
                    text=text_block.text,
                    bounding_box=text_block.bounding_box,
                    confidence=text_block.confidence
                )
                translated_block.translated_text = result['translatedText']
                
                # Estimate appropriate font size based on bounding box
                translated_block.font_size = await self.estimate_font_size(
                    translated_block.translated_text,
                    text_block.bounding_box
                )
                
                translated_blocks.append(translated_block)
                
            self.logger.info(f"Translated {len(translated_blocks)} text blocks")
            return translated_blocks
            
        except Exception as e:
            raise Exception(f"Text translation failed: {str(e)}")
            
    async def estimate_font_size(self, text: str, bounding_box: List[Tuple[int, int]]) -> int:
        """Estimate appropriate font size for the bounding box."""
        # Calculate bounding box dimensions
        x_coords = [point[0] for point in bounding_box]
        y_coords = [point[1] for point in bounding_box]
        
        width = max(x_coords) - min(x_coords)
        height = max(y_coords) - min(y_coords)
        
        # Simple heuristic: font size based on height and text length
        # This is a basic implementation - could be improved with actual font metrics
        estimated_size = max(8, min(72, int(height * 0.7)))
        
        # Adjust for text length
        if len(text) > 50:
            estimated_size = int(estimated_size * 0.8)
        elif len(text) < 10:
            estimated_size = int(estimated_size * 1.2)
            
        return estimated_size
        
    async def render_translated_text(self, clean_image_path: str, translated_blocks: List[TextBlock]) -> str:
        """Render translated text onto the clean image."""
        try:
            # Load clean image
            image = Image.open(clean_image_path)
            draw = ImageDraw.Draw(image)
            
            for text_block in translated_blocks:
                # Calculate text position (top-left of bounding box)
                x_coords = [point[0] for point in text_block.bounding_box]
                y_coords = [point[1] for point in text_block.bounding_box]
                
                x = min(x_coords)
                y = min(y_coords)
                width = max(x_coords) - min(x_coords)
                height = max(y_coords) - min(y_coords)
                
                # Try to load a font, fallback to default
                try:
                    font = ImageFont.truetype("arial.ttf", text_block.font_size)
                except:
                    try:
                        font = ImageFont.load_default()
                    except:
                        font = None
                        
                # Handle text wrapping if it's too long for the bounding box
                wrapped_text = await self.wrap_text(
                    text_block.translated_text,
                    width,
                    font
                )
                
                # Draw text
                draw.multiline_text(
                    (x, y),
                    wrapped_text,
                    fill=text_block.font_color,
                    font=font,
                    spacing=2
                )
                
            # Save final image
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_file.close()
            
            image.save(temp_file.name, "PNG")
            self.logger.debug("Rendered translated text")
            return temp_file.name
            
        except Exception as e:
            raise Exception(f"Text rendering failed: {str(e)}")
            
    async def wrap_text(self, text: str, max_width: int, font) -> str:
        """Wrap text to fit within the specified width."""
        if not font:
            return text
            
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            
            # Get text width
            try:
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0]
            except:
                # Fallback for older PIL versions
                text_width = len(test_line) * (font.size if hasattr(font, 'size') else 10)
                
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, add it anyway
                    lines.append(word)
                    
        if current_line:
            lines.append(' '.join(current_line))
            
        return '\n'.join(lines)
        
    async def upload_translated_image(self, image_path: str, page_number: int) -> str:
        """Upload translated image to GCS."""
        try:
            # Generate blob name
            filename = f"translated_page_{page_number:03d}_{int(self.get_current_time())}.png"
            blob_name = f"{self.gcs_config['translated_folder']}/{filename}"
            
            # Upload to GCS
            blob = self.bucket.blob(blob_name)
            blob.upload_from_filename(image_path)
            
            # Generate GCS URI
            image_uri = f"gs://{self.gcs_config['bucket_name']}/{blob_name}"
            
            self.logger.debug(f"Uploaded translated image: {image_uri}")
            return image_uri
            
        except Exception as e:
            raise Exception(f"Translated image upload failed: {str(e)}")
            
    async def cleanup_local_files(self, file_paths: List[str]):
        """Clean up temporary local files."""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up file {file_path}: {str(e)}")
                
    def get_current_time(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
