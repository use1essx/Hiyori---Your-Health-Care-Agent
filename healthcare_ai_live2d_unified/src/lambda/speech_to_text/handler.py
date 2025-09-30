"""
Speech-to-Text Lambda Function
=============================

AWS Lambda handler for converting speech to text using AWS Transcribe.
Supports Traditional Chinese and English with healthcare-optimized vocabulary.
"""

import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid
import base64
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
transcribe = boto3.client('transcribe')
s3 = boto3.client('s3')

# Environment variables
AUDIO_BUCKET = os.environ.get('AUDIO_BUCKET')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')


class SpeechToTextProcessor:
    """Processes speech-to-text conversion with healthcare optimization."""
    
    def __init__(self):
        self.transcribe_client = transcribe
        self.s3_client = s3
        
        # Supported languages with healthcare vocabulary
        self.language_configs = {
            'zh-HK': {
                'language_code': 'zh-CN',  # Use zh-CN as closest match for Traditional Chinese
                'vocabulary_name': 'HealthcareVocabulary-ZH',
                'medical_vocabulary': [
                    '糖尿病', '高血壓', '心臟病', '關節炎', '哮喘', '慢性阻塞性肺病',
                    '頭痛', '胸痛', '呼吸困難', '頭暈', '噁心', '嘔吐', '發燒', '咳嗽',
                    '藥物', '處方', '副作用', '劑量', '血壓', '血糖', '膽固醇',
                    '急症室', '醫院管理局', '家庭醫生', '專科醫生', '護士', '藥劑師',
                    '撒瑪利亞會', '緊急', '救命', '不舒服', '痛', '攰', '擔心'
                ]
            },
            'en-US': {
                'language_code': 'en-US',
                'vocabulary_name': 'HealthcareVocabulary-EN',
                'medical_vocabulary': [
                    'diabetes', 'hypertension', 'heart disease', 'arthritis', 'asthma', 'COPD',
                    'headache', 'chest pain', 'difficulty breathing', 'dizziness', 'nausea', 'vomiting',
                    'fever', 'cough', 'medication', 'prescription', 'side effects', 'dosage',
                    'blood pressure', 'blood sugar', 'cholesterol', 'emergency room', 'hospital',
                    'family doctor', 'specialist', 'nurse', 'pharmacist', 'Samaritans', 'emergency',
                    'help me', 'uncomfortable', 'pain', 'tired', 'worried', 'stressed', 'anxious'
                ]
            }
        }
    
    def detect_language(self, audio_metadata: Dict[str, Any]) -> str:
        """Detect language from audio metadata or user preferences."""
        # Check user preference first
        user_language = audio_metadata.get('language_preference', 'zh-HK')
        
        # Map common language codes
        language_mapping = {
            'zh': 'zh-HK',
            'zh-TW': 'zh-HK',
            'zh-HK': 'zh-HK',
            'zh-CN': 'zh-HK',  # Use HK config for all Chinese variants
            'en': 'en-US',
            'en-US': 'en-US',
            'en-GB': 'en-US'
        }
        
        return language_mapping.get(user_language, 'zh-HK')
    
    def create_custom_vocabulary(self, language: str) -> Optional[str]:
        """Create or update custom medical vocabulary for better accuracy."""
        if language not in self.language_configs:
            return None
        
        config = self.language_configs[language]
        vocabulary_name = config['vocabulary_name']
        
        try:
            # Check if vocabulary already exists
            try:
                response = self.transcribe_client.get_vocabulary(VocabularyName=vocabulary_name)
                if response['VocabularyState'] == 'READY':
                    logger.info(f"Using existing vocabulary: {vocabulary_name}")
                    return vocabulary_name
            except self.transcribe_client.exceptions.NotFoundException:
                pass
            
            # Create new vocabulary
            vocabulary_content = '\n'.join(config['medical_vocabulary'])
            
            self.transcribe_client.create_vocabulary(
                VocabularyName=vocabulary_name,
                LanguageCode=config['language_code'],
                Phrases=config['medical_vocabulary']
            )
            
            logger.info(f"Created custom vocabulary: {vocabulary_name}")
            return vocabulary_name
            
        except Exception as e:
            logger.warning(f"Failed to create vocabulary {vocabulary_name}: {e}")
            return None
    
    def start_transcription_job(self, audio_uri: str, job_name: str, 
                              language: str, vocabulary_name: Optional[str] = None) -> Dict[str, Any]:
        """Start AWS Transcribe job with healthcare optimizations."""
        config = self.language_configs.get(language, self.language_configs['zh-HK'])
        
        job_params = {
            'TranscriptionJobName': job_name,
            'LanguageCode': config['language_code'],
            'Media': {'MediaFileUri': audio_uri},
            'OutputBucketName': AUDIO_BUCKET,
            'OutputKey': f'transcriptions/{job_name}.json',
            'Settings': {
                'ShowSpeakerLabels': False,  # Single speaker for healthcare conversations
                'MaxSpeakerLabels': 1,
                'ChannelIdentification': False,
                'ShowAlternatives': True,
                'MaxAlternatives': 3,
                'VocabularyFilterMethod': 'remove'  # Remove profanity
            }
        }
        
        # Add custom vocabulary if available
        if vocabulary_name:
            job_params['Settings']['VocabularyName'] = vocabulary_name
        
        # Healthcare-specific settings
        if language == 'zh-HK':
            # Chinese-specific optimizations
            job_params['Settings']['VocabularyFilterName'] = 'HealthcareFilter-ZH'
        else:
            # English-specific optimizations
            job_params['Settings']['VocabularyFilterName'] = 'HealthcareFilter-EN'
        
        try:
            response = self.transcribe_client.start_transcription_job(**job_params)
            
            return {
                'job_name': job_name,
                'job_status': response['TranscriptionJob']['TranscriptionJobStatus'],
                'language_code': config['language_code'],
                'created_at': datetime.utcnow().isoformat(),
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to start transcription job: {e}")
            raise
    
    def get_transcription_result(self, job_name: str) -> Dict[str, Any]:
        """Get transcription result and process for healthcare context."""
        try:
            response = self.transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            job = response['TranscriptionJob']
            status = job['TranscriptionJobStatus']
            
            if status == 'COMPLETED':
                # Download transcription result
                transcript_uri = job['Transcript']['TranscriptFileUri']
                transcript_data = self._download_transcript(transcript_uri)
                
                # Process and enhance transcript
                processed_result = self._process_transcript(transcript_data)
                
                return {
                    'status': 'completed',
                    'transcript': processed_result['transcript'],
                    'confidence': processed_result['confidence'],
                    'alternatives': processed_result.get('alternatives', []),
                    'medical_terms_detected': processed_result.get('medical_terms', []),
                    'processing_time': job.get('CompletionTime', datetime.utcnow()).isoformat(),
                    'language_detected': job.get('LanguageCode', 'unknown')
                }
            
            elif status == 'FAILED':
                failure_reason = job.get('FailureReason', 'Unknown error')
                return {
                    'status': 'failed',
                    'error': failure_reason,
                    'job_name': job_name
                }
            
            else:
                return {
                    'status': 'in_progress',
                    'job_name': job_name,
                    'progress': self._estimate_progress(job)
                }
                
        except Exception as e:
            logger.error(f"Error getting transcription result: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'job_name': job_name
            }
    
    def _download_transcript(self, transcript_uri: str) -> Dict[str, Any]:
        """Download transcript JSON from S3."""
        try:
            # Parse S3 URI
            uri_parts = transcript_uri.replace('s3://', '').split('/', 1)
            bucket = uri_parts[0]
            key = uri_parts[1]
            
            # Download from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            transcript_data = json.loads(response['Body'].read().decode('utf-8'))
            
            return transcript_data
            
        except Exception as e:
            logger.error(f"Error downloading transcript: {e}")
            raise
    
    def _process_transcript(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcript for healthcare context and extract insights."""
        results = transcript_data.get('results', {})
        transcripts = results.get('transcripts', [])
        
        if not transcripts:
            return {
                'transcript': '',
                'confidence': 0.0,
                'alternatives': [],
                'medical_terms': []
            }
        
        # Get primary transcript
        primary_transcript = transcripts[0]['transcript']
        
        # Calculate average confidence
        items = results.get('items', [])
        confidences = [
            float(item.get('alternatives', [{}])[0].get('confidence', 0))
            for item in items
            if item.get('type') == 'pronunciation'
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Extract alternatives
        alternatives = []
        for transcript in transcripts[1:3]:  # Up to 2 alternatives
            alternatives.append(transcript['transcript'])
        
        # Detect medical terms
        medical_terms = self._detect_medical_terms(primary_transcript)
        
        # Post-process for healthcare context
        processed_transcript = self._post_process_healthcare_text(primary_transcript)
        
        return {
            'transcript': processed_transcript,
            'confidence': round(avg_confidence, 3),
            'alternatives': alternatives,
            'medical_terms': medical_terms,
            'word_count': len(processed_transcript.split()),
            'processing_metadata': {
                'original_length': len(primary_transcript),
                'processed_length': len(processed_transcript),
                'medical_terms_count': len(medical_terms)
            }
        }
    
    def _detect_medical_terms(self, text: str) -> List[Dict[str, Any]]:
        """Detect medical terms in the transcript."""
        medical_terms = []
        text_lower = text.lower()
        
        # Combine all medical vocabularies
        all_terms = []
        for config in self.language_configs.values():
            all_terms.extend(config['medical_vocabulary'])
        
        for term in all_terms:
            if term.lower() in text_lower:
                # Find positions of the term
                start_pos = text_lower.find(term.lower())
                if start_pos != -1:
                    medical_terms.append({
                        'term': term,
                        'position': start_pos,
                        'category': self._categorize_medical_term(term)
                    })
        
        return medical_terms
    
    def _categorize_medical_term(self, term: str) -> str:
        """Categorize medical terms for better context understanding."""
        term_lower = term.lower()
        
        # Symptoms
        symptom_keywords = ['pain', '痛', 'headache', '頭痛', 'fever', '發燒', 'cough', '咳嗽', 'dizzy', '頭暈']
        if any(keyword in term_lower for keyword in symptom_keywords):
            return 'symptom'
        
        # Conditions
        condition_keywords = ['diabetes', '糖尿病', 'hypertension', '高血壓', 'heart disease', '心臟病']
        if any(keyword in term_lower for keyword in condition_keywords):
            return 'condition'
        
        # Medications
        medication_keywords = ['medication', '藥物', 'prescription', '處方', 'dosage', '劑量']
        if any(keyword in term_lower for keyword in medication_keywords):
            return 'medication'
        
        # Emergency
        emergency_keywords = ['emergency', '緊急', 'help', '救命', 'urgent', '急']
        if any(keyword in term_lower for keyword in emergency_keywords):
            return 'emergency'
        
        return 'general'
    
    def _post_process_healthcare_text(self, text: str) -> str:
        """Post-process text for healthcare context."""
        # Common transcription corrections for healthcare terms
        corrections = {
            # English corrections
            'diabeetus': 'diabetes',
            'high blood pressure': 'hypertension',
            'heart attack': 'myocardial infarction',
            
            # Chinese corrections (common misheard terms)
            '糖料病': '糖尿病',
            '高血鴨': '高血壓',
            '心臟病發': '心肌梗塞'
        }
        
        processed_text = text
        for incorrect, correct in corrections.items():
            processed_text = processed_text.replace(incorrect, correct)
        
        # Capitalize medical terms appropriately
        medical_acronyms = ['COPD', 'HIV', 'AIDS', 'ECG', 'MRI', 'CT', 'DSE']
        for acronym in medical_acronyms:
            processed_text = processed_text.replace(acronym.lower(), acronym)
        
        return processed_text.strip()
    
    def _estimate_progress(self, job: Dict[str, Any]) -> int:
        """Estimate transcription progress based on job timing."""
        created_time = job.get('CreationTime')
        if not created_time:
            return 0
        
        # Estimate based on typical transcription time (1:4 ratio)
        elapsed = (datetime.utcnow() - created_time.replace(tzinfo=None)).total_seconds()
        estimated_total = 300  # 5 minutes typical
        
        progress = min(int((elapsed / estimated_total) * 100), 95)
        return progress


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for speech-to-text conversion.
    
    Expected event structure:
    {
        "action": "start_transcription" | "get_result",
        "audio_data": "base64_encoded_audio" (for start_transcription),
        "job_name": "transcription_job_name" (for get_result),
        "language_preference": "zh-HK" | "en-US",
        "user_id": "user_identifier"
    }
    """
    try:
        # Parse input
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        action = body.get('action', 'start_transcription')
        processor = SpeechToTextProcessor()
        
        if action == 'start_transcription':
            # Handle audio upload and start transcription
            audio_data = body.get('audio_data')
            language_preference = body.get('language_preference', 'zh-HK')
            user_id = body.get('user_id', 'anonymous')
            
            if not audio_data:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Audio data is required'})
                }
            
            # Generate unique job name
            job_name = f"healthcare-stt-{user_id}-{int(datetime.utcnow().timestamp())}"
            
            # Upload audio to S3
            try:
                audio_bytes = base64.b64decode(audio_data)
                audio_key = f"audio-input/{job_name}.wav"
                
                processor.s3_client.put_object(
                    Bucket=AUDIO_BUCKET,
                    Key=audio_key,
                    Body=audio_bytes,
                    ContentType='audio/wav',
                    Metadata={
                        'user_id': user_id,
                        'language_preference': language_preference,
                        'upload_time': datetime.utcnow().isoformat()
                    }
                )
                
                audio_uri = f"s3://{AUDIO_BUCKET}/{audio_key}"
                
            except Exception as e:
                logger.error(f"Error uploading audio: {e}")
                return {
                    'statusCode': 500,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Failed to upload audio'})
                }
            
            # Detect language and create vocabulary if needed
            language = processor.detect_language({'language_preference': language_preference})
            vocabulary_name = processor.create_custom_vocabulary(language)
            
            # Start transcription job
            try:
                result = processor.start_transcription_job(
                    audio_uri, job_name, language, vocabulary_name
                )
                
                return {
                    'statusCode': 200,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'job_name': result['job_name'],
                        'status': 'started',
                        'estimated_completion': result['estimated_completion'],
                        'language_detected': language,
                        'vocabulary_used': vocabulary_name is not None
                    })
                }
                
            except Exception as e:
                logger.error(f"Error starting transcription: {e}")
                return {
                    'statusCode': 500,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Failed to start transcription'})
                }
        
        elif action == 'get_result':
            # Get transcription result
            job_name = body.get('job_name')
            
            if not job_name:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Job name is required'})
                }
            
            result = processor.get_transcription_result(job_name)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(result)
            }
        
        else:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
    
    except Exception as e:
        logger.error(f"Error in speech-to-text handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }