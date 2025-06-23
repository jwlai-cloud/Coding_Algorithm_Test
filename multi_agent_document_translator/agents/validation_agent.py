"""Quality Validation Agent for translation results."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

import cv2
import numpy as np
from PIL import Image
import google.generativeai as genai

from .base_agent import BaseAgent, AgentResult


class ValidationAgent(BaseAgent):
    """Agent responsible for validating translation quality and layout preservation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("validator", config)
        self.model = None
        self.temp_dir = None
    
    async def _initialize(self):
        """Initialize the validation agent."""
        self.temp_dir = self._create_temp_dir()
        
        # Configure Gemini API for validation
        api_key = self.config.get('gemini_api_key')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro-vision')
        
        self.logger.info("Validation agent initialized")
    
    async def _cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
        self.logger.info("Validation agent cleaned up")
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Validate translation quality and layout preservation."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate input
            required_fields = ['original_images', 'translated_images', 'translation_metadata']
            if not self._validate_input(input_data, required_fields):
                return AgentResult(
                    success=False,
                    error="Missing required fields for validation"
                )
            
            original_images = input_data['original_images']
            translated_images = input_data['translated_images']
            translation_metadata = input_data['translation_metadata']
            target_language = input_data.get('target_language', 'unknown')
            
            if len(original_images) != len(translated_images):
                return AgentResult(
                    success=False,
                    error="Mismatch between original and translated image counts"
                )
            
            # Validate each page
            validation_results = []
            overall_scores = {
                'layout_preservation': [],
                'translation_quality': [],
                'visual_similarity': [],
                'text_completeness': []
            }
            
            for i, (orig_path, trans_path) in enumerate(zip(original_images, translated_images)):
                self.logger.info(f"Validating page {i+1}/{len(original_images)}")
                
                page_result = await self._validate_page(
                    orig_path, 
                    trans_path, 
                    translation_metadata[i] if i < len(translation_metadata) else {},
                    target_language,
                    page_number=i+1
                )
                
                validation_results.append(page_result)
                
                # Collect scores for overall assessment
                if page_result['success']:
                    scores = page_result['scores']
                    for metric, score in scores.items():
                        if metric in overall_scores:
                            overall_scores[metric].append(score)
            
            # Calculate overall scores
            final_scores = {}
            for metric, scores in overall_scores.items():
                if scores:
                    final_scores[metric] = {
                        'average': sum(scores) / len(scores),
                        'min': min(scores),
                        'max': max(scores),
                        'scores_per_page': scores
                    }
            
            # Determine overall quality assessment
            quality_assessment = self._assess_overall_quality(final_scores)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return AgentResult(
                success=True,
                data={
                    'validation_results': validation_results,
                    'overall_scores': final_scores,
                    'quality_assessment': quality_assessment,
                    'recommendations': self._generate_recommendations(final_scores, validation_results),
                    'page_count': len(validation_results)
                },
                metadata={
                    'agent_id': self.agent_id,
                    'validation_method': 'multimodal_analysis',
                    'target_language': target_language
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Error in validation process: {str(e)}")
            return AgentResult(
                success=False,
                error=f"Validation process failed: {str(e)}"
            )
    
    async def _validate_page(self, original_path: str, translated_path: str, 
                           metadata: Dict[str, Any], target_language: str, 
                           page_number: int) -> Dict[str, Any]:
        """Validate a single page translation."""
        try:
            # Load images
            original_img = cv2.imread(original_path)
            translated_img = cv2.imread(translated_path)
            
            if original_img is None or translated_img is None:
                return {
                    'success': False,
                    'error': 'Could not load images for validation',
                    'page_number': page_number
                }
            
            # Perform various validation checks
            layout_score = await self._check_layout_preservation(original_img, translated_img)
            visual_similarity = await self._check_visual_similarity(original_img, translated_img)
            text_completeness = await self._check_text_completeness(original_path, translated_path, metadata)
            
            # Use Gemini for translation quality assessment if available
            translation_quality = 0.8  # Default score
            if self.model:
                translation_quality = await self._assess_translation_quality(
                    original_path, translated_path, target_language
                )
            
            scores = {
                'layout_preservation': layout_score,
                'visual_similarity': visual_similarity,
                'text_completeness': text_completeness,
                'translation_quality': translation_quality
            }
            
            # Calculate overall page score
            overall_score = sum(scores.values()) / len(scores)
            
            return {
                'success': True,
                'page_number': page_number,
                'scores': scores,
                'overall_score': overall_score,
                'passed_validation': overall_score >= self.config.get('min_confidence', 0.8),
                'issues': self._identify_issues(scores),
                'metadata': metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error validating page {page_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'page_number': page_number
            }
    
    async def _check_layout_preservation(self, original_img: np.ndarray, 
                                       translated_img: np.ndarray) -> float:
        """Check how well the layout is preserved."""
        try:
            # Convert to grayscale
            orig_gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
            trans_gray = cv2.cvtColor(translated_img, cv2.COLOR_BGR2GRAY)
            
            # Resize images to same size if different
            if orig_gray.shape != trans_gray.shape:
                trans_gray = cv2.resize(trans_gray, (orig_gray.shape[1], orig_gray.shape[0]))
            
            # Use structural similarity index
            from skimage.metrics import structural_similarity as ssim
            similarity_score = ssim(orig_gray, trans_gray)
            
            # Convert to 0-1 scale where 1 is perfect preservation
            layout_score = max(0, similarity_score)
            
            return layout_score
            
        except Exception as e:
            self.logger.warning(f"Could not calculate layout preservation: {str(e)}")
            return 0.5  # Default moderate score
    
    async def _check_visual_similarity(self, original_img: np.ndarray, 
                                     translated_img: np.ndarray) -> float:
        """Check visual similarity between original and translated images."""
        try:
            # Calculate histogram similarity
            orig_hist = cv2.calcHist([original_img], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
            trans_hist = cv2.calcHist([translated_img], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
            
            # Compare histograms
            similarity = cv2.compareHist(orig_hist, trans_hist, cv2.HISTCMP_CORREL)
            
            # Normalize to 0-1 scale
            visual_score = max(0, min(1, similarity))
            
            return visual_score
            
        except Exception as e:
            self.logger.warning(f"Could not calculate visual similarity: {str(e)}")
            return 0.7  # Default good score
    
    async def _check_text_completeness(self, original_path: str, translated_path: str, 
                                     metadata: Dict[str, Any]) -> float:
        """Check if all text elements were translated."""
        try:
            # This is a simplified check based on metadata
            # In production, you'd want more sophisticated text detection and comparison
            
            if 'translation_response' in metadata:
                response = metadata['translation_response']
                
                # Check for indicators of complete translation
                completeness_indicators = [
                    'original text:' in response.lower(),
                    'translated text:' in response.lower(),
                    len(response) > 50,  # Reasonable response length
                    'position:' in response.lower() or 'location:' in response.lower()
                ]
                
                completeness_score = sum(completeness_indicators) / len(completeness_indicators)
                return completeness_score
            
            return 0.6  # Default moderate score if no metadata
            
        except Exception as e:
            self.logger.warning(f"Could not check text completeness: {str(e)}")
            return 0.6
    
    async def _assess_translation_quality(self, original_path: str, translated_path: str, 
                                        target_language: str) -> float:
        """Use Gemini to assess translation quality."""
        try:
            if not self.model:
                return 0.8  # Default score if no model available
            
            # Load images
            original_img = Image.open(original_path)
            translated_img = Image.open(translated_path)
            
            prompt = f"""
            Please assess the quality of this document translation to {target_language}.
            
            Compare the original image (first) with the translated image (second) and evaluate:
            1. Translation accuracy and appropriateness
            2. Preservation of document structure and layout
            3. Completeness of translation (all text translated)
            4. Professional quality and readability
            
            Provide a quality score from 0.0 to 1.0 where:
            - 1.0 = Perfect translation with excellent layout preservation
            - 0.8-0.9 = High quality with minor issues
            - 0.6-0.7 = Good quality with some noticeable issues
            - 0.4-0.5 = Moderate quality with significant issues
            - 0.0-0.3 = Poor quality with major problems
            
            Please provide just the numerical score followed by a brief explanation.
            """
            
            response = self.model.generate_content([prompt, original_img, translated_img])
            
            if response and response.text:
                # Extract numerical score from response
                score = self._extract_score_from_response(response.text)
                return score
            
            return 0.8  # Default score
            
        except Exception as e:
            self.logger.warning(f"Could not assess translation quality with Gemini: {str(e)}")
            return 0.8
    
    def _extract_score_from_response(self, response: str) -> float:
        """Extract numerical score from Gemini response."""
        try:
            import re
            
            # Look for decimal numbers between 0 and 1
            matches = re.findall(r'0\.\d+|1\.0+|1', response)
            
            for match in matches:
                score = float(match)
                if 0.0 <= score <= 1.0:
                    return score
            
            # If no valid score found, try to infer from text
            response_lower = response.lower()
            if 'excellent' in response_lower or 'perfect' in response_lower:
                return 0.9
            elif 'good' in response_lower or 'high quality' in response_lower:
                return 0.8
            elif 'moderate' in response_lower or 'average' in response_lower:
                return 0.6
            elif 'poor' in response_lower or 'low quality' in response_lower:
                return 0.4
            
            return 0.7  # Default moderate score
            
        except Exception as e:
            self.logger.warning(f"Could not extract score from response: {str(e)}")
            return 0.7
    
    def _identify_issues(self, scores: Dict[str, float]) -> List[str]:
        """Identify specific issues based on scores."""
        issues = []
        threshold = 0.7
        
        if scores.get('layout_preservation', 1.0) < threshold:
            issues.append("Layout preservation below acceptable threshold")
        
        if scores.get('visual_similarity', 1.0) < threshold:
            issues.append("Significant visual differences detected")
        
        if scores.get('text_completeness', 1.0) < threshold:
            issues.append("Possible incomplete text translation")
        
        if scores.get('translation_quality', 1.0) < threshold:
            issues.append("Translation quality concerns identified")
        
        return issues
    
    def _assess_overall_quality(self, final_scores: Dict[str, Dict]) -> Dict[str, Any]:
        """Assess overall translation quality."""
        if not final_scores:
            return {
                'grade': 'Unknown',
                'description': 'Insufficient data for assessment',
                'pass': False
            }
        
        # Calculate weighted average
        weights = {
            'layout_preservation': 0.3,
            'translation_quality': 0.4,
            'visual_similarity': 0.2,
            'text_completeness': 0.1
        }
        
        weighted_score = 0
        total_weight = 0
        
        for metric, weight in weights.items():
            if metric in final_scores and 'average' in final_scores[metric]:
                weighted_score += final_scores[metric]['average'] * weight
                total_weight += weight
        
        if total_weight > 0:
            overall_score = weighted_score / total_weight
        else:
            overall_score = 0.5
        
        # Determine grade
        if overall_score >= 0.9:
            grade = 'Excellent'
            description = 'Outstanding translation with excellent layout preservation'
        elif overall_score >= 0.8:
            grade = 'Good'
            description = 'High-quality translation with good layout preservation'
        elif overall_score >= 0.7:
            grade = 'Satisfactory'
            description = 'Acceptable translation with moderate layout preservation'
        elif overall_score >= 0.6:
            grade = 'Needs Improvement'
            description = 'Translation quality or layout preservation needs improvement'
        else:
            grade = 'Poor'
            description = 'Significant issues with translation quality or layout preservation'
        
        return {
            'grade': grade,
            'description': description,
            'overall_score': overall_score,
            'pass': overall_score >= self.config.get('min_confidence', 0.8)
        }
    
    def _generate_recommendations(self, final_scores: Dict[str, Dict], 
                                validation_results: List[Dict]) -> List[str]:
        """Generate recommendations for improvement."""
        recommendations = []
        
        # Check for consistent issues across pages
        layout_issues = sum(1 for result in validation_results 
                          if result.get('success') and 
                          result.get('scores', {}).get('layout_preservation', 1.0) < 0.7)
        
        if layout_issues > len(validation_results) * 0.5:
            recommendations.append("Consider improving layout preservation algorithms")
        
        # Check translation quality
        if 'translation_quality' in final_scores:
            avg_quality = final_scores['translation_quality'].get('average', 1.0)
            if avg_quality < 0.8:
                recommendations.append("Review translation prompts and model parameters")
        
        # Check for specific page issues
        problematic_pages = [result['page_number'] for result in validation_results 
                           if result.get('success') and result.get('overall_score', 1.0) < 0.7]
        
        if problematic_pages:
            recommendations.append(f"Review pages {', '.join(map(str, problematic_pages))} for specific issues")
        
        if not recommendations:
            recommendations.append("Translation quality meets standards")
        
        return recommendations

