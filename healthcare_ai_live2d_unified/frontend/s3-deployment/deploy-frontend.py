"""
S3 Frontend Deployment Script
============================

Deploys the Live2D frontend to S3 static hosting with CloudFront distribution.
Updates API endpoint configurations and optimizes assets for CDN delivery.
"""

import os
import json
import boto3
import logging
from pathlib import Path
from typing import Dict, Any, List
import mimetypes
import gzip
import hashlib
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3FrontendDeployer:
    """Handles deployment of Live2D frontend to S3 with CloudFront."""
    
    def __init__(self, bucket_name: str, cloudfront_distribution_id: str = None):
        self.s3_client = boto3.client('s3')
        self.cloudfront_client = boto3.client('cloudfront')
        self.bucket_name = bucket_name
        self.cloudfront_distribution_id = cloudfront_distribution_id
        
        # File type configurations
        self.compression_types = {
            '.js', '.css', '.html', '.json', '.svg', '.txt', '.xml'
        }
        
        self.cache_control_settings = {
            '.html': 'max-age=300',  # 5 minutes for HTML files
            '.js': 'max-age=31536000',  # 1 year for JS files
            '.css': 'max-age=31536000',  # 1 year for CSS files
            '.png': 'max-age=31536000',  # 1 year for images
            '.jpg': 'max-age=31536000',
            '.jpeg': 'max-age=31536000',
            '.gif': 'max-age=31536000',
            '.svg': 'max-age=31536000',
            '.ico': 'max-age=31536000',
            '.woff': 'max-age=31536000',  # 1 year for fonts
            '.woff2': 'max-age=31536000',
            '.ttf': 'max-age=31536000',
            '.json': 'max-age=300',  # 5 minutes for config files
            '.moc3': 'max-age=31536000',  # 1 year for Live2D model files
            '.model3': 'max-age=31536000',
            '.physics3': 'max-age=31536000',
            '.cdi3': 'max-age=31536000'
        }
    
    def prepare_frontend_files(self, source_dir: str, build_dir: str, 
                             api_gateway_url: str, environment: str = 'production') -> Dict[str, Any]:
        """Prepare frontend files for S3 deployment."""
        source_path = Path(source_dir)
        build_path = Path(build_dir)
        
        # Create build directory
        build_path.mkdir(parents=True, exist_ok=True)
        
        # Copy and process files
        processed_files = []
        total_size = 0
        
        for file_path in source_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_path)
                target_path = build_path / relative_path
                
                # Create target directory
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Process file based on type
                if file_path.suffix.lower() in ['.html', '.js', '.css', '.json']:
                    processed_size = self._process_text_file(
                        file_path, target_path, api_gateway_url, environment
                    )
                else:
                    # Copy binary files as-is
                    target_path.write_bytes(file_path.read_bytes())
                    processed_size = target_path.stat().st_size
                
                processed_files.append({
                    'source': str(relative_path),
                    'target': str(target_path),
                    'size': processed_size,
                    'type': file_path.suffix.lower()
                })
                
                total_size += processed_size
        
        logger.info(f"Prepared {len(processed_files)} files, total size: {total_size / 1024 / 1024:.2f} MB")
        
        return {
            'files': processed_files,
            'total_size': total_size,
            'build_directory': str(build_path)
        }
    
    def _process_text_file(self, source_path: Path, target_path: Path, 
                          api_gateway_url: str, environment: str) -> int:
        """Process text files with API endpoint updates and optimizations."""
        content = source_path.read_text(encoding='utf-8')
        
        # Update API endpoints
        content = self._update_api_endpoints(content, api_gateway_url, environment)
        
        # Minify if needed (basic minification)
        if source_path.suffix.lower() in ['.js', '.css']:
            content = self._basic_minify(content, source_path.suffix.lower())
        
        # Write processed content
        target_path.write_text(content, encoding='utf-8')
        
        return len(content.encode('utf-8'))
    
    def _update_api_endpoints(self, content: str, api_gateway_url: str, environment: str) -> str:
        """Update API endpoints in frontend files."""
        # Common API endpoint patterns to replace
        replacements = {
            # Local development endpoints
            'http://localhost:8000/api': f'{api_gateway_url}',
            'http://127.0.0.1:8000/api': f'{api_gateway_url}',
            'localhost:8000': api_gateway_url.replace('https://', '').replace('http://', ''),
            
            # Placeholder endpoints
            '{{API_GATEWAY_URL}}': api_gateway_url,
            '${API_GATEWAY_URL}': api_gateway_url,
            
            # Environment-specific replacements
            '{{ENVIRONMENT}}': environment,
            '${ENVIRONMENT}': environment
        }
        
        updated_content = content
        for old_endpoint, new_endpoint in replacements.items():
            updated_content = updated_content.replace(old_endpoint, new_endpoint)
        
        # Update WebSocket endpoints (if any)
        if 'ws://localhost' in updated_content or 'wss://localhost' in updated_content:
            ws_url = api_gateway_url.replace('https://', 'wss://').replace('http://', 'ws://')
            updated_content = updated_content.replace('ws://localhost:8000', ws_url)
            updated_content = updated_content.replace('wss://localhost:8000', ws_url)
        
        return updated_content
    
    def _basic_minify(self, content: str, file_type: str) -> str:
        """Basic minification for JS and CSS files."""
        if file_type == '.js':
            # Basic JS minification (remove comments and extra whitespace)
            lines = content.split('\n')
            minified_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('//') and not line.startswith('/*'):
                    minified_lines.append(line)
            
            return ' '.join(minified_lines)
        
        elif file_type == '.css':
            # Basic CSS minification
            import re
            # Remove comments
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            # Remove extra whitespace
            content = re.sub(r'\s+', ' ', content)
            # Remove spaces around certain characters
            content = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', content)
            
            return content.strip()
        
        return content
    
    def upload_to_s3(self, build_dir: str, file_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upload processed files to S3 with optimized settings."""
        build_path = Path(build_dir)
        upload_results = []
        total_uploaded = 0
        
        for file_info in file_list:
            file_path = Path(file_info['target'])
            s3_key = str(file_path.relative_to(build_path)).replace('\\', '/')
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Prepare upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
                'ContentType': content_type,
                'CacheControl': self._get_cache_control(file_path.suffix.lower())
            }
            
            # Handle compression
            file_data = file_path.read_bytes()
            if file_path.suffix.lower() in self.compression_types:
                compressed_data = gzip.compress(file_data)
                if len(compressed_data) < len(file_data):
                    file_data = compressed_data
                    upload_params['ContentEncoding'] = 'gzip'
            
            # Add metadata
            upload_params['Metadata'] = {
                'original-size': str(file_info['size']),
                'upload-time': datetime.utcnow().isoformat(),
                'file-hash': hashlib.md5(file_data).hexdigest()
            }
            
            # Upload file
            try:
                self.s3_client.put_object(Body=file_data, **upload_params)
                
                upload_results.append({
                    'file': s3_key,
                    'size': len(file_data),
                    'compressed': 'ContentEncoding' in upload_params,
                    'content_type': content_type,
                    'status': 'success'
                })
                
                total_uploaded += len(file_data)
                logger.info(f"Uploaded: {s3_key} ({len(file_data)} bytes)")
                
            except Exception as e:
                logger.error(f"Failed to upload {s3_key}: {e}")
                upload_results.append({
                    'file': s3_key,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return {
            'uploaded_files': upload_results,
            'total_uploaded_size': total_uploaded,
            'success_count': len([r for r in upload_results if r['status'] == 'success']),
            'failed_count': len([r for r in upload_results if r['status'] == 'failed'])
        }
    
    def _get_cache_control(self, file_extension: str) -> str:
        """Get cache control header for file type."""
        return self.cache_control_settings.get(file_extension, 'max-age=86400')  # Default 1 day
    
    def configure_s3_website(self) -> Dict[str, Any]:
        """Configure S3 bucket for static website hosting."""
        try:
            # Configure website hosting
            website_config = {
                'IndexDocument': {'Suffix': 'index.html'},
                'ErrorDocument': {'Key': 'error.html'}
            }
            
            self.s3_client.put_bucket_website(
                Bucket=self.bucket_name,
                WebsiteConfiguration=website_config
            )
            
            # Configure CORS for API access
            cors_config = {
                'CORSRules': [
                    {
                        'AllowedHeaders': ['*'],
                        'AllowedMethods': ['GET', 'POST', 'PUT', 'DELETE', 'HEAD'],
                        'AllowedOrigins': ['*'],
                        'ExposeHeaders': ['ETag'],
                        'MaxAgeSeconds': 3000
                    }
                ]
            }
            
            self.s3_client.put_bucket_cors(
                Bucket=self.bucket_name,
                CORSConfiguration=cors_config
            )
            
            # Get website URL
            region = self.s3_client.get_bucket_location(Bucket=self.bucket_name)['LocationConstraint']
            if region is None:
                region = 'us-east-1'
            
            website_url = f"http://{self.bucket_name}.s3-website-{region}.amazonaws.com"
            
            return {
                'website_url': website_url,
                'bucket_name': self.bucket_name,
                'region': region,
                'status': 'configured'
            }
            
        except Exception as e:
            logger.error(f"Error configuring S3 website: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def invalidate_cloudfront(self, paths: List[str] = None) -> Dict[str, Any]:
        """Invalidate CloudFront cache for updated files."""
        if not self.cloudfront_distribution_id:
            return {'status': 'skipped', 'reason': 'No CloudFront distribution ID provided'}
        
        try:
            # Default to invalidating all files
            if not paths:
                paths = ['/*']
            
            response = self.cloudfront_client.create_invalidation(
                DistributionId=self.cloudfront_distribution_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': len(paths),
                        'Items': paths
                    },
                    'CallerReference': f"deployment-{int(datetime.utcnow().timestamp())}"
                }
            )
            
            invalidation_id = response['Invalidation']['Id']
            
            return {
                'status': 'created',
                'invalidation_id': invalidation_id,
                'paths': paths,
                'distribution_id': self.cloudfront_distribution_id
            }
            
        except Exception as e:
            logger.error(f"Error creating CloudFront invalidation: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def deploy_complete_frontend(self, source_dir: str, api_gateway_url: str, 
                               environment: str = 'production') -> Dict[str, Any]:
        """Complete frontend deployment process."""
        deployment_start = datetime.utcnow()
        
        try:
            # Step 1: Prepare files
            logger.info("Step 1: Preparing frontend files...")
            build_dir = f"/tmp/healthcare-frontend-build-{int(deployment_start.timestamp())}"
            preparation_result = self.prepare_frontend_files(
                source_dir, build_dir, api_gateway_url, environment
            )
            
            # Step 2: Configure S3 website
            logger.info("Step 2: Configuring S3 website...")
            website_config = self.configure_s3_website()
            
            # Step 3: Upload files
            logger.info("Step 3: Uploading files to S3...")
            upload_result = self.upload_to_s3(build_dir, preparation_result['files'])
            
            # Step 4: Invalidate CloudFront
            logger.info("Step 4: Invalidating CloudFront cache...")
            invalidation_result = self.invalidate_cloudfront()
            
            deployment_end = datetime.utcnow()
            deployment_time = (deployment_end - deployment_start).total_seconds()
            
            return {
                'status': 'success',
                'deployment_time': deployment_time,
                'preparation': preparation_result,
                'website_config': website_config,
                'upload': upload_result,
                'invalidation': invalidation_result,
                'api_gateway_url': api_gateway_url,
                'environment': environment,
                'deployed_at': deployment_end.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'deployment_time': (datetime.utcnow() - deployment_start).total_seconds()
            }


def main():
    """Main deployment function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy Live2D frontend to S3')
    parser.add_argument('--source-dir', required=True, help='Source directory containing frontend files')
    parser.add_argument('--bucket-name', required=True, help='S3 bucket name for hosting')
    parser.add_argument('--api-gateway-url', required=True, help='API Gateway URL')
    parser.add_argument('--cloudfront-distribution-id', help='CloudFront distribution ID')
    parser.add_argument('--environment', default='production', help='Deployment environment')
    
    args = parser.parse_args()
    
    # Initialize deployer
    deployer = S3FrontendDeployer(
        bucket_name=args.bucket_name,
        cloudfront_distribution_id=args.cloudfront_distribution_id
    )
    
    # Deploy frontend
    result = deployer.deploy_complete_frontend(
        source_dir=args.source_dir,
        api_gateway_url=args.api_gateway_url,
        environment=args.environment
    )
    
    # Print results
    print(json.dumps(result, indent=2))
    
    if result['status'] == 'success':
        print(f"\n✅ Deployment successful!")
        print(f"Website URL: {result['website_config']['website_url']}")
        print(f"Files uploaded: {result['upload']['success_count']}")
        print(f"Total size: {result['upload']['total_uploaded_size'] / 1024 / 1024:.2f} MB")
        print(f"Deployment time: {result['deployment_time']:.2f} seconds")
    else:
        print(f"\n❌ Deployment failed: {result.get('error', 'Unknown error')}")
        exit(1)


if __name__ == '__main__':
    main()