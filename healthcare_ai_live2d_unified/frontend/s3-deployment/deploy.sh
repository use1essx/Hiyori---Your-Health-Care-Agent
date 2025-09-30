#!/bin/bash

# Healthcare AI Frontend Deployment Script
# ========================================
# 
# Deploys the Live2D frontend to S3 with CloudFront distribution.
# Usage: ./deploy.sh [environment] [api-gateway-url]

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FRONTEND_SOURCE="$PROJECT_ROOT/src/web/live2d/frontend"

# Default values
ENVIRONMENT="${1:-production}"
API_GATEWAY_URL="${2}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Environment-specific configurations
case $ENVIRONMENT in
    "development")
        S3_BUCKET="healthcare-ai-dev-frontend"
        CLOUDFRONT_DISTRIBUTION_ID=""
        ;;
    "staging")
        S3_BUCKET="healthcare-ai-staging-frontend"
        CLOUDFRONT_DISTRIBUTION_ID="${STAGING_CLOUDFRONT_ID}"
        ;;
    "production")
        S3_BUCKET="healthcare-ai-prod-frontend"
        CLOUDFRONT_DISTRIBUTION_ID="${PROD_CLOUDFRONT_ID}"
        ;;
    *)
        echo "❌ Invalid environment: $ENVIRONMENT"
        echo "Valid environments: development, staging, production"
        exit 1
        ;;
esac

# Validate required parameters
if [ -z "$API_GATEWAY_URL" ]; then
    echo "❌ API Gateway URL is required"
    echo "Usage: $0 [environment] [api-gateway-url]"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

echo "🚀 Starting Healthcare AI Frontend Deployment"
echo "Environment: $ENVIRONMENT"
echo "S3 Bucket: $S3_BUCKET"
echo "API Gateway URL: $API_GATEWAY_URL"
echo "Source Directory: $FRONTEND_SOURCE"
echo ""

# Step 1: Check if source directory exists
if [ ! -d "$FRONTEND_SOURCE" ]; then
    echo "❌ Frontend source directory not found: $FRONTEND_SOURCE"
    exit 1
fi

echo "📁 Source directory found: $FRONTEND_SOURCE"

# Step 2: Create S3 bucket if it doesn't exist
echo "🪣 Checking S3 bucket: $S3_BUCKET"

if ! aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
    echo "Creating S3 bucket: $S3_BUCKET"
    
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "$S3_BUCKET"
    else
        aws s3api create-bucket \
            --bucket "$S3_BUCKET" \
            --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$S3_BUCKET" \
        --versioning-configuration Status=Enabled
    
    echo "✅ S3 bucket created: $S3_BUCKET"
else
    echo "✅ S3 bucket exists: $S3_BUCKET"
fi

# Step 3: Configure bucket policy for public read access
echo "🔒 Configuring bucket policy..."

BUCKET_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$S3_BUCKET/*"
        }
    ]
}
EOF
)

echo "$BUCKET_POLICY" | aws s3api put-bucket-policy --bucket "$S3_BUCKET" --policy file:///dev/stdin

echo "✅ Bucket policy configured"

# Step 4: Install Python dependencies
echo "📦 Installing Python dependencies..."

pip3 install boto3 --quiet

echo "✅ Dependencies installed"

# Step 5: Run Python deployment script
echo "🚀 Running deployment script..."

python3 "$SCRIPT_DIR/deploy-frontend.py" \
    --source-dir "$FRONTEND_SOURCE" \
    --bucket-name "$S3_BUCKET" \
    --api-gateway-url "$API_GATEWAY_URL" \
    --cloudfront-distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --environment "$ENVIRONMENT"

DEPLOY_EXIT_CODE=$?

if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Deployment completed successfully!"
    
    # Get website URL
    WEBSITE_URL="http://$S3_BUCKET.s3-website-$AWS_REGION.amazonaws.com"
    
    echo "🌐 Website URL: $WEBSITE_URL"
    
    if [ -n "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
        CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution --id "$CLOUDFRONT_DISTRIBUTION_ID" --query 'Distribution.DomainName' --output text)
        echo "🚀 CloudFront URL: https://$CLOUDFRONT_DOMAIN"
    fi
    
    echo ""
    echo "📋 Deployment Summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  S3 Bucket: $S3_BUCKET"
    echo "  API Gateway: $API_GATEWAY_URL"
    echo "  Website: $WEBSITE_URL"
    
    if [ -n "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
        echo "  CloudFront: https://$CLOUDFRONT_DOMAIN"
        echo ""
        echo "⏳ Note: CloudFront cache invalidation may take 5-15 minutes to complete."
    fi
    
    echo ""
    echo "🎉 Healthcare AI Frontend is now live!"
    
else
    echo ""
    echo "❌ Deployment failed with exit code: $DEPLOY_EXIT_CODE"
    exit $DEPLOY_EXIT_CODE
fi

# Step 6: Optional - Run smoke tests
if [ "$ENVIRONMENT" = "production" ]; then
    echo ""
    echo "🧪 Running smoke tests..."
    
    # Test if the website is accessible
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$WEBSITE_URL" || echo "000")
    
    if [ "$HTTP_STATUS" = "200" ]; then
        echo "✅ Website accessibility test passed"
    else
        echo "⚠️  Website accessibility test failed (HTTP $HTTP_STATUS)"
    fi
    
    # Test API connectivity (if possible)
    API_HEALTH_URL="$API_GATEWAY_URL/health"
    API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_HEALTH_URL" || echo "000")
    
    if [ "$API_STATUS" = "200" ]; then
        echo "✅ API connectivity test passed"
    else
        echo "⚠️  API connectivity test failed (HTTP $API_STATUS)"
    fi
fi

echo ""
echo "🏁 Deployment script completed!"