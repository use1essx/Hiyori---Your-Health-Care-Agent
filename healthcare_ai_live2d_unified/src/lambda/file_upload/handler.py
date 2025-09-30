"""
File Upload Lambda Function
==========================

AWS Lambda handler for secure file upload and processing.
Handles medical documents with OCR, document analysis, and security measures.
"""

import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import uuid
import base64
import mimetypes
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
textract = boto3.client('textract')
comprehend_medical = boto3.client('comprehendmedical')
dynamodb = boto3.resource('dynamodb')

# Environment variables
FILES_BUCKET = os.environ.get('FILES_BUCKET')
FILE_METADATA_TABLE = os.environ.get('FILE_METADATA_TABLE')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Initialize DynamoDB table
file_metadata_table = dynamodb.Table(FILE_METADATA_TABLE) if FILE_METADATA_TABLE else None


class FileUploadProcessor:
    """Processes file uploads with security and medical document analysis."""
    
    def __init__(self):
        self.s3_client = s3
        self.textract_client = textract
        self.comprehend_medical_client = comprehend_medical
        self.dynamodb_table = file_metadata_table
        
        # Allowed file types and sizes
        self.allowed_file_types = {
            # Images
            '.jpg': {'max_size': 10 * 1024 * 1024, 'category': 'image'},  # 10MB
            '.jpeg': {'max_size': 10 * 1024 * 1024, 'category': 'image'},
            '.png': {'max_size': 10 * 1024 * 1024, 'category': 'image'},
            '.gif': {'max_size': 5 * 1024 * 1024, 'category': 'image'},   # 5MB
            
            # Documents
            '.pdf': {'max_size': 50 * 1024 * 1024, 'category': 'document'},  # 50MB
            '.doc': {'max_size': 25 * 1024 * 1024, 'category': 'document'},  # 25MB
            '.docx': {'max_size': 25 * 1024 * 1024, 'category': 'document'},
            '.txt': {'max_size': 1 * 1024 * 1024, 'category': 'document'},   # 1MB
            
            # Medical formats
            '.dcm': {'max_size': 100 * 1024 * 1024, 'category': 'medical'},  # 100MB for DICOM
            '.hl7': {'max_size': 1 * 1024 * 1024, 'category': 'medical'},    # 1MB for HL7
        }
        
        # Virus scanning patterns (basic)
        self.suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'onload=',
            b'onerror=',
            b'<?php',
            b'<%',
            b'exec(',
            b'system(',
            b'shell_exec'
        ]
    
    def validate_file(self, file_data: bytes, filename: str, content_type: str) -> Dict[str, Any]:
        """Validate uploaded file for security and compliance."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        # Check file extension
        file_extension = os.path.splitext(filename.lower())[1]
        if file_extension not in self.allowed_file_types:
            validation_result['valid'] = False
            validation_result['errors'].append(f"File type not allowed: {file_extension}")
            return validation_result
        
        file_config = self.allowed_file_types[file_extension]
        
        # Check file size
        file_size = len(file_data)
        if file_size > file_config['max_size']:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"File too large: {file_size} bytes (max: {file_config['max_size']} bytes)"
            )
        
        # Check for suspicious content
        for pattern in self.suspicious_patterns:
            if pattern in file_data[:1024]:  # Check first 1KB
                validation_result['valid'] = False
                validation_result['errors'].append("Suspicious content detected")
                break
        
        # Validate content type
        expected_content_type, _ = mimetypes.guess_type(filename)
        if expected_content_type and content_type != expected_content_type:
            validation_result['warnings'].append(
                f"Content type mismatch: expected {expected_content_type}, got {content_type}"
            )
        
        # Store file info
        validation_result['file_info'] = {
            'filename': filename,
            'size': file_size,
            'extension': file_extension,
            'category': file_config['category'],
            'content_type': content_type
        }
        
        return validation_result
    
    def upload_file_to_s3(self, file_data: bytes, filename: str, user_id: str,
                          content_type: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Upload file to S3 with security and lifecycle policies."""
        try:
            # Generate unique file ID and S3 key
            file_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().strftime('%Y/%m/%d')
            s3_key = f"uploads/{user_id}/{timestamp}/{file_id}_{filename}"
            
            # Prepare metadata
            s3_metadata = {
                'user-id': user_id,
                'original-filename': filename,
                'upload-time': datetime.utcnow().isoformat(),
                'file-id': file_id
            }
            
            if metadata:
                for key, value in metadata.items():
                    s3_metadata[f'custom-{key}'] = str(value)
            
            # Upload to S3 with encryption
            self.s3_client.put_object(
                Bucket=FILES_BUCKET,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
                Metadata=s3_metadata,
                ServerSideEncryption='AES256',
                StorageClass='STANDARD_IA'  # Infrequent Access for cost optimization
            )
            
            # Generate presigned URL for temporary access (24 hours)
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': FILES_BUCKET, 'Key': s3_key},
                ExpiresIn=86400  # 24 hours
            )
            
            return {
                'file_id': file_id,
                's3_key': s3_key,
                'presigned_url': presigned_url,
                'bucket': FILES_BUCKET,
                'upload_successful': True
            }
            
        except Exception as e:
            logger.error(f"Error uploading file to S3: {e}")
            return {
                'upload_successful': False,
                'error': str(e)
            }
    
    def store_file_metadata(self, file_info: Dict[str, Any], user_id: str,
                           s3_info: Dict[str, Any], processing_results: Dict[str, Any] = None) -> bool:
        """Store file metadata in DynamoDB."""
        if not self.dynamodb_table:
            logger.warning("File metadata table not configured")
            return False
        
        try:
            # Calculate TTL (90 days for medical files, 30 days for others)
            is_medical = file_info.get('category') == 'medical'
            ttl_days = 90 if is_medical else 30
            ttl = int((datetime.utcnow() + timedelta(days=ttl_days)).timestamp())
            
            item = {
                'file_id': s3_info['file_id'],
                'user_id': user_id,
                'original_filename': file_info['filename'],
                'file_size': file_info['size'],
                'file_type': file_info['extension'],
                'file_category': file_info['category'],
                'content_type': file_info['content_type'],
                's3_bucket': s3_info['bucket'],
                's3_key': s3_info['s3_key'],
                'upload_time': datetime.utcnow().isoformat(),
                'ttl': ttl,
                'processing_status': 'uploaded'
            }
            
            # Add processing results if available
            if processing_results:
                item['processing_results'] = processing_results
                item['processing_status'] = 'processed'
            
            self.dynamodb_table.put_item(Item=item)
            
            logger.info(f"Stored metadata for file {s3_info['file_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing file metadata: {e}")
            return False
    
    def process_document_with_textract(self, s3_key: str) -> Dict[str, Any]:
        """Process document with AWS Textract for OCR and analysis."""
        try:
            # Start document text detection
            response = self.textract_client.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': FILES_BUCKET,
                        'Name': s3_key
                    }
                }
            )
            
            job_id = response['JobId']
            
            # For synchronous processing of small documents, use detect_document_text
            try:
                sync_response = self.textract_client.detect_document_text(
                    Document={
                        'S3Object': {
                            'Bucket': FILES_BUCKET,
                            'Name': s3_key
                        }
                    }
                )
                
                # Extract text from blocks
                extracted_text = []
                for block in sync_response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        extracted_text.append(block['Text'])
                
                full_text = '\n'.join(extracted_text)
                
                return {
                    'status': 'completed',
                    'job_id': job_id,
                    'extracted_text': full_text,
                    'text_length': len(full_text),
                    'lines_detected': len(extracted_text),
                    'processing_time': datetime.utcnow().isoformat()
                }
                
            except Exception as sync_error:
                # Fall back to async processing
                logger.info(f"Sync processing failed, using async: {sync_error}")
                return {
                    'status': 'processing',
                    'job_id': job_id,
                    'message': 'Document is being processed asynchronously'
                }
                
        except Exception as e:
            logger.error(f"Error processing document with Textract: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def analyze_medical_text(self, text: str) -> Dict[str, Any]:
        """Analyze extracted text for medical entities using Comprehend Medical."""
        try:
            # Limit text length for Comprehend Medical (5000 UTF-8 bytes)
            if len(text.encode('utf-8')) > 5000:
                text = text[:4000]  # Safe truncation
            
            # Detect medical entities
            entities_response = self.comprehend_medical_client.detect_entities_v2(Text=text)
            
            # Detect PHI (Protected Health Information)
            phi_response = self.comprehend_medical_client.detect_phi(Text=text)
            
            # Process entities
            medical_entities = []
            for entity in entities_response.get('Entities', []):
                medical_entities.append({
                    'text': entity['Text'],
                    'category': entity['Category'],
                    'type': entity['Type'],
                    'confidence': entity['Score'],
                    'begin_offset': entity['BeginOffset'],
                    'end_offset': entity['EndOffset']
                })
            
            # Process PHI
            phi_entities = []
            for phi in phi_response.get('Entities', []):
                phi_entities.append({
                    'text': phi['Text'],
                    'type': phi['Type'],
                    'confidence': phi['Score'],
                    'begin_offset': phi['BeginOffset'],
                    'end_offset': phi['EndOffset']
                })
            
            return {
                'status': 'completed',
                'medical_entities': medical_entities,
                'phi_entities': phi_entities,
                'entity_count': len(medical_entities),
                'phi_count': len(phi_entities),
                'has_sensitive_data': len(phi_entities) > 0,
                'analysis_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing medical text: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def get_file_metadata(self, file_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve file metadata from DynamoDB."""
        if not self.dynamodb_table:
            return None
        
        try:
            response = self.dynamodb_table.get_item(
                Key={'file_id': file_id}
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            # Verify user ownership
            if item.get('user_id') != user_id:
                logger.warning(f"User {user_id} attempted to access file {file_id} owned by {item.get('user_id')}")
                return None
            
            return item
            
        except Exception as e:
            logger.error(f"Error retrieving file metadata: {e}")
            return None
    
    def delete_file(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """Delete file and its metadata."""
        try:
            # Get file metadata first
            metadata = self.get_file_metadata(file_id, user_id)
            if not metadata:
                return {
                    'success': False,
                    'error': 'File not found or access denied'
                }
            
            # Delete from S3
            self.s3_client.delete_object(
                Bucket=metadata['s3_bucket'],
                Key=metadata['s3_key']
            )
            
            # Delete metadata from DynamoDB
            if self.dynamodb_table:
                self.dynamodb_table.delete_item(
                    Key={'file_id': file_id}
                )
            
            return {
                'success': True,
                'file_id': file_id,
                'deleted_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for file upload and processing.
    
    Expected event structure:
    {
        "action": "upload" | "get_metadata" | "delete" | "get_processing_status",
        "file_data": "base64_encoded_file_data" (for upload),
        "filename": "original_filename" (for upload),
        "content_type": "mime_type" (for upload),
        "file_id": "file_identifier" (for get_metadata, delete, get_processing_status),
        "user_id": "user_identifier",
        "process_document": true/false (for upload, optional)
    }
    """
    try:
        # Parse input
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        action = body.get('action', 'upload')
        user_id = body.get('user_id', 'anonymous')
        
        processor = FileUploadProcessor()
        
        if action == 'upload':
            # Handle file upload
            file_data_b64 = body.get('file_data')
            filename = body.get('filename')
            content_type = body.get('content_type', 'application/octet-stream')
            process_document = body.get('process_document', False)
            
            if not file_data_b64 or not filename:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'File data and filename are required'})
                }
            
            try:
                # Decode file data
                file_data = base64.b64decode(file_data_b64)
            except Exception as e:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Invalid base64 file data'})
                }
            
            # Validate file
            validation_result = processor.validate_file(file_data, filename, content_type)
            
            if not validation_result['valid']:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'error': 'File validation failed',
                        'details': validation_result['errors']
                    })
                }
            
            # Upload to S3
            s3_result = processor.upload_file_to_s3(
                file_data, filename, user_id, content_type
            )
            
            if not s3_result['upload_successful']:
                return {
                    'statusCode': 500,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'error': 'File upload failed',
                        'details': s3_result.get('error')
                    })
                }
            
            # Process document if requested
            processing_results = None
            if process_document and validation_result['file_info']['category'] in ['document', 'image']:
                # OCR processing
                textract_result = processor.process_document_with_textract(s3_result['s3_key'])
                
                # Medical analysis if text was extracted
                medical_analysis = None
                if textract_result.get('status') == 'completed' and textract_result.get('extracted_text'):
                    medical_analysis = processor.analyze_medical_text(textract_result['extracted_text'])
                
                processing_results = {
                    'textract': textract_result,
                    'medical_analysis': medical_analysis
                }
            
            # Store metadata
            processor.store_file_metadata(
                validation_result['file_info'],
                user_id,
                s3_result,
                processing_results
            )
            
            # Return response
            response_data = {
                'file_id': s3_result['file_id'],
                'filename': filename,
                'file_size': validation_result['file_info']['size'],
                'file_type': validation_result['file_info']['extension'],
                'upload_time': datetime.utcnow().isoformat(),
                'presigned_url': s3_result['presigned_url'],
                'processing_requested': process_document
            }
            
            if processing_results:
                response_data['processing_results'] = processing_results
            
            if validation_result['warnings']:
                response_data['warnings'] = validation_result['warnings']
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(response_data)
            }
        
        elif action == 'get_metadata':
            # Get file metadata
            file_id = body.get('file_id')
            
            if not file_id:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'File ID is required'})
                }
            
            metadata = processor.get_file_metadata(file_id, user_id)
            
            if not metadata:
                return {
                    'statusCode': 404,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'File not found'})
                }
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(metadata)
            }
        
        elif action == 'delete':
            # Delete file
            file_id = body.get('file_id')
            
            if not file_id:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'File ID is required'})
                }
            
            delete_result = processor.delete_file(file_id, user_id)
            
            if not delete_result['success']:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': delete_result['error']})
                }
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(delete_result)
            }
        
        else:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
    
    except Exception as e:
        logger.error(f"Error in file upload handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }