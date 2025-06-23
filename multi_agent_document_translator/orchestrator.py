"""Multi-Agent Orchestrator for Document Translation."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime

from .agents import DocumentConverterAgent, TranslationAgent, ValidationAgent
from .config import get_agent_config, settings


class TranslationOrchestrator:
    """Orchestrates the multi-agent document translation process."""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.agents = {}
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize all agents."""
        if self.is_initialized:
            return
        
        try:
            # Initialize agents with their configurations
            self.agents['converter'] = DocumentConverterAgent(
                get_agent_config('document_converter')
            )
            
            self.agents['translator'] = TranslationAgent(
                get_agent_config('translator')
            )
            
            self.agents['validator'] = ValidationAgent(
                get_agent_config('validator')
            )
            
            # Start all agents
            for agent in self.agents.values():
                await agent.start()
            
            self.is_initialized = True
            print(f"✅ Multi-agent system initialized (Session: {self.session_id[:8]})")
            
        except Exception as e:
            print(f"❌ Failed to initialize agents: {str(e)}")
            raise
    
    async def shutdown(self):
        """Shutdown all agents."""
        if not self.is_initialized:
            return
        
        for agent in self.agents.values():
            await agent.stop()
        
        self.is_initialized = False
        print("🔄 Multi-agent system shutdown complete")
    
    async def translate_document(self, document_path: str, target_language: str, 
                               source_language: str = "auto", 
                               output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Translate a document using the multi-agent system.
        
        Args:
            document_path: Path to the input document
            target_language: Target language code (e.g., 'es', 'fr', 'de')
            source_language: Source language code (default: 'auto')
            output_path: Optional output path for translated document
            
        Returns:
            Dictionary containing translation results and metadata
        """
        if not self.is_initialized:
            await self.initialize()
        
        start_time = datetime.now()
        translation_id = str(uuid.uuid4())[:8]
        
        print(f"🚀 Starting document translation (ID: {translation_id})")
        print(f"📄 Document: {document_path}")
        print(f"🌐 Language: {source_language} → {target_language}")
        
        try:
            # Validate inputs
            doc_path = Path(document_path)
            if not doc_path.exists():
                raise FileNotFoundError(f"Document not found: {document_path}")
            
            if target_language not in settings.supported_languages:
                raise ValueError(f"Unsupported target language: {target_language}")
            
            # Step 1: Convert document to images
            print("🔄 Step 1: Converting document to images...")
            converter_result = await self.agents['converter'].process({
                'document_path': str(doc_path)
            })
            
            if not converter_result.success:
                raise Exception(f"Document conversion failed: {converter_result.error}")
            
            images = converter_result.data['images']
            page_count = converter_result.data['page_count']
            print(f"✅ Converted {page_count} pages to images")
            
            # Step 2: Translate images
            print("🔄 Step 2: Translating images with Gemini Vision...")
            translation_result = await self.agents['translator'].process({
                'images': images,
                'target_language': target_language,
                'source_language': source_language
            })
            
            if not translation_result.success:
                raise Exception(f"Translation failed: {translation_result.error}")
            
            translated_images = translation_result.data['translated_images']
            translation_metadata = translation_result.data['translation_metadata']
            print(f"✅ Translated {len(translated_images)} pages")
            
            # Step 3: Validate translation quality
            print("🔄 Step 3: Validating translation quality...")
            validation_result = await self.agents['validator'].process({
                'original_images': images,
                'translated_images': translated_images,
                'translation_metadata': translation_metadata,
                'target_language': target_language
            })
            
            if not validation_result.success:
                print(f"⚠️ Validation failed: {validation_result.error}")
                # Continue with results even if validation fails
                validation_data = {'quality_assessment': {'grade': 'Unknown', 'pass': False}}
            else:
                validation_data = validation_result.data
                quality = validation_data['quality_assessment']
                print(f"✅ Validation complete - Grade: {quality['grade']} ({quality.get('overall_score', 0):.2f})")
            
            # Step 4: Generate output (if requested)
            output_files = []
            if output_path:
                output_files = await self._generate_output(
                    translated_images, output_path, doc_path.suffix
                )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Compile results
            results = {
                'success': True,
                'translation_id': translation_id,
                'session_id': self.session_id,
                'processing_time': processing_time,
                'input_document': str(doc_path),
                'target_language': target_language,
                'source_language': source_language,
                'page_count': page_count,
                'original_images': images,
                'translated_images': translated_images,
                'output_files': output_files,
                'validation': validation_data,
                'metadata': {
                    'converter_time': converter_result.processing_time,
                    'translation_time': translation_result.processing_time,
                    'validation_time': validation_result.processing_time if validation_result.success else 0,
                    'file_size_mb': converter_result.data.get('file_size_mb', 0),
                    'original_format': converter_result.data.get('original_format', 'unknown')
                }
            }
            
            print(f"🎉 Translation completed successfully in {processing_time:.1f}s")
            print(f"📊 Quality: {validation_data.get('quality_assessment', {}).get('grade', 'Unknown')}")
            
            return results
            
        except Exception as e:
            error_msg = f"Translation failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            return {
                'success': False,
                'error': error_msg,
                'translation_id': translation_id,
                'session_id': self.session_id,
                'processing_time': (datetime.now() - start_time).total_seconds()
            }
    
    async def _generate_output(self, translated_images: List[str], 
                             output_path: str, original_format: str) -> List[str]:
        """Generate output files from translated images."""
        try:
            output_files = []
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if original_format.lower() == '.pdf':
                # Convert images back to PDF
                pdf_path = await self._images_to_pdf(translated_images, output_path)
                output_files.append(pdf_path)
            else:
                # Save individual images
                for i, img_path in enumerate(translated_images):
                    output_file = output_dir / f"translated_page_{i+1:03d}.png"
                    import shutil
                    shutil.copy2(img_path, output_file)
                    output_files.append(str(output_file))
            
            return output_files
            
        except Exception as e:
            print(f"⚠️ Could not generate output files: {str(e)}")
            return []
    
    async def _images_to_pdf(self, image_paths: List[str], output_path: str) -> str:
        """Convert images to PDF."""
        try:
            from PIL import Image
            
            images = []
            for img_path in image_paths:
                img = Image.open(img_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
            
            if images:
                images[0].save(
                    output_path,
                    save_all=True,
                    append_images=images[1:],
                    format='PDF'
                )
            
            return output_path
            
        except Exception as e:
            print(f"⚠️ Could not create PDF: {str(e)}")
            return ""
    
    async def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages."""
        return settings.supported_languages
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            'session_id': self.session_id,
            'initialized': self.is_initialized,
            'agents': {
                name: agent.is_running for name, agent in self.agents.items()
            },
            'supported_languages': settings.supported_languages,
            'max_file_size_mb': settings.max_file_size_mb,
            'supported_formats': settings.supported_formats
        }


# Global orchestrator instance
orchestrator = TranslationOrchestrator()

