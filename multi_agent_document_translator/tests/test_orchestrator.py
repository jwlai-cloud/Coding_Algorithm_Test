"""Tests for the translation orchestrator."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import os

from orchestrator import TranslationOrchestrator
from config import settings


class TestTranslationOrchestrator:
    """Test the translation orchestrator."""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create an orchestrator for testing."""
        orch = TranslationOrchestrator()
        yield orch
        if orch.is_initialized:
            await orch.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert not orchestrator.is_initialized
        
        # Skip if no API key is available
        if not settings.gemini_api_key:
            pytest.skip("Gemini API key not available")
        
        await orchestrator.initialize()
        
        assert orchestrator.is_initialized
        assert len(orchestrator.agents) == 3
        assert 'converter' in orchestrator.agents
        assert 'translator' in orchestrator.agents
        assert 'validator' in orchestrator.agents
    
    @pytest.mark.asyncio
    async def test_shutdown(self, orchestrator):
        """Test orchestrator shutdown."""
        if not settings.gemini_api_key:
            pytest.skip("Gemini API key not available")
        
        await orchestrator.initialize()
        assert orchestrator.is_initialized
        
        await orchestrator.shutdown()
        assert not orchestrator.is_initialized
    
    @pytest.mark.asyncio
    async def test_get_supported_languages(self, orchestrator):
        """Test getting supported languages."""
        languages = await orchestrator.get_supported_languages()
        
        assert isinstance(languages, dict)
        assert 'en' in languages
        assert 'es' in languages
        assert languages['en'] == 'English'
    
    @pytest.mark.asyncio
    async def test_get_system_status(self, orchestrator):
        """Test getting system status."""
        status = await orchestrator.get_system_status()
        
        assert isinstance(status, dict)
        assert 'session_id' in status
        assert 'initialized' in status
        assert 'agents' in status
        assert 'supported_languages' in status
    
    @pytest.mark.asyncio
    async def test_translate_nonexistent_document(self, orchestrator):
        """Test translation with nonexistent document."""
        if not settings.gemini_api_key:
            pytest.skip("Gemini API key not available")
        
        result = await orchestrator.translate_document(
            document_path="nonexistent_file.pdf",
            target_language="es"
        )
        
        assert not result['success']
        assert 'not found' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_translate_unsupported_language(self, orchestrator):
        """Test translation with unsupported language."""
        if not settings.gemini_api_key:
            pytest.skip("Gemini API key not available")
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test document content")
            temp_path = f.name
        
        try:
            result = await orchestrator.translate_document(
                document_path=temp_path,
                target_language="xyz"  # Invalid language
            )
            
            assert not result['success']
            assert 'unsupported' in result['error'].lower()
        
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_translate_text_document(self, orchestrator):
        """Test translation of a simple text document."""
        if not settings.gemini_api_key:
            pytest.skip("Gemini API key not available")
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello world!\nThis is a test document.\nIt has multiple lines.")
            temp_path = f.name
        
        try:
            await orchestrator.initialize()
            
            result = await orchestrator.translate_document(
                document_path=temp_path,
                target_language="es",
                source_language="en"
            )
            
            # The translation might fail due to API limitations in testing,
            # but we can at least test the structure
            assert 'success' in result
            assert 'translation_id' in result
            assert 'session_id' in result
            assert 'processing_time' in result
            
            if result['success']:
                assert 'page_count' in result
                assert 'original_images' in result
                assert 'translated_images' in result
                assert 'validation' in result
        
        finally:
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_multiple_orchestrator_instances():
    """Test that multiple orchestrator instances work independently."""
    orch1 = TranslationOrchestrator()
    orch2 = TranslationOrchestrator()
    
    # They should have different session IDs
    assert orch1.session_id != orch2.session_id
    
    # Test status without initialization
    status1 = await orch1.get_system_status()
    status2 = await orch2.get_system_status()
    
    assert status1['session_id'] != status2['session_id']
    assert not status1['initialized']
    assert not status2['initialized']


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

