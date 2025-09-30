"""
Quality scoring for uploaded medical documents
"""

from typing import Dict, Any, List
import re


class QualityScorer:
    """Score the quality of medical documents"""
    
    def __init__(self):
        # Medical keywords that indicate high-quality content
        self.medical_keywords = [
            "diagnosis", "treatment", "medication", "symptoms", "patient",
            "medical", "health", "clinical", "therapy", "prescription",
            "disease", "condition", "procedure", "surgery", "hospital"
        ]
        
        # Hong Kong medical terms
        self.hk_medical_terms = [
            "醫院", "診所", "醫生", "病人", "治療", "藥物", "症狀", "診斷"
        ]
    
    async def score_content(
        self, 
        content: str,
        document_type: str = "general",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Score the quality of medical content
        
        Args:
            content: Text content to score
            document_type: Type of document
            **kwargs: Additional scoring parameters
        
        Returns:
            Dict containing quality score and details
        """
        try:
            if not content or len(content.strip()) < 10:
                return {
                    "score": 0.0,
                    "max_score": 100.0,
                    "details": {
                        "length_score": 0,
                        "medical_content_score": 0,
                        "structure_score": 0,
                        "language_score": 0
                    },
                    "recommendations": ["Content is too short or empty"]
                }
            
            # Calculate different quality metrics
            length_score = self._score_length(content)
            medical_score = self._score_medical_content(content)
            structure_score = self._score_structure(content)
            language_score = self._score_language(content)
            
            # Weighted total score
            total_score = (
                length_score * 0.2 +
                medical_score * 0.4 +
                structure_score * 0.2 +
                language_score * 0.2
            )
            
            recommendations = self._generate_recommendations(
                length_score, medical_score, structure_score, language_score
            )
            
            return {
                "score": round(total_score, 2),
                "max_score": 100.0,
                "details": {
                    "length_score": length_score,
                    "medical_content_score": medical_score,
                    "structure_score": structure_score,
                    "language_score": language_score
                },
                "recommendations": recommendations
            }
            
        except Exception as e:
            return {
                "score": 0.0,
                "max_score": 100.0,
                "error": str(e),
                "details": {},
                "recommendations": ["Error occurred during scoring"]
            }
    
    def _score_length(self, content: str) -> float:
        """Score based on content length"""
        length = len(content.strip())
        if length < 50:
            return 20.0
        elif length < 200:
            return 50.0
        elif length < 500:
            return 75.0
        else:
            return 100.0
    
    def _score_medical_content(self, content: str) -> float:
        """Score based on medical content relevance"""
        content_lower = content.lower()
        
        # Count English medical keywords
        en_matches = sum(1 for keyword in self.medical_keywords if keyword in content_lower)
        
        # Count Chinese medical terms
        zh_matches = sum(1 for term in self.hk_medical_terms if term in content)
        
        total_matches = en_matches + zh_matches
        
        if total_matches == 0:
            return 20.0
        elif total_matches <= 2:
            return 50.0
        elif total_matches <= 5:
            return 75.0
        else:
            return 100.0
    
    def _score_structure(self, content: str) -> float:
        """Score based on document structure"""
        lines = content.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        # Check for basic structure indicators
        has_headings = any(line.isupper() or line.startswith('#') for line in non_empty_lines)
        has_lists = any(line.strip().startswith(('-', '*', '•', '1.', '2.')) for line in lines)
        has_paragraphs = len(non_empty_lines) > 3
        
        structure_score = 0
        if has_headings:
            structure_score += 40
        if has_lists:
            structure_score += 30
        if has_paragraphs:
            structure_score += 30
        
        return min(structure_score, 100.0)
    
    def _score_language(self, content: str) -> float:
        """Score based on language quality"""
        # Basic language quality indicators
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) < 2:
            return 30.0
        
        # Check for proper sentence structure
        proper_sentences = 0
        for sentence in sentences:
            if len(sentence.split()) >= 3:  # At least 3 words
                proper_sentences += 1
        
        sentence_ratio = proper_sentences / len(sentences)
        return min(sentence_ratio * 100, 100.0)
    
    def _generate_recommendations(
        self, 
        length_score: float, 
        medical_score: float, 
        structure_score: float,
        language_score: float
    ) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if length_score < 50:
            recommendations.append("Content appears too short. Consider adding more detailed information.")
        
        if medical_score < 50:
            recommendations.append("Content lacks medical terminology. Ensure it's relevant to healthcare.")
        
        if structure_score < 50:
            recommendations.append("Improve document structure with headings, lists, or clear paragraphs.")
        
        if language_score < 50:
            recommendations.append("Improve language quality with clearer, more complete sentences.")
        
        if not recommendations:
            recommendations.append("Content quality is good!")
        
        return recommendations
















