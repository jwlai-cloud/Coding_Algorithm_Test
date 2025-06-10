"""
Test script for the PDF Document Translator MCP Server
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from PIL import Image
import io

# Import the main functions from app.py
from app import pdf_to_images, extract_text_from_image, translate_text, document_translator

class TestPDFTranslator(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_image = Image.new('RGB', (100, 100), color='white')
        
    def test_extract_text_from_image_mock(self):
        """Test text extraction with mocked vision model"""
        with patch('app.vision_model') as mock_model:
            mock_model.return_value = [{'generated_text': 'Hello World'}]
            
            result = extract_text_from_image(self.test_image)
            self.assertEqual(result, 'Hello World')
    
    def test_translate_text_mock(self):
        """Test translation with mocked pipeline"""
        with patch('app.pipeline') as mock_pipeline:
            mock_translator = Mock()
            mock_translator.return_value = [{'translation_text': 'Hola Mundo'}]
            mock_pipeline.return_value = mock_translator
            
            result = translate_text('Hello World', 'en', 'es')
            self.assertEqual(result, 'Hola Mundo')
    
    def test_document_translator_no_file(self):
        """Test document translator with no file"""
        result = document_translator(None, 'en', 'es')
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'No PDF file uploaded')
    
    def test_document_translator_no_languages(self):
        """Test document translator with missing languages"""
        mock_file = Mock()
        mock_file.name = 'test.pdf'
        
        result = document_translator(mock_file, '', 'es')
        self.assertIn('error', result)
        
        result = document_translator(mock_file, 'en', '')
        self.assertIn('error', result)
    
    @patch('app.pdf_to_images')
    @patch('app.extract_text_from_image')
    @patch('app.translate_text')
    def test_document_translator_success(self, mock_translate, mock_extract, mock_pdf_to_images):
        """Test successful document translation"""
        # Mock the functions
        mock_pdf_to_images.return_value = [self.test_image]
        mock_extract.return_value = 'Hello World'
        mock_translate.return_value = 'Hola Mundo'
        
        mock_file = Mock()
        mock_file.name = 'test.pdf'
        
        result = document_translator(mock_file, 'en', 'es')
        
        # Check the structure
        self.assertIn('total_pages', result)
        self.assertIn('pages', result)
        self.assertEqual(result['total_pages'], 1)
        self.assertEqual(len(result['pages']), 1)
        
        page = result['pages'][0]
        self.assertEqual(page['page_number'], 1)
        self.assertEqual(page['original_text'], 'Hello World')
        self.assertEqual(page['translated_text'], 'Hola Mundo')
        self.assertEqual(page['status'], 'completed')

class TestLanguageSupport(unittest.TestCase):
    """Test language support functionality"""
    
    def test_language_codes(self):
        """Test that language codes are properly defined"""
        from app import LANGUAGE_OPTIONS
        
        # Check that we have the expected languages
        language_codes = [code for _, code in LANGUAGE_OPTIONS]
        
        expected_codes = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi']
        
        for code in expected_codes:
            self.assertIn(code, language_codes)

class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios"""
    
    def test_pdf_to_images_invalid_file(self):
        """Test PDF to images with invalid file"""
        result = pdf_to_images(None)
        self.assertEqual(result, [])
    
    def test_extract_text_no_model(self):
        """Test text extraction when model is not available"""
        with patch('app.vision_model', None):
            result = extract_text_from_image(Image.new('RGB', (100, 100)))
            self.assertIn('Vision model not available', result)

def run_integration_test():
    """Run a simple integration test"""
    print("Running integration test...")
    
    # Test the Gradio interface creation
    try:
        from app import demo
        print("✅ Gradio interface created successfully")
        
        # Test that the interface has the right components
        assert demo.fn == document_translator
        print("✅ Interface function is correctly set")
        
        # Test that inputs are properly configured
        assert len(demo.input_components) == 3
        print("✅ Input components configured correctly")
        
        print("🎉 Integration test passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")

if __name__ == '__main__':
    print("=== PDF Document Translator Tests ===\n")
    
    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "="*50 + "\n")
    
    # Run integration test
    run_integration_test()

