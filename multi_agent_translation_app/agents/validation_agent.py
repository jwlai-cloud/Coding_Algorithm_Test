"""Validation Agent for assessing translation quality and layout preservation."""

import os
import tempfile
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
from skimage.metrics import structural_similarity as ssim
from google.cloud import storage, translate_v2 as translate
from loguru import logger

from .base_agent import BaseAgent, AgentResult
from config.settings import settings, get_gcs_config


class ValidationAgent(BaseAgent):
    """
    Validation Agent assesses translation quality and layout preservation.
    
    Responsibilities:
    - Perform semantic validation through back-translation
    - Check layout consistency using image comparison
    - Verify completeness of text translation
    - Generate quality scores and issue reports
    """
    
    def __init__(self):
        super().__init__("validation_agent", "ValidationAgent")
        self.gcs_client = storage.Client()
        self.translate_client = translate.Client()
        self.gcs_config = get_gcs_config()
        self.bucket = self.gcs_client.bucket(self.gcs_config["bucket_name"])
        
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate validation input data."""
        required_fields = ["original_image_uri", "translated_image_uri"]
        return all(field in input_data for field in required_fields)
        
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process validation of translated image."""
        try:
            if not await self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    error="Invalid input data. Required: original_image_uri, translated_image_uri"
                )
                
            original_image_uri = input_data["original_image_uri"]
            translated_image_uri = input_data["translated_image_uri"]
            page_number = input_data.get("page_number", 1)
            
            self.logger.info(f"Starting validation for page {page_number}")
            
            # Download images
            original_image_path = await self.download_image(original_image_uri)
            translated_image_path = await self.download_image(translated_image_uri)
            
            # Perform validation checks
            validation_results = {}
            
            # 1. Layout Consistency Check
            layout_score = await self.check_layout_consistency(
                original_image_path, 
                translated_image_path
            )
            validation_results["layout_consistency_score"] = layout_score
            
            # 2. Structural Similarity Check
            ssim_score = await self.calculate_structural_similarity(
                original_image_path,
                translated_image_path
            )
            validation_results["structural_similarity_score"] = ssim_score
            
            # 3. Text Completeness Check (if original text is provided)
            original_text = input_data.get("original_text", "")
            translated_text = input_data.get("translated_text", "")
            
            if original_text and translated_text:
                # Semantic validation through back-translation
                semantic_score = await self.check_semantic_consistency(
                    original_text,
                    translated_text,
                    input_data.get("source_language", "en"),
                    input_data.get("target_language", "es")
                )
                validation_results["semantic_consistency_score"] = semantic_score
                
                # Text completeness check
                completeness_score = await self.check_text_completeness(
                    original_text,
                    translated_text
                )
                validation_results["text_completeness_score"] = completeness_score
            else:
                validation_results["semantic_consistency_score"] = None
                validation_results["text_completeness_score"] = None
                
            # 4. Overall Quality Assessment
            overall_quality = await self.calculate_overall_quality(validation_results)
            validation_results["overall_quality_score"] = overall_quality
            
            # 5. Generate Issues Report
            issues = await self.generate_issues_report(validation_results)
            validation_results["issues"] = issues
            
            # Clean up local files
            await self.cleanup_local_files([original_image_path, translated_image_path])
            
            # Determine if validation passed
            validation_passed = overall_quality >= settings.MIN_QUALITY_SCORE
            
            self.logger.info(f"Validation completed for page {page_number}: {overall_quality:.3f}")
            
            return AgentResult(
                success=True,
                data={
                    "quality_score": overall_quality,
                    "validation_passed": validation_passed,
                    "page_number": page_number,
                    "detailed_scores": validation_results,
                    "issues_count": len(issues)
                },
                metadata={
                    "original_image_uri": original_image_uri,
                    "translated_image_uri": translated_image_uri,
                    "validation_details": validation_results
                }
            )
            
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
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
            return temp_file.name
            
        except Exception as e:
            raise Exception(f"Image download failed: {str(e)}")
            
    async def check_layout_consistency(self, original_path: str, translated_path: str) -> float:
        """Check layout consistency between original and translated images."""
        try:
            # Load images
            original = cv2.imread(original_path)
            translated = cv2.imread(translated_path)
            
            if original is None or translated is None:
                raise Exception("Failed to load images for layout comparison")
                
            # Resize images to same dimensions if needed
            if original.shape != translated.shape:
                height, width = original.shape[:2]
                translated = cv2.resize(translated, (width, height))
                
            # Create blurred versions to focus on structure rather than text
            original_blurred = cv2.GaussianBlur(original, (15, 15), 0)
            translated_blurred = cv2.GaussianBlur(translated, (15, 15), 0)
            
            # Convert to grayscale
            original_gray = cv2.cvtColor(original_blurred, cv2.COLOR_BGR2GRAY)
            translated_gray = cv2.cvtColor(translated_blurred, cv2.COLOR_BGR2GRAY)
            
            # Calculate structural similarity
            layout_score = ssim(original_gray, translated_gray)
            
            self.logger.debug(f"Layout consistency score: {layout_score:.3f}")
            return max(0.0, layout_score)  # Ensure non-negative
            
        except Exception as e:
            self.logger.warning(f"Layout consistency check failed: {str(e)}")
            return 0.5  # Default score if check fails
            
    async def calculate_structural_similarity(self, original_path: str, translated_path: str) -> float:
        """Calculate structural similarity between images."""
        try:
            # Load images
            original = cv2.imread(original_path, cv2.IMREAD_GRAYSCALE)
            translated = cv2.imread(translated_path, cv2.IMREAD_GRAYSCALE)
            
            if original is None or translated is None:
                raise Exception("Failed to load images for SSIM calculation")
                
            # Resize to same dimensions if needed
            if original.shape != translated.shape:
                height, width = original.shape
                translated = cv2.resize(translated, (width, height))
                
            # Calculate SSIM
            ssim_score = ssim(original, translated)
            
            self.logger.debug(f"SSIM score: {ssim_score:.3f}")
            return max(0.0, ssim_score)
            
        except Exception as e:
            self.logger.warning(f"SSIM calculation failed: {str(e)}")
            return 0.5
            
    async def check_semantic_consistency(self, original_text: str, translated_text: str, 
                                       source_lang: str, target_lang: str) -> float:
        """Check semantic consistency using back-translation."""
        try:
            if not original_text.strip() or not translated_text.strip():
                return 1.0  # Perfect score if no text to validate
                
            # Perform back-translation
            back_translation_result = self.translate_client.translate(
                translated_text,
                target_language=source_lang,
                source_language=target_lang
            )
            
            back_translated_text = back_translation_result['translatedText']
            
            # Calculate semantic similarity (simplified approach)
            # In a more sophisticated implementation, you could use:
            # - Sentence embeddings (e.g., BERT, Universal Sentence Encoder)
            # - BLEU score
            # - Semantic similarity metrics
            
            semantic_score = await self.calculate_text_similarity(original_text, back_translated_text)
            
            self.logger.debug(f"Semantic consistency score: {semantic_score:.3f}")
            return semantic_score
            
        except Exception as e:
            self.logger.warning(f"Semantic consistency check failed: {str(e)}")
            return 0.7  # Default score
            
    async def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simplified implementation)."""
        try:
            # Simple word-based similarity
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 and not words2:
                return 1.0
            if not words1 or not words2:
                return 0.0
                
            # Jaccard similarity
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            similarity = intersection / union if union > 0 else 0.0
            
            # Adjust for length difference
            length_ratio = min(len(text1), len(text2)) / max(len(text1), len(text2))
            adjusted_similarity = similarity * length_ratio
            
            return min(1.0, adjusted_similarity)
            
        except Exception as e:
            self.logger.warning(f"Text similarity calculation failed: {str(e)}")
            return 0.5
            
    async def check_text_completeness(self, original_text: str, translated_text: str) -> float:
        """Check if translation is complete (no missing text blocks)."""
        try:
            if not original_text.strip():
                return 1.0  # Perfect if no original text
                
            # Simple completeness check based on text length and structure
            original_sentences = original_text.split('.')
            translated_sentences = translated_text.split('.')
            
            # Remove empty sentences
            original_sentences = [s.strip() for s in original_sentences if s.strip()]
            translated_sentences = [s.strip() for s in translated_sentences if s.strip()]
            
            if not original_sentences:
                return 1.0
                
            # Calculate completeness based on sentence count ratio
            sentence_ratio = len(translated_sentences) / len(original_sentences)
            
            # Penalize if too few or too many sentences
            if sentence_ratio < 0.8:
                completeness_score = sentence_ratio
            elif sentence_ratio > 1.2:
                completeness_score = 1.0 / sentence_ratio
            else:
                completeness_score = 1.0
                
            self.logger.debug(f"Text completeness score: {completeness_score:.3f}")
            return min(1.0, completeness_score)
            
        except Exception as e:
            self.logger.warning(f"Text completeness check failed: {str(e)}")
            return 0.8
            
    async def calculate_overall_quality(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall quality score from individual metrics."""
        try:
            scores = []
            weights = []
            
            # Layout consistency (weight: 0.3)
            if validation_results.get("layout_consistency_score") is not None:
                scores.append(validation_results["layout_consistency_score"])
                weights.append(0.3)
                
            # Structural similarity (weight: 0.2)
            if validation_results.get("structural_similarity_score") is not None:
                scores.append(validation_results["structural_similarity_score"])
                weights.append(0.2)
                
            # Semantic consistency (weight: 0.3)
            if validation_results.get("semantic_consistency_score") is not None:
                scores.append(validation_results["semantic_consistency_score"])
                weights.append(0.3)
                
            # Text completeness (weight: 0.2)
            if validation_results.get("text_completeness_score") is not None:
                scores.append(validation_results["text_completeness_score"])
                weights.append(0.2)
                
            if not scores:
                return 0.5  # Default if no scores available
                
            # Calculate weighted average
            weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
            total_weight = sum(weights)
            
            overall_score = weighted_sum / total_weight if total_weight > 0 else 0.5
            
            return min(1.0, max(0.0, overall_score))
            
        except Exception as e:
            self.logger.warning(f"Overall quality calculation failed: {str(e)}")
            return 0.5
            
    async def generate_issues_report(self, validation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a report of potential issues."""
        issues = []
        
        try:
            # Check layout consistency
            layout_score = validation_results.get("layout_consistency_score", 1.0)
            if layout_score < 0.7:
                issues.append({
                    "type": "layout_inconsistency",
                    "severity": "high" if layout_score < 0.5 else "medium",
                    "description": f"Layout consistency score is low ({layout_score:.3f})",
                    "suggestion": "Check if text positioning and visual elements are preserved"
                })
                
            # Check structural similarity
            ssim_score = validation_results.get("structural_similarity_score", 1.0)
            if ssim_score < settings.SSIM_THRESHOLD:
                issues.append({
                    "type": "structural_changes",
                    "severity": "medium",
                    "description": f"Structural similarity is below threshold ({ssim_score:.3f})",
                    "suggestion": "Verify that non-text elements are preserved"
                })
                
            # Check semantic consistency
            semantic_score = validation_results.get("semantic_consistency_score")
            if semantic_score is not None and semantic_score < 0.6:
                issues.append({
                    "type": "semantic_drift",
                    "severity": "high",
                    "description": f"Semantic consistency score is low ({semantic_score:.3f})",
                    "suggestion": "Review translation accuracy and context preservation"
                })
                
            # Check text completeness
            completeness_score = validation_results.get("text_completeness_score")
            if completeness_score is not None and completeness_score < 0.8:
                issues.append({
                    "type": "incomplete_translation",
                    "severity": "high",
                    "description": f"Text completeness score is low ({completeness_score:.3f})",
                    "suggestion": "Check if all text blocks were translated"
                })
                
            return issues
            
        except Exception as e:
            self.logger.warning(f"Issues report generation failed: {str(e)}")
            return []
            
    async def cleanup_local_files(self, file_paths: List[str]):
        """Clean up temporary local files."""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up file {file_path}: {str(e)}")
                
    def get_validation_thresholds(self) -> Dict[str, float]:
        """Get validation quality thresholds."""
        return {
            "min_overall_quality": settings.MIN_QUALITY_SCORE,
            "min_layout_consistency": 0.7,
            "min_structural_similarity": settings.SSIM_THRESHOLD,
            "min_semantic_consistency": 0.6,
            "min_text_completeness": 0.8
        }
