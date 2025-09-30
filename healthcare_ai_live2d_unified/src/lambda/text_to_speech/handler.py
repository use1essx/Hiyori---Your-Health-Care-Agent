"""
Text-to-Speech Lambda Function
=============================

AWS Lambda handler for converting text to speech using AWS Polly.
Supports Traditional Chinese and English with agent-specific voice selection.
"""

import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import uuid
import base64

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
polly = boto3.client('polly')
s3 = boto3.client('s3')

# Environment variables
AUDIO_BUCKET = os.environ.get('AUDIO_BUCKET')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')


class TextToSpeechProcessor:
    """Processes text-to-speech conversion with agent-specific voices."""
    
    def __init__(self):
        self.polly_client = polly
        self.s3_client = s3
        
        # Agent-specific voice configurations
        self.agent_voices = {
            'illness_monitor': {
                'zh-HK': {
                    'voice_id': 'Zhiyu',  # Mandarin Chinese female voice
                    'language_code': 'cmn-CN',
                    'engine': 'standard',
                    'speaking_rate': 'medium',
                    'pitch': 'medium',
                    'personality': 'caring and professional'
                },
                'en-US': {
                    'voice_id': 'Joanna',  # US English female voice
                    'language_code': 'en-US',
                    'engine': 'neural',
                    'speaking_rate': 'medium',
                    'pitch': 'medium',
                    'personality': 'warm and knowledgeable'
                }
            },
            'mental_health': {
                'zh-HK': {
                    'voice_id': 'Zhiyu',
                    'language_code': 'cmn-CN',
                    'engine': 'standard',
                    'speaking_rate': 'slow',  # Slower for emotional support
                    'pitch': 'medium',
                    'personality': 'gentle and understanding'
                },
                'en-US': {
                    'voice_id': 'Amy',  # British English female voice (softer)
                    'language_code': 'en-GB',
                    'engine': 'neural',
                    'speaking_rate': 'slow',
                    'pitch': 'medium',
                    'personality': 'empathetic and supportive'
                }
            },
            'safety_guardian': {
                'zh-HK': {
                    'voice_id': 'Zhiyu',
                    'language_code': 'cmn-CN',
                    'engine': 'standard',
                    'speaking_rate': 'fast',  # Faster for emergencies
                    'pitch': 'medium',
                    'personality': 'authoritative and clear'
                },
                'en-US': {
                    'voice_id': 'Matthew',  # US English male voice (authoritative)
                    'language_code': 'en-US',
                    'engine': 'neural',
                    'speaking_rate': 'fast',
                    'pitch': 'medium',
                    'personality': 'confident and decisive'
                }
            },
            'wellness_coach': {
                'zh-HK': {
                    'voice_id': 'Zhiyu',
                    'language_code': 'cmn-CN',
                    'engine': 'standard',
                    'speaking_rate': 'medium',
                    'pitch': 'high',  # More energetic
                    'personality': 'enthusiastic and motivating'
                },
                'en-US': {
                    'voice_id': 'Kendra',  # US English female voice (energetic)
                    'language_code': 'en-US',
                    'engine': 'neural',
                    'speaking_rate': 'medium',
                    'pitch': 'high',
                    'personality': 'upbeat and encouraging'
                }
            }
        }
        
        # SSML templates for different contexts
        self.ssml_templates = {
            'emergency': {
                'zh': '<speak><prosody rate="fast" pitch="medium"><emphasis level="strong">{text}</emphasis></prosody></speak>',
                'en': '<speak><prosody rate="fast" pitch="medium"><emphasis level="strong">{text}</emphasis></prosody></speak>'
            },
            'caring': {
                'zh': '<speak><prosody rate="slow" pitch="medium" volume="soft">{text}</prosody></speak>',
                'en': '<speak><prosody rate="slow" pitch="medium" volume="soft">{text}</prosody></speak>'
            },
            'motivational': {
                'zh': '<speak><prosody rate="medium" pitch="high" volume="loud"><emphasis level="moderate">{text}</emphasis></prosody></speak>',
                'en': '<speak><prosody rate="medium" pitch="high" volume="loud"><emphasis level="moderate">{text}</emphasis></prosody></speak>'
            },
            'normal': {
                'zh': '<speak><prosody rate="medium" pitch="medium">{text}</prosody></speak>',
                'en': '<speak><prosody rate="medium" pitch="medium">{text}</prosody></speak>'
            }
        }
    
    def get_voice_config(self, agent_type: str, language: str) -> Dict[str, Any]:
        """Get voice configuration for specific agent and language."""
        # Normalize language code
        language_map = {
            'zh': 'zh-HK',
            'zh-TW': 'zh-HK',
            'zh-HK': 'zh-HK',
            'zh-CN': 'zh-HK',
            'en': 'en-US',
            'en-US': 'en-US',
            'en-GB': 'en-US'
        }
        
        normalized_language = language_map.get(language, 'zh-HK')
        
        # Get agent voice config or fallback to wellness_coach
        agent_config = self.agent_voices.get(agent_type, self.agent_voices['wellness_coach'])
        voice_config = agent_config.get(normalized_language, agent_config['zh-HK'])
        
        return voice_config
    
    def detect_speech_context(self, text: str, agent_type: str) -> str:
        """Detect appropriate speech context based on text content and agent."""
        text_lower = text.lower()
        
        # Emergency context
        emergency_keywords = [
            'emergency', '緊急', 'urgent', '急', 'call 999', '致電999',
            'immediately', '立即', 'right away', '馬上', 'crisis', '危機'
        ]
        
        if any(keyword in text_lower for keyword in emergency_keywords):
            return 'emergency'
        
        # Caring context (for emotional support)
        caring_keywords = [
            'understand', '明白', 'sorry', '對不起', 'here for you', '陪伴你',
            'support', '支持', 'comfort', '安慰', 'gentle', '溫柔'
        ]
        
        if agent_type == 'mental_health' or any(keyword in text_lower for keyword in caring_keywords):
            return 'caring'
        
        # Motivational context
        motivational_keywords = [
            'great job', '做得好', 'excellent', '優秀', 'keep going', '繼續努力',
            'you can do it', '你可以做到', 'amazing', '了不起', 'proud', '驕傲'
        ]
        
        if agent_type == 'wellness_coach' or any(keyword in text_lower for keyword in motivational_keywords):
            return 'motivational'
        
        return 'normal'
    
    def prepare_ssml_text(self, text: str, context: str, language: str) -> str:
        """Prepare SSML-enhanced text for better speech synthesis."""
        # Determine language for template
        template_lang = 'zh' if language.startswith('zh') else 'en'
        
        # Get appropriate SSML template
        template = self.ssml_templates.get(context, self.ssml_templates['normal'])
        ssml_template = template[template_lang]
        
        # Clean and prepare text
        cleaned_text = self._clean_text_for_speech(text, language)
        
        # Apply SSML template
        ssml_text = ssml_template.format(text=cleaned_text)
        
        # Add pauses for better comprehension
        ssml_text = self._add_natural_pauses(ssml_text, language)
        
        return ssml_text
    
    def _clean_text_for_speech(self, text: str, language: str) -> str:
        """Clean text for better speech synthesis."""
        # Remove markdown formatting
        cleaned = text.replace('**', '').replace('*', '').replace('_', '')
        
        # Handle emojis and special characters
        emoji_replacements = {
            '🚨': '緊急' if language.startswith('zh') else 'Emergency',
            '💪': '加油' if language.startswith('zh') else 'Stay strong',
            '✨': '',  # Remove decorative emojis
            '💙': '',
            '🌟': '',
            '🏥': '醫院' if language.startswith('zh') else 'Hospital',
            '📞': '電話' if language.startswith('zh') else 'Phone',
            '⚠️': '注意' if language.startswith('zh') else 'Warning'
        }
        
        for emoji, replacement in emoji_replacements.items():
            cleaned = cleaned.replace(emoji, replacement)
        
        # Handle URLs and special formatting
        cleaned = cleaned.replace('http://', '').replace('https://', '')
        cleaned = cleaned.replace('\n\n', '. ').replace('\n', '. ')
        
        # Handle numbers and abbreviations for Chinese
        if language.startswith('zh'):
            number_replacements = {
                '999': '九九九',
                '24/7': '二十四小時',
                'A&E': '急症室',
                'DSE': '中學文憑試'
            }
            
            for abbrev, replacement in number_replacements.items():
                cleaned = cleaned.replace(abbrev, replacement)
        
        return cleaned.strip()
    
    def _add_natural_pauses(self, ssml_text: str, language: str) -> str:
        """Add natural pauses to SSML for better comprehension."""
        # Add pauses after sentences
        ssml_text = ssml_text.replace('。', '。<break time="0.5s"/>')
        ssml_text = ssml_text.replace('. ', '. <break time="0.5s"/>')
        ssml_text = ssml_text.replace('? ', '? <break time="0.5s"/>')
        ssml_text = ssml_text.replace('! ', '! <break time="0.5s"/>')
        
        # Add pauses after important phrases
        if language.startswith('zh'):
            important_phrases = ['緊急情況', '立即', '馬上', '重要提醒']
        else:
            important_phrases = ['emergency', 'immediately', 'important', 'urgent']
        
        for phrase in important_phrases:
            ssml_text = ssml_text.replace(phrase, f'{phrase}<break time="0.3s"/>')
        
        return ssml_text
    
    async def synthesize_speech(self, text: str, agent_type: str, 
                              language: str, output_format: str = 'mp3') -> Dict[str, Any]:
        """Synthesize speech with agent-specific voice and context."""
        try:
            # Get voice configuration
            voice_config = self.get_voice_config(agent_type, language)
            
            # Detect speech context
            context = self.detect_speech_context(text, agent_type)
            
            # Prepare SSML text
            ssml_text = self.prepare_ssml_text(text, context, language)
            
            # Synthesize speech
            response = self.polly_client.synthesize_speech(
                Text=ssml_text,
                TextType='ssml',
                VoiceId=voice_config['voice_id'],
                OutputFormat=output_format,
                Engine=voice_config['engine'],
                LanguageCode=voice_config.get('language_code')
            )
            
            # Get audio stream
            audio_stream = response['AudioStream'].read()
            
            # Generate unique filename
            audio_id = str(uuid.uuid4())
            audio_key = f"audio-output/{agent_type}/{audio_id}.{output_format}"
            
            # Upload to S3 with temporary access
            self.s3_client.put_object(
                Bucket=AUDIO_BUCKET,
                Key=audio_key,
                Body=audio_stream,
                ContentType=f'audio/{output_format}',
                Metadata={
                    'agent_type': agent_type,
                    'language': language,
                    'voice_id': voice_config['voice_id'],
                    'context': context,
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            
            # Generate presigned URL for temporary access (1 hour)
            audio_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': AUDIO_BUCKET, 'Key': audio_key},
                ExpiresIn=3600  # 1 hour
            )
            
            return {
                'audio_id': audio_id,
                'audio_url': audio_url,
                'audio_format': output_format,
                'voice_used': voice_config['voice_id'],
                'language': language,
                'context': context,
                'duration_estimate': len(text) * 0.1,  # Rough estimate: 0.1s per character
                'file_size': len(audio_stream),
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            raise
    
    def get_available_voices(self, language: str = None) -> List[Dict[str, Any]]:
        """Get list of available voices for the specified language."""
        try:
            if language:
                # Map language to Polly language codes
                language_map = {
                    'zh-HK': 'cmn-CN',
                    'zh': 'cmn-CN',
                    'en-US': 'en-US',
                    'en': 'en-US'
                }
                
                polly_language = language_map.get(language, 'cmn-CN')
                
                response = self.polly_client.describe_voices(
                    LanguageCode=polly_language
                )
            else:
                response = self.polly_client.describe_voices()
            
            voices = []
            for voice in response['Voices']:
                voices.append({
                    'voice_id': voice['Id'],
                    'name': voice['Name'],
                    'gender': voice['Gender'],
                    'language_code': voice['LanguageCode'],
                    'language_name': voice['LanguageName'],
                    'supported_engines': voice.get('SupportedEngines', ['standard'])
                })
            
            return voices
            
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            return []
    
    def get_speech_marks(self, text: str, agent_type: str, language: str) -> Dict[str, Any]:
        """Get speech marks for lip-sync with Live2D avatar."""
        try:
            voice_config = self.get_voice_config(agent_type, language)
            context = self.detect_speech_context(text, agent_type)
            ssml_text = self.prepare_ssml_text(text, context, language)
            
            # Get speech marks (for lip-sync)
            response = self.polly_client.synthesize_speech(
                Text=ssml_text,
                TextType='ssml',
                VoiceId=voice_config['voice_id'],
                OutputFormat='json',
                Engine=voice_config['engine'],
                SpeechMarkTypes=['viseme', 'word'],
                LanguageCode=voice_config.get('language_code')
            )
            
            # Parse speech marks
            speech_marks_data = response['AudioStream'].read().decode('utf-8')
            speech_marks = []
            
            for line in speech_marks_data.strip().split('\n'):
                if line:
                    mark = json.loads(line)
                    speech_marks.append(mark)
            
            return {
                'speech_marks': speech_marks,
                'total_duration': max(mark['time'] for mark in speech_marks) if speech_marks else 0,
                'word_count': len([mark for mark in speech_marks if mark['type'] == 'word']),
                'viseme_count': len([mark for mark in speech_marks if mark['type'] == 'viseme']),
                'voice_used': voice_config['voice_id'],
                'language': language
            }
            
        except Exception as e:
            logger.error(f"Error getting speech marks: {e}")
            return {'error': str(e)}


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for text-to-speech conversion.
    
    Expected event structure:
    {
        "action": "synthesize" | "get_voices" | "get_speech_marks",
        "text": "text to convert to speech",
        "agent_type": "illness_monitor" | "mental_health" | "safety_guardian" | "wellness_coach",
        "language": "zh-HK" | "en-US",
        "output_format": "mp3" | "ogg" | "pcm"
    }
    """
    try:
        # Parse input
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        action = body.get('action', 'synthesize')
        processor = TextToSpeechProcessor()
        
        if action == 'synthesize':
            # Synthesize speech
            text = body.get('text', '')
            agent_type = body.get('agent_type', 'wellness_coach')
            language = body.get('language', 'zh-HK')
            output_format = body.get('output_format', 'mp3')
            
            if not text:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Text is required'})
                }
            
            # Check text length (Polly has limits)
            if len(text) > 3000:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Text too long (max 3000 characters)'})
                }
            
            result = await processor.synthesize_speech(text, agent_type, language, output_format)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(result)
            }
        
        elif action == 'get_voices':
            # Get available voices
            language = body.get('language')
            voices = processor.get_available_voices(language)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'voices': voices,
                    'total_count': len(voices),
                    'language_filter': language
                })
            }
        
        elif action == 'get_speech_marks':
            # Get speech marks for lip-sync
            text = body.get('text', '')
            agent_type = body.get('agent_type', 'wellness_coach')
            language = body.get('language', 'zh-HK')
            
            if not text:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Text is required'})
                }
            
            result = processor.get_speech_marks(text, agent_type, language)
            
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
        logger.error(f"Error in text-to-speech handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }