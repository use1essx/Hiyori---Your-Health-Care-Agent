#!/bin/bash

# Healthcare AI Lambda Container Build and Push Script
# ===================================================
# 
# Builds and pushes all Lambda container images to ECR
# Usage: ./build-and-push.sh [aws-account-id] [region] [environment]

set -e  # Exit on any error

# Configuration
AWS_ACCOUNT_ID="${1}"
AWS_REGION="${2:-us-east-1}"
ENVIRONMENT="${3:-dev}"

# Validate required parameters
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ AWS Account ID is required"
    echo "Usage: $0 [aws-account-id] [region] [environment]"
    exit 1
fi

# ECR repository base name
ECR_BASE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
REPO_PREFIX="healthcare-ai-$ENVIRONMENT"

# Lambda functions to build
LAMBDA_FUNCTIONS=(
    "agent-router"
    "illness-monitor"
    "mental-health"
    "safety-guardian"
    "wellness-coach"
    "speech-to-text"
    "text-to-speech"
    "file-upload"
    "hk-healthcare-data"
    "cost-monitor"
)

echo "🚀 Building and pushing Healthcare AI Lambda containers"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Environment: $ENVIRONMENT"
echo "ECR Base: $ECR_BASE"
echo ""

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI is not configured or credentials are invalid"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running"
    exit 1
fi

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_BASE

# Function to create ECR repository if it doesn't exist
create_ecr_repo() {
    local repo_name="$1"
    
    if ! aws ecr describe-repositories --repository-names "$repo_name" --region $AWS_REGION &> /dev/null; then
        echo "📦 Creating ECR repository: $repo_name"
        aws ecr create-repository \
            --repository-name "$repo_name" \
            --region $AWS_REGION \
            --image-scanning-configuration scanOnPush=true \
            --lifecycle-policy-text '{
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Keep last 10 images",
                        "selection": {
                            "tagStatus": "any",
                            "countType": "imageCountMoreThan",
                            "countNumber": 10
                        },
                        "action": {
                            "type": "expire"
                        }
                    }
                ]
            }' > /dev/null
        
        echo "✅ Created ECR repository: $repo_name"
    else
        echo "✅ ECR repository exists: $repo_name"
    fi
}

# Build base image first
echo "🏗️  Building base Lambda image..."
BASE_REPO_NAME="$REPO_PREFIX-lambda-base"
BASE_IMAGE_URI="$ECR_BASE/$BASE_REPO_NAME:latest"

create_ecr_repo "$BASE_REPO_NAME"

docker build \
    -t healthcare-ai-lambda-base:latest \
    -t "$BASE_IMAGE_URI" \
    -f docker/lambda-base/Dockerfile \
    .

echo "📤 Pushing base image to ECR..."
docker push "$BASE_IMAGE_URI"

echo "✅ Base image built and pushed: $BASE_IMAGE_URI"
echo ""

# Build and push each Lambda function
for func in "${LAMBDA_FUNCTIONS[@]}"; do
    echo "🏗️  Building $func Lambda image..."
    
    REPO_NAME="$REPO_PREFIX-$func"
    IMAGE_URI="$ECR_BASE/$REPO_NAME:latest"
    
    # Create ECR repository
    create_ecr_repo "$REPO_NAME"
    
    # Check if Dockerfile exists
    DOCKERFILE_PATH="docker/$func/Dockerfile"
    if [ ! -f "$DOCKERFILE_PATH" ]; then
        echo "⚠️  Dockerfile not found for $func, creating generic one..."
        
        # Create directory if it doesn't exist
        mkdir -p "docker/$func"
        
        # Create generic Dockerfile
        cat > "$DOCKERFILE_PATH" << EOF
# $func Lambda Container
FROM healthcare-ai-lambda-base:latest

# Copy function specific code
COPY src/lambda/${func//-/_}/ ./

# Set the Lambda handler
CMD ["handler.lambda_handler"]
EOF
    fi
    
    # Build image
    docker build \
        -t "$func-lambda:latest" \
        -t "$IMAGE_URI" \
        -f "$DOCKERFILE_PATH" \
        .
    
    # Push to ECR
    echo "📤 Pushing $func image to ECR..."
    docker push "$IMAGE_URI"
    
    echo "✅ $func image built and pushed: $IMAGE_URI"
    echo ""
done

# Clean up local images to save space
echo "🧹 Cleaning up local images..."
docker image prune -f

echo ""
echo "🎉 All Lambda container images built and pushed successfully!"
echo ""
echo "📋 Summary:"
echo "Base image: $BASE_IMAGE_URI"
for func in "${LAMBDA_FUNCTIONS[@]}"; do
    REPO_NAME="$REPO_PREFIX-$func"
    IMAGE_URI="$ECR_BASE/$REPO_NAME:latest"
    echo "$func: $IMAGE_URI"
done

echo ""
echo "💡 Next steps:"
echo "1. Update your CloudFormation template to use these container images"
echo "2. Deploy your Lambda functions with the new container images"
echo "3. Test the deployed functions"