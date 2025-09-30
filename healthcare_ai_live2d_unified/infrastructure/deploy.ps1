# Healthcare AI Live2D System - One-Click AWS Deployment Script (PowerShell)
# This script deploys the entire serverless healthcare system to AWS

param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1", 
    [string]$StackName = "healthcare-ai-live2d",
    [string]$CostAlertEmail = "",
    [int]$CostThreshold = 20,
    [switch]$Help
)

# Configuration
$TemplateFile = "cloudformation-template.yaml"

# Function to write colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to show help
function Show-Help {
    Write-Host "Healthcare AI Live2D System - AWS Deployment Script (PowerShell)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\deploy.ps1 [OPTIONS]" -ForegroundColor White
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor White
    Write-Host "  -Environment ENV      Environment name (dev, staging, prod) [default: dev]" -ForegroundColor Gray
    Write-Host "  -Region REGION        AWS region [default: us-east-1]" -ForegroundColor Gray
    Write-Host "  -StackName NAME       CloudFormation stack name [default: healthcare-ai-live2d]" -ForegroundColor Gray
    Write-Host "  -CostAlertEmail EMAIL Email for cost alerts" -ForegroundColor Gray
    Write-Host "  -CostThreshold AMOUNT Cost threshold in USD [default: 20]" -ForegroundColor Gray
    Write-Host "  -Help                 Show this help message" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  .\deploy.ps1 -CostAlertEmail admin@example.com" -ForegroundColor Gray
    Write-Host "  .\deploy.ps1 -Environment prod -Region us-west-2 -CostAlertEmail admin@example.com" -ForegroundColor Gray
    Write-Host "  .\deploy.ps1 -StackName my-healthcare-stack -CostThreshold 50 -CostAlertEmail admin@example.com" -ForegroundColor Gray
}

# Function to check if AWS CLI is installed and configured
function Test-AwsCli {
    try {
        $null = Get-Command aws -ErrorAction Stop
        $null = aws sts get-caller-identity 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "AWS CLI not configured"
        }
        Write-Success "AWS CLI is installed and configured"
        return $true
    }
    catch {
        Write-Error "AWS CLI is not installed or configured. Please install AWS CLI and run 'aws configure' first."
        return $false
    }
}

# Function to validate parameters
function Test-Parameters {
    if ([string]::IsNullOrEmpty($CostAlertEmail)) {
        $CostAlertEmail = Read-Host "Enter email address for cost alerts"
        if ([string]::IsNullOrEmpty($CostAlertEmail)) {
            Write-Error "Email address is required for cost alerts"
            return $false
        }
    }

    # Validate email format
    $emailRegex = '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    if ($CostAlertEmail -notmatch $emailRegex) {
        Write-Error "Invalid email format"
        return $false
    }

    Write-Success "Parameters validated"
    return $true
}

