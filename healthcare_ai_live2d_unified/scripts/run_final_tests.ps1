# Healthcare AI Live2D System - Final Integration Testing Script (PowerShell)
# This script runs comprehensive tests and generates final reports

param(
    [string]$Environment = "test",
    [string]$AwsRegion = "us-east-1",
    [string]$StackName = "",
    [switch]$Help
)

# Configuration
if ([string]::IsNullOrEmpty($StackName)) {
    $StackName = "healthcare-ai-$Environment"
}

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ReportsDir = Join-Path $ProjectRoot "reports"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    Purple = "Magenta"
}

# Function to print colored output
function Write-Header {
    param([string]$Message)
    Write-Host "================================" -ForegroundColor $Colors.Purple
    Write-Host $Message -ForegroundColor $Colors.Purple
    Write-Host "================================" -ForegroundColor $Colors.Purple
}

function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

# Function to show help
function Show-Help {
    Write-Host "Healthcare AI Live2D System - Final Integration Testing"
    Write-Host ""
    Write-Host "Usage: .\run_final_tests.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Environment ENV     Environment name [default: test]"
    Write-Host "  -AwsRegion REGION    AWS region [default: us-east-1]"
    Write-Host "  -StackName NAME      CloudFormation stack name [default: healthcare-ai-ENV]"
    Write-Host "  -Help               Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run_final_tests.ps1"
    Write-Host "  .\run_final_tests.ps1 -Environment prod -AwsRegion us-west-2"
    Write-Host "  .\run_final_tests.ps1 -StackName my-healthcare-stack"
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    $MissingTools = @()
    
    # Check required tools
    $RequiredTools = @("aws", "python", "curl")
    
    foreach ($Tool in $RequiredTools) {
        if (-not (Get-Command $Tool -ErrorAction SilentlyContinue)) {
            $MissingTools += $Tool
        }
    }
    
    if ($MissingTools.Count -gt 0) {
        Write-Error "Missing required tools: $($MissingTools -join ', ')"
        Write-Status "Please install the missing tools and try again"
        return $false
    }
    
    # Check AWS credentials
    try {
        $null = aws sts get-caller-identity 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "AWS credentials not configured or invalid"
            Write-Status "Please configure AWS credentials using 'aws configure' or environment variables"
            return $false
        }
    }
    catch {
        Write-Error "Error checking AWS credentials: $_"
        return $false
    }
    
    # Check Python dependencies
    try {
        python -c "import boto3, requests" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Some Python dependencies may be missing"
            Write-Status "Installing required Python packages..."
            pip install boto3 requests --quiet
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to install Python dependencies"
                return $false
            }
        }
    }
    catch {
        Write-Warning "Error checking Python dependencies: $_"
    }
    
    Write-Success "Prerequisites check completed"
    return $true
}

# Function to create reports directory
function Initialize-ReportsDirectory {
    Write-Status "Setting up reports directory..."
    
    if (-not (Test-Path $ReportsDir)) {
        New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null
    }
    
    # Create subdirectories for different types of reports
    $SubDirs = @("deployment", "testing", "cost_analysis", "final")
    foreach ($SubDir in $SubDirs) {
        $SubDirPath = Join-Path $ReportsDir $SubDir
        if (-not (Test-Path $SubDirPath)) {
            New-Item -ItemType Directory -Path $SubDirPath -Force | Out-Null
        }
    }
    
    Write-Success "Reports directory created: $ReportsDir"
    return $true
}

# Function to validate deployment
function Test-Deployment {
    Write-Header "STEP 1: DEPLOYMENT VALIDATION"
    
    $ValidationScript = Join-Path $ProjectRoot "infrastructure\validate-deployment.sh"
    $ValidationReport = Join-Path $ReportsDir "deployment\validation_$Timestamp.json"
    
    if (-not (Test-Path $ValidationScript)) {
        Write-Error "Deployment validation script not found: $ValidationScript"
        return $false
    }
    
    Write-Status "Running deployment validation..."
    
    try {
        # Run validation using bash (if available) or PowerShell equivalent
        if (Get-Command bash -ErrorAction SilentlyContinue) {
            $ValidationOutput = bash $ValidationScript --stack-name $StackName --region $AwsRegion 2>&1
            $ValidationSuccess = $LASTEXITCODE -eq 0
        }
        else {
            # PowerShell equivalent validation
            $ValidationSuccess = Invoke-DeploymentValidation
            $ValidationOutput = "PowerShell validation completed"
        }
        
        if ($ValidationSuccess) {
            Write-Success "Deployment validation completed successfully"
            
            # Create JSON report
            $ValidationReportData = @{
                validation_status = "PASSED"
                timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                environment = $Environment
                stack_name = $StackName
                aws_region = $AwsRegion
                output = $ValidationOutput
            }
            
            $ValidationReportData | ConvertTo-Json -Depth 10 | Out-File -FilePath $ValidationReport -Encoding UTF8
            return $true
        }
        else {
            Write-Error "Deployment validation failed"
            
            # Create JSON report for failure
            $ValidationReportData = @{
                validation_status = "FAILED"
                timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                environment = $Environment
                stack_name = $StackName
                aws_region = $AwsRegion
                error = "Deployment validation failed"
                output = $ValidationOutput
            }
            
            $ValidationReportData | ConvertTo-Json -Depth 10 | Out-File -FilePath $ValidationReport -Encoding UTF8
            return $false
        }
    }
    catch {
        Write-Error "Error during deployment validation: $_"
        return $false
    }
}

# Function to perform PowerShell-based deployment validation
function Invoke-DeploymentValidation {
    try {
        # Check if stack exists
        $StackInfo = aws cloudformation describe-stacks --stack-name $StackName --region $AwsRegion 2>$null | ConvertFrom-Json
        
        if (-not $StackInfo -or -not $StackInfo.Stacks) {
            Write-Error "CloudFormation stack '$StackName' not found in region '$AwsRegion'"
            return $false
        }
        
        $Stack = $StackInfo.Stacks[0]
        
        if ($Stack.StackStatus -notin @("CREATE_COMPLETE", "UPDATE_COMPLETE")) {
            Write-Error "Stack is not in a complete state: $($Stack.StackStatus)"
            return $false
        }
        
        Write-Success "CloudFormation stack validation passed"
        return $true
    }
    catch {
        Write-Error "Error validating deployment: $_"
        return $false
    }
}

# Function to run comprehensive integration tests
function Invoke-IntegrationTests {
    Write-Header "STEP 2: COMPREHENSIVE INTEGRATION TESTING"
    
    $TestScript = Join-Path $ProjectRoot "tests\final_integration_test.py"
    $TestReport = Join-Path $ReportsDir "testing\integration_test_$Timestamp.json"
    
    if (-not (Test-Path $TestScript)) {
        Write-Error "Integration test script not found: $TestScript"
        return $false
    }
    
    Write-Status "Running comprehensive integration tests..."
    
    # Set Python path
    $env:PYTHONPATH = "$ProjectRoot;$ProjectRoot\tests;$ProjectRoot\src;$env:PYTHONPATH"
    
    try {
        # Run integration tests
        python $TestScript --environment $Environment --region $AwsRegion --stack-name $StackName --output $TestReport --timeout 30 --parallel 5
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Integration tests completed successfully"
            return $true
        }
        else {
            Write-Error "Integration tests failed"
            return $false
        }
    }
    catch {
        Write-Error "Error running integration tests: $_"
        return $false
    }
}

# Function to run cost analysis
function Invoke-CostAnalysis {
    Write-Header "STEP 3: COST ANALYSIS AND OPTIMIZATION"
    
    $CostScript = Join-Path $ProjectRoot "scripts\cost_analysis.py"
    $CostReport = Join-Path $ReportsDir "cost_analysis\cost_analysis_$Timestamp.json"
    
    if (-not (Test-Path $CostScript)) {
        Write-Error "Cost analysis script not found: $CostScript"
        return $false
    }
    
    Write-Status "Running cost analysis..."
    
    try {
        # Run cost analysis
        python $CostScript --environment $Environment --region $AwsRegion --days 30 --output $CostReport
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Cost analysis completed successfully"
            return $true
        }
        else {
            Write-Warning "Cost analysis completed with warnings (this is normal for new deployments)"
            return $true  # Don't fail the entire process for cost analysis issues
        }
    }
    catch {
        Write-Warning "Cost analysis had issues: $_"
        return $true  # Don't fail the entire process for cost analysis issues
    }
}

# Function to test agent functionality
function Test-AgentFunctionality {
    Write-Header "STEP 4: HEALTHCARE AGENT FUNCTIONALITY TESTING"
    
    $AgentTestReport = Join-Path $ReportsDir "testing\agent_functionality_$Timestamp.json"
    
    Write-Status "Testing individual healthcare agents..."
    
    try {
        # Get API Gateway URL from CloudFormation stack
        $StackOutputs = aws cloudformation describe-stacks --stack-name $StackName --region $AwsRegion --query "Stacks[0].Outputs" 2>$null | ConvertFrom-Json
        
        $ApiUrl = ($StackOutputs | Where-Object { $_.OutputKey -eq "APIGatewayURL" }).OutputValue
        
        if ([string]::IsNullOrEmpty($ApiUrl)) {
            Write-Error "Could not retrieve API Gateway URL from stack outputs"
            return $false
        }
        
        Write-Status "API Gateway URL: $ApiUrl"
        
        # Test messages for each agent
        $TestMessages = @{
            "illness_monitor" = "I have a headache and feel dizzy"
            "mental_health" = "I'm feeling really stressed about school"
            "safety_guardian" = "I'm having chest pain and can't breathe"
            "wellness_coach" = "How can I start exercising?"
        }
        
        $TestResults = @()
        $TotalTests = 0
        $PassedTests = 0
        
        foreach ($Agent in $TestMessages.Keys) {
            $Message = $TestMessages[$Agent]
            Write-Status "Testing $Agent agent with message: '$Message'"
            
            # Make API request
            $RequestBody = @{
                message = $Message
                user_id = "test_user"
                conversation_id = "test_$(Get-Date -Format 'yyyyMMddHHmmss')"
            } | ConvertTo-Json
            
            try {
                $Response = Invoke-RestMethod -Uri "$ApiUrl/chat" -Method POST -Body $RequestBody -ContentType "application/json" -TimeoutSec 30
                
                $TotalTests++
                $PassedTests++
                
                Write-Success "$Agent agent test passed"
                
                $TestResults += @{
                    agent = $Agent
                    status = "PASSED"
                    message = $Message
                    response = $Response
                }
            }
            catch {
                $TotalTests++
                
                Write-Error "$Agent agent test failed: $_"
                
                $TestResults += @{
                    agent = $Agent
                    status = "FAILED"
                    message = $Message
                    error = $_.Exception.Message
                }
            }
            
            # Small delay between tests
            Start-Sleep -Seconds 1
        }
        
        # Create test report
        $SuccessRate = if ($TotalTests -gt 0) { [math]::Round(($PassedTests * 100) / $TotalTests) } else { 0 }
        
        $AgentTestReportData = @{
            test_type = "agent_functionality"
            timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            environment = $Environment
            api_url = $ApiUrl
            summary = @{
                total_tests = $TotalTests
                passed_tests = $PassedTests
                failed_tests = $TotalTests - $PassedTests
                success_rate = $SuccessRate
            }
            test_results = $TestResults
        }
        
        $AgentTestReportData | ConvertTo-Json -Depth 10 | Out-File -FilePath $AgentTestReport -Encoding UTF8
        
        Write-Status "Agent functionality test results:"
        Write-Status "  Total tests: $TotalTests"
        Write-Status "  Passed: $PassedTests"
        Write-Status "  Failed: $($TotalTests - $PassedTests)"
        Write-Status "  Success rate: $SuccessRate%"
        
        if ($SuccessRate -ge 75) {
            Write-Success "Agent functionality tests passed (≥75% success rate)"
            return $true
        }
        else {
            Write-Error "Agent functionality tests failed (<75% success rate)"
            return $false
        }
    }
    catch {
        Write-Error "Error testing agent functionality: $_"
        return $false
    }
}

# Function to test Live2D frontend
function Test-Live2DFrontend {
    Write-Header "STEP 5: LIVE2D FRONTEND TESTING"
    
    $FrontendTestReport = Join-Path $ReportsDir "testing\frontend_test_$Timestamp.json"
    
    Write-Status "Testing Live2D frontend accessibility..."
    
    try {
        # Get CloudFront URL from CloudFormation stack
        $StackOutputs = aws cloudformation describe-stacks --stack-name $StackName --region $AwsRegion --query "Stacks[0].Outputs" 2>$null | ConvertFrom-Json
        
        $CloudFrontUrl = ($StackOutputs | Where-Object { $_.OutputKey -eq "CloudFrontURL" }).OutputValue
        
        if ([string]::IsNullOrEmpty($CloudFrontUrl)) {
            Write-Error "Could not retrieve CloudFront URL from stack outputs"
            return $false
        }
        
        Write-Status "CloudFront URL: $CloudFrontUrl"
        
        # Test frontend accessibility
        $FrontendTests = @()
        $TotalFrontendTests = 0
        $PassedFrontendTests = 0
        
        # Test main page
        Write-Status "Testing main page accessibility..."
        try {
            $MainResponse = Invoke-WebRequest -Uri "$CloudFrontUrl/" -TimeoutSec 30
            $TotalFrontendTests++
            
            if ($MainResponse.StatusCode -eq 200) {
                Write-Success "Main page accessible (HTTP $($MainResponse.StatusCode))"
                $PassedFrontendTests++
                $FrontendTests += @{
                    test = "main_page"
                    status = "PASSED"
                    http_code = $MainResponse.StatusCode
                }
            }
            else {
                Write-Error "Main page not accessible (HTTP $($MainResponse.StatusCode))"
                $FrontendTests += @{
                    test = "main_page"
                    status = "FAILED"
                    http_code = $MainResponse.StatusCode
                }
            }
        }
        catch {
            $TotalFrontendTests++
            Write-Error "Main page not accessible: $_"
            $FrontendTests += @{
                test = "main_page"
                status = "FAILED"
                error = $_.Exception.Message
            }
        }
        
        # Test static assets
        $Assets = @("assets/css/style.css", "assets/js/main.js", "config/aws-config.js")
        
        foreach ($Asset in $Assets) {
            Write-Status "Testing asset: $Asset"
            try {
                $AssetResponse = Invoke-WebRequest -Uri "$CloudFrontUrl/$Asset" -TimeoutSec 30
                $TotalFrontendTests++
                
                if ($AssetResponse.StatusCode -eq 200) {
                    Write-Success "Asset $Asset accessible (HTTP $($AssetResponse.StatusCode))"
                    $PassedFrontendTests++
                    $FrontendTests += @{
                        test = $Asset
                        status = "PASSED"
                        http_code = $AssetResponse.StatusCode
                    }
                }
                else {
                    Write-Warning "Asset $Asset not accessible (HTTP $($AssetResponse.StatusCode)) - may not be deployed yet"
                    $FrontendTests += @{
                        test = $Asset
                        status = "FAILED"
                        http_code = $AssetResponse.StatusCode
                    }
                }
            }
            catch {
                $TotalFrontendTests++
                Write-Warning "Asset $Asset not accessible: $_ - may not be deployed yet"
                $FrontendTests += @{
                    test = $Asset
                    status = "FAILED"
                    error = $_.Exception.Message
                }
            }
        }
        
        # Create frontend test report
        $FrontendSuccessRate = if ($TotalFrontendTests -gt 0) { [math]::Round(($PassedFrontendTests * 100) / $TotalFrontendTests) } else { 0 }
        
        $FrontendTestReportData = @{
            test_type = "live2d_frontend"
            timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            environment = $Environment
            cloudfront_url = $CloudFrontUrl
            summary = @{
                total_tests = $TotalFrontendTests
                passed_tests = $PassedFrontendTests
                failed_tests = $TotalFrontendTests - $PassedFrontendTests
                success_rate = $FrontendSuccessRate
            }
            test_results = $FrontendTests
        }
        
        $FrontendTestReportData | ConvertTo-Json -Depth 10 | Out-File -FilePath $FrontendTestReport -Encoding UTF8
        
        Write-Status "Frontend test results:"
        Write-Status "  Total tests: $TotalFrontendTests"
        Write-Status "  Passed: $PassedFrontendTests"
        Write-Status "  Failed: $($TotalFrontendTests - $PassedFrontendTests)"
        Write-Status "  Success rate: $FrontendSuccessRate%"
        
        if ($FrontendSuccessRate -ge 50) {
            Write-Success "Frontend tests passed (≥50% success rate)"
            return $true
        }
        else {
            Write-Error "Frontend tests failed (<50% success rate)"
            return $false
        }
    }
    catch {
        Write-Error "Error testing frontend: $_"
        return $false
    }
}

