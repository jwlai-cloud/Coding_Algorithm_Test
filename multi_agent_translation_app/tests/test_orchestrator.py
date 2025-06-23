"""Tests for the Orchestrator Agent."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from agents.orchestrator_agent import OrchestratorAgent, TranslationJob
from agents.base_agent import AgentResult


class TestOrchestratorAgent:
    """Test cases for OrchestratorAgent."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing."""
        return OrchestratorAgent()
        
    @pytest.mark.asyncio
    async def test_validate_input_valid(self, orchestrator):
        """Test input validation with valid data."""
        input_data = {
            "document_path": "gs://bucket/document.pdf",
            "target_language": "es"
        }
        
        result = await orchestrator.validate_input(input_data)
        assert result is True
        
    @pytest.mark.asyncio
    async def test_validate_input_invalid(self, orchestrator):
        """Test input validation with invalid data."""
        input_data = {
            "document_path": "gs://bucket/document.pdf"
            # Missing target_language
        }
        
        result = await orchestrator.validate_input(input_data)
        assert result is False
        
    @pytest.mark.asyncio
    async def test_detect_language(self, orchestrator):
        """Test language detection."""
        with patch.object(orchestrator.translate_client, 'detect_language') as mock_detect:
            mock_detect.return_value = {"language": "en", "confidence": 0.95}
            
            result = await orchestrator.detect_language("test_document.pdf")
            assert result == "en"
            
    @pytest.mark.asyncio
    async def test_detect_language_fallback(self, orchestrator):
        """Test language detection fallback on error."""
        with patch.object(orchestrator.translate_client, 'detect_language') as mock_detect:
            mock_detect.side_effect = Exception("API Error")
            
            result = await orchestrator.detect_language("test_document.pdf")
            assert result == "en"  # Default fallback
            
    @pytest.mark.asyncio
    async def test_process_success(self, orchestrator):
        """Test successful document processing."""
        input_data = {
            "document_path": "gs://bucket/test.pdf",
            "target_language": "es",
            "job_id": "test_job_123"
        }
        
        # Mock agent invocations
        with patch.object(orchestrator, 'invoke_conversion_agent') as mock_conversion, \
             patch.object(orchestrator, 'invoke_translation_agent') as mock_translation, \
             patch.object(orchestrator, 'invoke_validation_agent') as mock_validation, \
             patch.object(orchestrator, 'assemble_final_document') as mock_assembly:
            
            # Setup mocks
            mock_conversion.return_value = AgentResult(
                success=True,
                data={"page_images": ["gs://bucket/page1.png", "gs://bucket/page2.png"]}
            )
            
            mock_translation.return_value = AgentResult(
                success=True,
                data={"translated_image_uri": "gs://bucket/translated_page.png"}
            )
            
            mock_validation.return_value = AgentResult(
                success=True,
                data={"quality_score": 0.85}
            )
            
            mock_assembly.return_value = AgentResult(
                success=True,
                data={"output_document_uri": "gs://bucket/final.pdf"}
            )
            
            result = await orchestrator.process(input_data)
            
            assert result.success is True
            assert result.data["job_id"] == "test_job_123"
            assert result.data["status"] == "completed"
            assert "output_document" in result.data
            
    @pytest.mark.asyncio
    async def test_process_conversion_failure(self, orchestrator):
        """Test handling of conversion agent failure."""
        input_data = {
            "document_path": "gs://bucket/test.pdf",
            "target_language": "es"
        }
        
        with patch.object(orchestrator, 'invoke_conversion_agent') as mock_conversion:
            mock_conversion.return_value = AgentResult(
                success=False,
                error="Conversion failed"
            )
            
            result = await orchestrator.process(input_data)
            
            assert result.success is False
            assert "Conversion failed" in result.error
            
    def test_get_job_status(self, orchestrator):
        """Test job status retrieval."""
        job = TranslationJob(
            job_id="test_job",
            document_path="test.pdf",
            target_language="es"
        )
        orchestrator.active_jobs["test_job"] = job
        
        retrieved_job = orchestrator.get_job_status("test_job")
        assert retrieved_job == job
        
        # Test non-existent job
        non_existent = orchestrator.get_job_status("non_existent")
        assert non_existent is None
        
    def test_list_active_jobs(self, orchestrator):
        """Test listing active jobs."""
        job1 = TranslationJob(job_id="job1", document_path="doc1.pdf", target_language="es")
        job2 = TranslationJob(job_id="job2", document_path="doc2.pdf", target_language="fr")
        
        orchestrator.active_jobs["job1"] = job1
        orchestrator.active_jobs["job2"] = job2
        
        jobs = orchestrator.list_active_jobs()
        assert len(jobs) == 2
        assert job1 in jobs
        assert job2 in jobs

