# Healthcare AI Frontend Deployment Script (PowerShell)
# =====================================================
# 
# Deploys the Live2D frontend to S3 with CloudFront distribution.
# Usage: .\deploy.ps1 [environment] [api-gateway-url]

param(
    [Parameter(Position=0)]
    [string]$Environment = "production",
    
    [Parameter(Position=1, Mandatory=$true)]
    [string]$ApiGatewayUrl,
    
    [string]$AwsRegion = "us-east-1"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$FrontendSource = Join-Path $ProjectRoot "src\web\live2d\frontend"

# Environment-specific configurations
switch ($Environment) {
    "development" {
        $S3Bucket = "healthcare-ai-dev-frontend"
        $CloudFrontDistributionId = ""
    }
    "staging" {
        $S3Bucket = "healthcare-ai-staging-frontend"
        $CloudFrontDistributionId = $env:STAGING_CLOUDFRONT_ID
    }
    "production" {
        $S3Bucket = "healthcare-ai-prod-frontend"
        $CloudFrontDistributionId = $env:PROD_CLOUDFRONT_ID
    }
    default {
        Write-Host "❌ Invalid environment: $Environment" -ForegroundColor Red
        Write-Host "Valid environments: development, staging, production"
        exit 1
    }
}

Write-Host "🚀 Starting Healthcare AI Frontend Deployment" -ForegroundColor Green
Write-Host "Environment: $Environment"
Write-Host "S3 Bucket: $S3Bucket"
Write-Host "API Gateway URL: $ApiGatewayUrl"
Write-Host "Source Directory: $FrontendSource"
Write-Host ""

# Check if AWS CLI is installed
try {
    aws --version | Out-Null
} catch {
    Write-Host "❌ AWS CLI is not installed. Please install it first." -ForegroundColor Red
    exit 1
}

# Check if Python is available
try {
    python --version | Out-Null
} catch {
    Write-Host "❌ Python is not installed. Please install it first." -ForegroundColor Red
    exit 1
}

# Check AWS credentials
try {
    aws sts get-caller-identity | Out-Null
} catch {
    Write-Host "❌ AWS credentials not configured. Please run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Step 1: Check if source directory exists
if (-not (Test-Path $FrontendSource)) {
    Write-Host "❌ Frontend source directory not found: $FrontendSource" -ForegroundColor Red
    exit 1
}

Write-Host "📁 Source directory found: $FrontendSource" -ForegroundColor Green

# Step 2: Create S3 bucket if it doesn't exist
Write-Host "🪣 Checking S3 bucket: $S3Bucket"

try {
    aws s3api head-bucket --bucket $S3Bucket 2>$null
    Write-Host "✅ S3 bucket exists: $S3Bucket" -ForegroundColor Green
} catch {
    Write-Host "Creating S3 bucket: $S3Bucket"
    
    if ($AwsRegion -eq "us-east-1") {
        aws s3api create-bucket --bucket $S3Bucket
    } else {
        aws s3api create-bucket --bucket $S3Bucket --region $AwsRegion --create-bucket-configuration LocationConstraint=$AwsRegion
    }
    
    # Enable versioning
    aws s3api put-bucket-versioning --bucket $S3Bucket --versioning-configuration Status=Enabled
    
    Write-Host "✅ S3 bucket created: $S3Bucket" -ForegroundColor Green
}

# Step 3: Configure bucket policy for public read access
Write-Host "🔒 Configuring bucket policy..."

$BucketPolicy = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$S3Bucket/*"
        }
    ]
}
"@

$TempPolicyFile = [System.IO.Path]::GetTempFileName()
$BucketPolicy | Out-File -FilePath $TempPolicyFile -Encoding UTF8

try {
    aws s3api put-bucket-policy --bucket $S3Bucket --policy file://$TempPolicyFile
    Write-Host "✅ Bucket policy configured" -ForegroundColor Green
} finally {
    Remove-Item $TempPolicyFile -ErrorAction SilentlyContinue
}

# Step 4: Install Python dependencies
Write-Host "📦 Installing Python dependencies..."

pip install boto3 --quiet

Write-Host "✅ Dependencies installed" -ForegroundColor Green

# Step 5: Run Python deployment script
Write-Host "🚀 Running deployment script..."

$DeployScript = Join-Path $ScriptDir "deploy-frontend.py"
$DeployArgs = @(
    "--source-dir", $FrontendSource,
    "--bucket-name", $S3Bucket,
    "--api-gateway-url", $ApiGatewayUrl,
    "--environment", $Environment
)

if ($CloudFrontDistributionId) {
    $DeployArgs += "--cloudfront-distribution-id", $CloudFrontDistributionId
}

try {
    python $DeployScript @DeployArgs
    
    Write-Host ""
    Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
    
    # Get website URL
    $WebsiteUrl = "http://$S3Bucket.s3-website-$AwsRegion.amazonaws.com"
    
    Write-Host "🌐 Website URL: $WebsiteUrl" -ForegroundColor Cyan
    
    if ($CloudFrontDistributionId) {
        $CloudFrontDomain = aws cloudfront get-distribution --id $CloudFrontDistributionId --query 'Distribution.DomainName' --output text
        Write-Host "🚀 CloudFront URL: https://$CloudFrontDomain" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "📋 Deployment Summary:" -ForegroundColor Yellow
    Write-Host "  Environment: $Environment"
    Write-Host "  S3 Bucket: $S3Bucket"
    Write-Host "  API Gateway: $ApiGatewayUrl"
    Write-Host "  Website: $WebsiteUrl"
    
    if ($CloudFrontDistributionId) {
        Write-Host "  CloudFront: https://$CloudFrontDomain"
        Write-Host ""
        Write-Host "⏳ Note: CloudFront cache invalidation may take 5-15 minutes to complete." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "🎉 Healthcare AI Frontend is now live!" -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "❌ Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 6: Optional - Run smoke tests
if ($Environment -eq "production") {
    Write-Host ""
    Write-Host "🧪 Running smoke tests..." -ForegroundColor Yellow
    
    # Test if the website is accessible
    try {
        $Response = Invoke-WebRequest -Uri $WebsiteUrl -Method Head -TimeoutSec 30
        if ($Response.StatusCode -eq 200) {
            Write-Host "✅ Website accessibility test passed" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Website accessibility test failed (HTTP $($Response.StatusCode))" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️  Website accessibility test failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # Test API connectivity (if possible)
    $ApiHealthUrl = "$ApiGatewayUrl/health"
    try {
        $ApiResponse = Invoke-WebRequest -Uri $ApiHealthUrl -Method Get -TimeoutSec 30
        if ($ApiResponse.StatusCode -eq 200) {
            Write-Host "✅ API connectivity test passed" -ForegroundColor Green
        } else {
            Write-Host "⚠️  API connectivity test failed (HTTP $($ApiResponse.StatusCode))" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️  API connectivity test failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "🏁 Deployment script completed!" -ForegroundColor Green