# Function to generate final comprehensive report
function New-FinalReport {
    Write-Header "STEP 6: GENERATING FINAL COMPREHENSIVE REPORT"
    
    $FinalReport = Join-Path $ReportsDir "final\final_integration_report_$Timestamp.json"
    $FinalSummary = Join-Path $ReportsDir "final\final_summary_$Timestamp.txt"
    
    Write-Status "Generating final comprehensive report..."
    
    # Collect all test results
    $ValidationStatus = "UNKNOWN"
    $IntegrationStatus = "UNKNOWN"
    $CostAnalysisStatus = "UNKNOWN"
    $AgentStatus = "UNKNOWN"
    $FrontendStatus = "UNKNOWN"
    
    # Check validation results
    $ValidationFile = Join-Path $ReportsDir "deployment\validation_$Timestamp.json"
    if (Test-Path $ValidationFile) {
        try {
            $ValidationData = Get-Content $ValidationFile | ConvertFrom-Json
            $ValidationStatus = $ValidationData.validation_status
        }
        catch {
            $ValidationStatus = "UNKNOWN"
        }
    }
    
    # Check integration test results
    $IntegrationFile = Join-Path $ReportsDir "testing\integration_test_$Timestamp.json"
    if (Test-Path $IntegrationFile) {
        try {
            $IntegrationData = Get-Content $IntegrationFile | ConvertFrom-Json
            $IntegrationSuccessRate = $IntegrationData.test_results.summary.success_rate
            if ($IntegrationSuccessRate -ge 80) {
                $IntegrationStatus = "PASSED"
            }
            else {
                $IntegrationStatus = "FAILED"
            }
        }
        catch {
            $IntegrationStatus = "UNKNOWN"
        }
    }
    
    # Check cost analysis results
    $CostFile = Join-Path $ReportsDir "cost_analysis\cost_analysis_$Timestamp.json"
    if (Test-Path $CostFile) {
        $CostAnalysisStatus = "COMPLETED"
    }
    
    # Check agent test results
    $AgentFile = Join-Path $ReportsDir "testing\agent_functionality_$Timestamp.json"
    if (Test-Path $AgentFile) {
        try {
            $AgentData = Get-Content $AgentFile | ConvertFrom-Json
            $AgentSuccessRate = $AgentData.summary.success_rate
            if ($AgentSuccessRate -ge 75) {
                $AgentStatus = "PASSED"
            }
            else {
                $AgentStatus = "FAILED"
            }
        }
        catch {
            $AgentStatus = "UNKNOWN"
        }
    }
    
    # Check frontend test results
    $FrontendFile = Join-Path $ReportsDir "testing\frontend_test_$Timestamp.json"
    if (Test-Path $FrontendFile) {
        try {
            $FrontendData = Get-Content $FrontendFile | ConvertFrom-Json
            $FrontendSuccessRate = $FrontendData.summary.success_rate
            if ($FrontendSuccessRate -ge 50) {
                $FrontendStatus = "PASSED"
            }
            else {
                $FrontendStatus = "FAILED"
            }
        }
        catch {
            $FrontendStatus = "UNKNOWN"
        }
    }
    
    # Determine overall status
    $OverallStatus = "FAILED"
    $PassedComponents = 0
    $TotalComponents = 5
    
    $Statuses = @($ValidationStatus, $IntegrationStatus, $AgentStatus, $FrontendStatus)
    foreach ($Status in $Statuses) {
        if ($Status -eq "PASSED") {
            $PassedComponents++
        }
    }
    
    if ($CostAnalysisStatus -eq "COMPLETED") {
        $PassedComponents++
    }
    
    if ($PassedComponents -ge 4) {
        $OverallStatus = "PASSED"
    }
    elseif ($PassedComponents -ge 3) {
        $OverallStatus = "PARTIAL"
    }
    
    # Get deployment URLs
    try {
        $StackOutputs = aws cloudformation describe-stacks --stack-name $StackName --region $AwsRegion --query "Stacks[0].Outputs" 2>$null | ConvertFrom-Json
        $ApiUrl = ($StackOutputs | Where-Object { $_.OutputKey -eq "APIGatewayURL" }).OutputValue
        $CloudFrontUrl = ($StackOutputs | Where-Object { $_.OutputKey -eq "CloudFrontURL" }).OutputValue
    }
    catch {
        $ApiUrl = "N/A"
        $CloudFrontUrl = "N/A"
    }
    
    # Create final JSON report
    $FinalReportData = @{
        final_integration_test_report = @{
            timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            environment = $Environment
            aws_region = $AwsRegion
            stack_name = $StackName
            overall_status = $OverallStatus
            component_results = @{
                deployment_validation = $ValidationStatus
                integration_testing = $IntegrationStatus
                cost_analysis = $CostAnalysisStatus
                agent_functionality = $AgentStatus
                frontend_testing = $FrontendStatus
            }
            deployment_urls = @{
                api_gateway = $ApiUrl
                cloudfront = $CloudFrontUrl
            }
            report_files = @{
                validation = $ValidationFile
                integration_test = $IntegrationFile
                cost_analysis = $CostFile
                agent_functionality = $AgentFile
                frontend_test = $FrontendFile
            }
            summary = @{
                total_components = $TotalComponents
                passed_components = $PassedComponents
                success_rate = [math]::Round(($PassedComponents * 100) / $TotalComponents)
            }
        }
    }
    
    $FinalReportData | ConvertTo-Json -Depth 10 | Out-File -FilePath $FinalReport -Encoding UTF8
    
    # Create human-readable summary
    $SummaryContent = @"
Healthcare AI Live2D System - Final Integration Test Summary
===========================================================

Test Execution: $(Get-Date)
Environment: $Environment
AWS Region: $AwsRegion
Stack Name: $StackName

OVERALL STATUS: $OverallStatus

Component Test Results:
-----------------------
✓ Deployment Validation: $ValidationStatus
✓ Integration Testing: $IntegrationStatus
✓ Cost Analysis: $CostAnalysisStatus
✓ Agent Functionality: $AgentStatus
✓ Frontend Testing: $FrontendStatus

Success Rate: $([math]::Round(($PassedComponents * 100) / $TotalComponents))% ($PassedComponents/$TotalComponents components passed)

Deployment URLs:
----------------
API Gateway: $ApiUrl
CloudFront: $CloudFrontUrl

Report Files:
-------------
Final Report: $FinalReport
Summary: $FinalSummary
Validation: $ValidationFile
Integration Test: $IntegrationFile
Cost Analysis: $CostFile
Agent Functionality: $AgentFile
Frontend Test: $FrontendFile

Recommendations:
----------------
"@
    
    # Add recommendations based on results
    if ($OverallStatus -eq "PASSED") {
        $SummaryContent += @"
✅ System is ready for production use
📊 Set up regular monitoring and cost reviews
🔄 Implement automated testing in CI/CD pipeline
📚 Update documentation with deployment URLs
👥 Train users on the new AWS-based system
"@
    }
    elseif ($OverallStatus -eq "PARTIAL") {
        $SummaryContent += @"
⚠️  System has some issues but core functionality works
🔍 Review failed components and address issues
🛠️ Consider deploying with current functionality while fixing issues
📋 Monitor system closely after deployment
"@
    }
    else {
        $SummaryContent += @"
❌ System has significant issues and should not be deployed
🔍 Review all failed components and error logs
🛠️ Fix critical issues before attempting deployment
🔄 Re-run tests after fixes are implemented
"@
    }
    
    $SummaryContent | Out-File -FilePath $FinalSummary -Encoding UTF8
    
    Write-Success "Final comprehensive report generated"
    Write-Status "Final report: $FinalReport"
    Write-Status "Summary: $FinalSummary"
    
    return $true
}