# Function to check if stack exists
function Test-StackExists {
    param([string]$StackName)
    try {
        $null = aws cloudformation describe-stacks --stack-name $StackName --region $Region 2>$null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

# Function to deploy CloudFormation stack
function Deploy-Stack {
    param(
        [string]$StackName,
        [string]$Operation
    )
    
    Write-Status "Starting CloudFormation $Operation for stack: $StackName"
    
    $parameters = @(
        "ParameterKey=Environment,ParameterValue=$Environment",
        "ParameterKey=CostAlertEmail,ParameterValue=$CostAlertEmail",
        "ParameterKey=CostThreshold,ParameterValue=$CostThreshold"
    )
    
    $tags = @(
        "Key=Project,Value=HealthcareAI",
        "Key=Environment,Value=$Environment",
        "Key=CostCenter,Value=Development"
    )
    
    try {
        if ($Operation -eq "create") {
            aws cloudformation create-stack `
                --stack-name $StackName `
                --template-body "file://$TemplateFile" `
                --parameters $parameters `
                --capabilities CAPABILITY_NAMED_IAM `
                --region $Region `
                --tags $tags
        } else {
            aws cloudformation update-stack `
                --stack-name $StackName `
                --template-body "file://$TemplateFile" `
                --parameters $parameters `
                --capabilities CAPABILITY_NAMED_IAM `
                --region $Region
        }
        
        if ($LASTEXITCODE -ne 0) {
            throw "CloudFormation $Operation command failed"
        }
        
        return $true
    }
    catch {
        Write-Error "Failed to start CloudFormation $Operation"
        return $false
    }
}

# Function to wait for stack operation to complete
function Wait-ForStack {
    param(
        [string]$StackName,
        [string]$Operation
    )
    
    Write-Status "Waiting for stack $Operation to complete..."
    
    try {
        if ($Operation -eq "create") {
            aws cloudformation wait stack-create-complete --stack-name $StackName --region $Region
        } else {
            aws cloudformation wait stack-update-complete --stack-name $StackName --region $Region
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Stack $Operation completed successfully"
            return $true
        } else {
            Write-Error "Stack $Operation failed"
            return $false
        }
    }
    catch {
        Write-Error "Error waiting for stack $Operation to complete"
        return $false
    }
}

# Function to get stack output value
function Get-StackOutput {
    param(
        [string]$StackName,
        [string]$OutputKey
    )
    
    try {
        $output = aws cloudformation describe-stacks `
            --stack-name $StackName `
            --region $Region `
            --query "Stacks[0].Outputs[?OutputKey=='$OutputKey'].OutputValue" `
            --output text 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            return $output
        } else {
            return ""
        }
    }
    catch {
        return ""
    }
}

# Function to display deployment summary
function Show-DeploymentSummary {
    param([string]$StackName)
    
    Write-Success "Deployment completed successfully!"
    Write-Host ""
    Write-Host "=== DEPLOYMENT SUMMARY ===" -ForegroundColor Cyan
    Write-Host "Stack Name: $StackName" -ForegroundColor White
    Write-Host "Region: $Region" -ForegroundColor White
    Write-Host "Environment: $Environment" -ForegroundColor White
    Write-Host ""
    
    # Get important outputs
    $apiUrl = Get-StackOutput -StackName $StackName -OutputKey "APIGatewayURL"
    $cloudfrontUrl = Get-StackOutput -StackName $StackName -OutputKey "CloudFrontURL"
    $websiteBucket = Get-StackOutput -StackName $StackName -OutputKey "WebsiteBucketName"
    
    Write-Host "=== IMPORTANT URLS ===" -ForegroundColor Cyan
    Write-Host "API Endpoint: $apiUrl" -ForegroundColor White
    Write-Host "Frontend URL: $cloudfrontUrl" -ForegroundColor White
    Write-Host ""
    Write-Host "=== NEXT STEPS ===" -ForegroundColor Cyan
    Write-Host "1. Upload your Live2D frontend files to S3 bucket: $websiteBucket" -ForegroundColor White
    Write-Host "2. Update your frontend configuration to use the API endpoint: $apiUrl" -ForegroundColor White
    Write-Host "3. Deploy your Lambda function code (see tasks 2-6 in the implementation plan)" -ForegroundColor White
    Write-Host "4. Test the system functionality" -ForegroundColor White
    Write-Host ""
    Write-Host "=== COST MONITORING ===" -ForegroundColor Cyan
    Write-Host "- Cost alerts configured for: $CostAlertEmail" -ForegroundColor White
    Write-Host "- Alert threshold: `$$CostThreshold USD/month" -ForegroundColor White
    Write-Host "- Estimated cost for light usage: `$5-10 USD/month" -ForegroundColor White
    Write-Host ""
    Write-Host "=== USEFUL COMMANDS ===" -ForegroundColor Cyan
    Write-Host "View stack details: aws cloudformation describe-stacks --stack-name $StackName --region $Region" -ForegroundColor Gray
    Write-Host "View stack events: aws cloudformation describe-stack-events --stack-name $StackName --region $Region" -ForegroundColor Gray
    Write-Host "Delete stack: aws cloudformation delete-stack --stack-name $StackName --region $Region" -ForegroundColor Gray
}

# Main function
function Main {
    Write-Host "=== Healthcare AI Live2D System - AWS Deployment ===" -ForegroundColor Cyan
    Write-Host ""
    
    # Show help if requested
    if ($Help) {
        Show-Help
        return
    }
    
    # Check prerequisites
    if (-not (Test-AwsCli)) {
        return
    }
    
    if (-not (Test-Parameters)) {
        return
    }
    
    # Check if template file exists
    if (-not (Test-Path $TemplateFile)) {
        Write-Error "CloudFormation template file not found: $TemplateFile"
        return
    }
    
    # Determine operation (create or update)
    $operation = "create"
    if (Test-StackExists -StackName $StackName) {
        $operation = "update"
        Write-Warning "Stack already exists. Will perform update operation."
    }
    
    # Deploy the stack
    if (-not (Deploy-Stack -StackName $StackName -Operation $operation)) {
        return
    }
    
    if (-not (Wait-ForStack -StackName $StackName -Operation $operation)) {
        return
    }
    
    # Display results
    Show-DeploymentSummary -StackName $StackName
}

# Run main function
Main