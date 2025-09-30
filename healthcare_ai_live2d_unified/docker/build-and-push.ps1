# Healthcare AI Lambda Container Build and Push Script (PowerShell)
# ================================================================
# 
# Builds and pushes all Lambda container images to ECR
# Usage: .\build-and-push.ps1 [aws-account-id] [region] [environment]

param(
    [Parameter(Position=0, Mandatory=$true)]
    [string]$AwsAccountId,
    
    [Parameter(Position=1)]
    [string]$AwsRegion = "us-east-1",
    
    [Parameter(Position=2)]
    [string]$Environment = "dev"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Configuration
$EcrBase = "$AwsAccountId.dkr.ecr.$AwsRegion.amazonaws.com"
$RepoPrefix = "healthcare-ai-$Environment"

# Lambda functions to build
$LambdaFunctions = @(
    "agent-router",
    "illness-monitor",
    "mental-health",
    "safety-guardian",
    "wellness-coach",
    "speech-to-text",
    "text-to-speech",
    "file-upload",
    "hk-healthcare-data",
    "cost-monitor"
)

Write-Host "🚀 Building and pushing Healthcare AI Lambda containers" -ForegroundColor Green
Write-Host "AWS Account: $AwsAccountId"
Write-Host "Region: $AwsRegion"
Write-Host "Environment: $Environment"
Write-Host "ECR Base: $EcrBase"
Write-Host ""

# Check if AWS CLI is installed and configured
try {
    aws --version | Out-Null
} catch {
    Write-Host "❌ AWS CLI is not installed" -ForegroundColor Red
    exit 1
}

try {
    aws sts get-caller-identity | Out-Null
} catch {
    Write-Host "❌ AWS CLI is not configured or credentials are invalid" -ForegroundColor Red
    exit 1
}

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running" -ForegroundColor Red
    exit 1
}

# Login to ECR
Write-Host "🔐 Logging in to ECR..." -ForegroundColor Yellow
$LoginCommand = aws ecr get-login-password --region $AwsRegion
$LoginCommand | docker login --username AWS --password-stdin $EcrBase

# Function to create ECR repository if it doesn't exist
function Create-EcrRepo {
    param([string]$RepoName)
    
    try {
        aws ecr describe-repositories --repository-names $RepoName --region $AwsRegion | Out-Null
        Write-Host "✅ ECR repository exists: $RepoName" -ForegroundColor Green
    } catch {
        Write-Host "📦 Creating ECR repository: $RepoName" -ForegroundColor Yellow
        
        $LifecyclePolicy = @'
{
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
}
'@
        
        aws ecr create-repository --repository-name $RepoName --region $AwsRegion --image-scanning-configuration scanOnPush=true --lifecycle-policy-text $LifecyclePolicy | Out-Null
        
        Write-Host "✅ Created ECR repository: $RepoName" -ForegroundColor Green
    }
}

# Build base image first
Write-Host "🏗️  Building base Lambda image..." -ForegroundColor Yellow
$BaseRepoName = "$RepoPrefix-lambda-base"
$BaseImageUri = "$EcrBase/$BaseRepoName`:latest"

Create-EcrRepo -RepoName $BaseRepoName

docker build -t "healthcare-ai-lambda-base:latest" -t $BaseImageUri -f "docker/lambda-base/Dockerfile" .

Write-Host "📤 Pushing base image to ECR..." -ForegroundColor Yellow
docker push $BaseImageUri

Write-Host "✅ Base image built and pushed: $BaseImageUri" -ForegroundColor Green
Write-Host ""

# Build and push each Lambda function
foreach ($func in $LambdaFunctions) {
    Write-Host "🏗️  Building $func Lambda image..." -ForegroundColor Yellow
    
    $RepoName = "$RepoPrefix-$func"
    $ImageUri = "$EcrBase/$RepoName`:latest"
    
    # Create ECR repository
    Create-EcrRepo -RepoName $RepoName
    
    # Check if Dockerfile exists
    $DockerfilePath = "docker/$func/Dockerfile"
    if (-not (Test-Path $DockerfilePath)) {
        Write-Host "⚠️  Dockerfile not found for $func, creating generic one..." -ForegroundColor Yellow
        
        # Create directory if it doesn't exist
        $DockerDir = "docker/$func"
        if (-not (Test-Path $DockerDir)) {
            New-Item -ItemType Directory -Path $DockerDir -Force | Out-Null
        }
        
        # Create generic Dockerfile
        $FuncPath = $func -replace "-", "_"
        $DockerfileContent = @"
# $func Lambda Container
FROM healthcare-ai-lambda-base:latest

# Copy function specific code
COPY src/lambda/$FuncPath/ ./

# Set the Lambda handler
CMD ["handler.lambda_handler"]
"@
        
        $DockerfileContent | Out-File -FilePath $DockerfilePath -Encoding UTF8
    }
    
    # Build image
    docker build -t "$func-lambda:latest" -t $ImageUri -f $DockerfilePath .
    
    # Push to ECR
    Write-Host "📤 Pushing $func image to ECR..." -ForegroundColor Yellow
    docker push $ImageUri
    
    Write-Host "✅ $func image built and pushed: $ImageUri" -ForegroundColor Green
    Write-Host ""
}

# Clean up local images to save space
Write-Host "🧹 Cleaning up local images..." -ForegroundColor Yellow
docker image prune -f

Write-Host ""
Write-Host "🎉 All Lambda container images built and pushed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Summary:" -ForegroundColor Cyan
Write-Host "Base image: $BaseImageUri"
foreach ($func in $LambdaFunctions) {
    $RepoName = "$RepoPrefix-$func"
    $ImageUri = "$EcrBase/$RepoName`:latest"
    Write-Host "$func`: $ImageUri"
}

Write-Host ""
Write-Host "💡 Next steps:" -ForegroundColor Yellow
Write-Host "1. Update your CloudFormation template to use these container images"
Write-Host "2. Deploy your Lambda functions with the new container images"
Write-Host "3. Test the deployed functions"