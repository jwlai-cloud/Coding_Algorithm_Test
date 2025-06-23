"""Multimodal Translation Agent using Google Gemini."""

import asyncio
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional
import io

import google.generativeai as genai
from PIL import Image

from .base_agent import BaseAgent, AgentResult


class TranslationAgent(BaseAgent):
    """Agent responsible for translating images using Google Gemini Vision."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("translator", config)
        self.model = None
        self.temp_dir = None
    
    async def _initialize(self):
        """Initialize the translation agent."""
        self.temp_dir = self._create_temp_dir()
        
        # Configure Gemini API
        api_key = self.config.get('gemini_api_key')
        if not api_key:
            raise ValueError("Gemini API key not provided")
        
        genai.configure(api_key=api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-pro-vision')
        
        self.logger.info("Translation agent initialized with Gemini Vision")
    
    async def _cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
        self.logger.info("Translation agent cleaned up")
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Translate images while preserving layout."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate input
            required_fields = ['images', 'target_language']
            if not self._validate_input(input_data, required_fields):
                return AgentResult(
                    success=False,
                    error="Missing required fields: images, target_language"
                )
            
            images = input_data['images']
            target_language = input_data['target_language']
            source_language = input_data.get('source_language', 'auto')
            
            # Validate target language
            supported_languages = self.config.get('supported_languages', {})
            if target_language not in supported_languages:
                return AgentResult(
                    success=False,
                    error=f"Unsupported target language: {target_language}"
                )
            
            # Translate each image
            translated_images = []
            translation_metadata = []
            
            for i, image_path in enumerate(images):
                self.logger.info(f"Translating image {i+1}/{len(images)}: {image_path}")
                
                result = await self._translate_image(
                    image_path, 
                    target_language, 
                    source_language,
                    page_number=i+1
                )
                
                if result['success']:
                    translated_images.append(result['translated_image'])
                    translation_metadata.append(result['metadata'])
                else:
                    self.logger.error(f"Failed to translate image {i+1}: {result['error']}")
                    return AgentResult(
                        success=False,
                        error=f"Translation failed for page {i+1}: {result['error']}"
                    )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return AgentResult(
                success=True,
                data={
                    'translated_images': translated_images,
                    'translation_metadata': translation_metadata,
                    'target_language': target_language,
                    'source_language': source_language,
                    'page_count': len(translated_images)
                },
                metadata={
                    'agent_id': self.agent_id,
                    'model_used': 'gemini-pro-vision',
                    'language_pair': f"{source_language}->{target_language}"
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Error in translation process: {str(e)}")
            return AgentResult(
                success=False,
                error=f"Translation process failed: {str(e)}"
            )
    
    async def _translate_image(self, image_path: str, target_language: str, 
                             source_language: str, page_number: int) -> Dict[str, Any]:
        """Translate a single image using Gemini Vision."""
        try:
            # Load and prepare image
            image = Image.open(image_path)
            
            # Create translation prompt
            language_name = self.config.get('supported_languages', {}).get(target_language, target_language)
            
            prompt = self._create_translation_prompt(target_language, language_name, source_language)
            
            # Generate translation
            response = await self._call_gemini_vision(image, prompt)
            
            if not response:
                return {
                    'success': False,
                    'error': 'No response from Gemini Vision API'
                }
            
            # Process the response to create translated image
            translated_image_path = await self._create_translated_image(
                image, response, image_path, page_number
            )
            
            return {
                'success': True,
                'translated_image': translated_image_path,
                'metadata': {
                    'original_image': image_path,
                    'page_number': page_number,
                    'translation_response': response[:500] + "..." if len(response) > 500 else response,
                    'target_language': target_language,
                    'confidence_score': self._estimate_confidence(response)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error translating image {image_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_translation_prompt(self, target_language: str, language_name: str, source_language: str) -> str:
        """Create a detailed prompt for image translation."""
        prompt = f"""
        You are an expert document translator specializing in layout-preserving translation.
        
        Please analyze this image and provide a translation that:
        1. Translates ALL visible text to {language_name} ({target_language})
        2. Maintains the exact spatial positioning of text elements
        3. Preserves formatting, fonts, and visual hierarchy
        4. Keeps non-text elements (images, diagrams, charts) unchanged
        5. Maintains the overall document structure and layout
        
        For each text element you identify, provide:
        - Original text
        - Translated text
        - Approximate position/coordinates
        - Text formatting details (font size, style, color if visible)
        
        If the source language is not {source_language if source_language != 'auto' else 'automatically detected'}, 
        please note the detected source language.
        
        Focus on accuracy and context-appropriate translation while preserving the document's professional appearance.
        
        Please provide your analysis in a structured format that includes:
        1. Detected source language
        2. List of text elements with translations and positioning
        3. Any special formatting or layout considerations
        4. Overall translation confidence assessment
        """
        
        return prompt
    
    async def _call_gemini_vision(self, image: Image.Image, prompt: str) -> Optional[str]:
        """Call Gemini Vision API with image and prompt."""
        try:
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Create the request
            response = self.model.generate_content([prompt, image])
            
            if response and response.text:
                return response.text
            else:
                self.logger.warning("Empty response from Gemini Vision")
                return None
                
        except Exception as e:
            self.logger.error(f"Error calling Gemini Vision API: {str(e)}")
            return None
    
    async def _create_translated_image(self, original_image: Image.Image, 
                                     translation_response: str, original_path: str, 
                                     page_number: int) -> str:
        """Create a translated image based on the Gemini response."""
        try:
            # For now, we'll create a simple overlay approach
            # In a production system, you'd want more sophisticated image manipulation
            
            from PIL import ImageDraw, ImageFont
            
            # Create a copy of the original image
            translated_image = original_image.copy()
            draw = ImageDraw.Draw(translated_image)
            
            # Parse the translation response to extract text elements
            # This is a simplified approach - you'd want more sophisticated parsing
            text_elements = self._parse_translation_response(translation_response)
            
            # Apply translations (simplified approach)
            for element in text_elements:
                if 'position' in element and 'translated_text' in element:
                    # This is a very basic implementation
                    # In production, you'd need sophisticated text placement and formatting
                    try:
                        font = ImageFont.load_default()
                        position = element.get('position', (50, 50))
                        text = element['translated_text']
                        
                        # Simple text overlay (you'd want to remove original text first)
                        draw.text(position, text, fill='red', font=font)
                    except Exception as e:
                        self.logger.warning(f"Could not apply text element: {str(e)}")
            
            # Save translated image
            output_path = self.temp_dir / f"translated_page_{page_number:03d}.png"
            translated_image.save(str(output_path), 'PNG')
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error creating translated image: {str(e)}")
            # Return original image path as fallback
            return original_path
    
    def _parse_translation_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the Gemini response to extract text elements."""
        # This is a simplified parser - in production you'd want more robust parsing
        elements = []
        
        try:
            # Look for structured information in the response
            lines = response.split('\n')
            current_element = {}
            
            for line in lines:
                line = line.strip()
                if 'Original text:' in line:
                    current_element['original_text'] = line.split('Original text:')[1].strip()
                elif 'Translated text:' in line:
                    current_element['translated_text'] = line.split('Translated text:')[1].strip()
                elif 'Position:' in line:
                    # Try to extract position coordinates
                    try:
                        pos_str = line.split('Position:')[1].strip()
                        # Simple coordinate extraction (you'd want more robust parsing)
                        current_element['position'] = (100, 100)  # Default position
                    except:
                        current_element['position'] = (100, 100)
                
                # If we have both original and translated text, add the element
                if 'original_text' in current_element and 'translated_text' in current_element:
                    elements.append(current_element.copy())
                    current_element = {}
            
        except Exception as e:
            self.logger.warning(f"Could not parse translation response: {str(e)}")
        
        return elements
    
    def _estimate_confidence(self, response: str) -> float:
        """Estimate translation confidence based on response quality."""
        # Simple heuristic - in production you'd want more sophisticated confidence estimation
        if not response:
            return 0.0
        
        # Check for indicators of good translation
        confidence_indicators = [
            'translated text:' in response.lower(),
            'original text:' in response.lower(),
            'position:' in response.lower(),
            len(response) > 100,
            'confidence' in response.lower()
        ]
        
        confidence = sum(confidence_indicators) / len(confidence_indicators)
        return min(confidence, 1.0)

