"""Tests for the multi-agent system."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import os

from agents import DocumentConverterAgent, TranslationAgent, ValidationAgent
from config import get_agent_config


class TestDocumentConverterAgent:
    """Test the document converter agent."""
    
    @pytest.fixture
    async def agent(self):
        """Create a document converter agent for testing."""
        config = get_agent_config('document_converter')
        agent = DocumentConverterAgent(config)
        await agent.start()
        yield agent
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "document_converter"
        assert agent.is_running
    
    @pytest.mark.asyncio
    async def test_invalid_document_path(self, agent):
        """Test handling of invalid document path."""
        result = await agent.process({
            'document_path': 'nonexistent_file.pdf'
        })
        
        assert not result.success
        assert 'not found' in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_missing_document_path(self, agent):
        """Test handling of missing document path."""
        result = await agent.process({})
        
        assert not result.success
        assert 'missing required field' in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_text_to_image_conversion(self, agent):
        """Test text file to image conversion."""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document.\nWith multiple lines.\nFor testing purposes.")
            temp_path = f.name
        
        try:
            result = await agent.process({
                'document_path': temp_path
            })
            
            assert result.success
            assert 'images' in result.data
            assert len(result.data['images']) > 0
            assert result.data['page_count'] > 0
            
            # Check that image files exist
            for image_path in result.data['images']:
                assert os.path.exists(image_path)
        
        finally:
            # Clean up
            os.unlink(temp_path)


class TestTranslationAgent:
    """Test the translation agent."""
    
    @pytest.fixture
    async def agent(self):
        """Create a translation agent for testing."""
        config = get_agent_config('translator')
        # Skip if no API key is available
        if not config.get('gemini_api_key'):
            pytest.skip("Gemini API key not available")
        
        agent = TranslationAgent(config)
        await agent.start()
        yield agent
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "translator"
        assert agent.is_running
        assert agent.model is not None
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, agent):
        """Test handling of missing required fields."""
        result = await agent.process({})
        
        assert not result.success
        assert 'missing required fields' in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_unsupported_language(self, agent):
        """Test handling of unsupported target language."""
        result = await agent.process({
            'images': ['test_image.png'],
            'target_language': 'xyz'  # Invalid language code
        })
        
        assert not result.success
        assert 'unsupported target language' in result.error.lower()


class TestValidationAgent:
    """Test the validation agent."""
    
    @pytest.fixture
    async def agent(self):
        """Create a validation agent for testing."""
        config = get_agent_config('validator')
        agent = ValidationAgent(config)
        await agent.start()
        yield agent
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "validator"
        assert agent.is_running
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, agent):
        """Test handling of missing required fields."""
        result = await agent.process({})
        
        assert not result.success
        assert 'missing required fields' in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_image_count_mismatch(self, agent):
        """Test handling of mismatched image counts."""
        result = await agent.process({
            'original_images': ['image1.png', 'image2.png'],
            'translated_images': ['image1_trans.png'],  # Different count
            'translation_metadata': [{}]
        })
        
        assert not result.success
        assert 'mismatch' in result.error.lower()


@pytest.mark.asyncio
async def test_agent_communication():
    """Test basic agent communication."""
    config = get_agent_config('document_converter')
    agent = DocumentConverterAgent(config)
    
    await agent.start()
    
    try:
        # Test message sending (basic functionality)
        await agent.send_message(
            target_agent="test_agent",
            message_type="test_message",
            content={"test": "data"}
        )
        
        # This is a basic test - in a full implementation,
        # you'd test actual message delivery and processing
        
    finally:
        await agent.stop()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