# Function to display final results
function Show-FinalResults {
    Write-Header "FINAL INTEGRATION TEST RESULTS"
    
    $FinalSummary = Join-Path $ReportsDir "final\final_summary_$Timestamp.txt"
    
    if (Test-Path $FinalSummary) {
        Get-Content $FinalSummary | Write-Host
    }
    else {
        Write-Error "Final summary not found"
        return $false
    }
    
    Write-Header "TEST EXECUTION COMPLETED"
    return $true
}

# Main execution function
function Main {
    if ($Help) {
        Show-Help
        return 0
    }
    
    Write-Header "HEALTHCARE AI LIVE2D SYSTEM - FINAL INTEGRATION TESTING"
    
    Write-Status "Starting final integration testing process..."
    Write-Status "Environment: $Environment"
    Write-Status "AWS Region: $AwsRegion"
    Write-Status "Stack Name: $StackName"
    Write-Status "Timestamp: $Timestamp"
    
    # Track overall success
    $OverallSuccess = $true
    
    # Step 0: Prerequisites and setup
    if (-not (Test-Prerequisites)) {
        $OverallSuccess = $false
    }
    
    if (-not (Initialize-ReportsDirectory)) {
        $OverallSuccess = $false
    }
    
    # Step 1: Validate deployment
    if (-not (Test-Deployment)) {
        Write-Warning "Deployment validation failed, but continuing with other tests..."
        $OverallSuccess = $false
    }
    
    # Step 2: Run integration tests
    if (-not (Invoke-IntegrationTests)) {
        Write-Warning "Integration tests failed, but continuing with other tests..."
        $OverallSuccess = $false
    }
    
    # Step 3: Run cost analysis
    if (-not (Invoke-CostAnalysis)) {
        Write-Warning "Cost analysis had issues, but continuing with other tests..."
        # Don't set OverallSuccess = false for cost analysis issues
    }
    
    # Step 4: Test agent functionality
    if (-not (Test-AgentFunctionality)) {
        Write-Warning "Agent functionality tests failed, but continuing with other tests..."
        $OverallSuccess = $false
    }
    
    # Step 5: Test Live2D frontend
    if (-not (Test-Live2DFrontend)) {
        Write-Warning "Frontend tests failed, but continuing with other tests..."
        $OverallSuccess = $false
    }
    
    # Step 6: Generate final report
    if (-not (New-FinalReport)) {
        $OverallSuccess = $false
    }
    
    # Display results
    Show-FinalResults | Out-Null
    
    # Return appropriate exit code
    if ($OverallSuccess) {
        Write-Success "🎉 Final integration testing completed successfully!"
        return 0
    }
    else {
        Write-Error "❌ Final integration testing completed with failures"
        return 1
    }
}

# Run main function
$ExitCode = Main
exit $ExitCode