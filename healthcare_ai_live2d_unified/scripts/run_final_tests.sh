#!/bin/bash

# Healthcare AI Live2D System - Final Integration Testing Script
# This script runs comprehensive tests and generates final reports

set -e

# Configuration
ENVIRONMENT="${ENVIRONMENT:-test}"
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${STACK_NAME:-healthcare-ai-${ENVIRONMENT}}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="${PROJECT_ROOT}/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    for tool in aws python3 curl jq; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_status "Please install the missing tools and try again"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured or invalid"
        print_status "Please configure AWS credentials using 'aws configure' or environment variables"
        exit 1
    fi
    
    # Check Python dependencies
    if ! python3 -c "import boto3, requests" &> /dev/null; then
        print_warning "Some Python dependencies may be missing"
        print_status "Installing required Python packages..."
        pip3 install boto3 requests --quiet || {
            print_error "Failed to install Python dependencies"
            exit 1
        }
    fi
    
    print_success "Prerequisites check completed"
}

# Function to create reports directory
setup_reports_directory() {
    print_status "Setting up reports directory..."
    
    mkdir -p "$REPORTS_DIR"
    
    # Create subdirectories for different types of reports
    mkdir -p "$REPORTS_DIR/deployment"
    mkdir -p "$REPORTS_DIR/testing"
    mkdir -p "$REPORTS_DIR/cost_analysis"
    mkdir -p "$REPORTS_DIR/final"
    
    print_success "Reports directory created: $REPORTS_DIR"
}

# Function to validate deployment
validate_deployment() {
    print_header "STEP 1: DEPLOYMENT VALIDATION"
    
    local validation_script="${PROJECT_ROOT}/infrastructure/validate-deployment.sh"
    local validation_report="${REPORTS_DIR}/deployment/validation_${TIMESTAMP}.json"
    
    if [ ! -f "$validation_script" ]; then
        print_error "Deployment validation script not found: $validation_script"
        return 1
    fi
    
    print_status "Running deployment validation..."
    
    # Run validation script and capture output
    if bash "$validation_script" \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" > "${validation_report}.log" 2>&1; then
        
        print_success "Deployment validation completed successfully"
        
        # Create JSON report
        cat > "$validation_report" << EOF
{
    "validation_status": "PASSED",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT",
    "stack_name": "$STACK_NAME",
    "aws_region": "$AWS_REGION",
    "log_file": "${validation_report}.log"
}
EOF
        
        return 0
    else
        print_error "Deployment validation failed"
        
        # Create JSON report for failure
        cat > "$validation_report" << EOF
{
    "validation_status": "FAILED",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT",
    "stack_name": "$STACK_NAME",
    "aws_region": "$AWS_REGION",
    "log_file": "${validation_report}.log",
    "error": "Deployment validation failed - check log file for details"
}
EOF
        
        return 1
    fi
}

# Function to run comprehensive integration tests
run_integration_tests() {
    print_header "STEP 2: COMPREHENSIVE INTEGRATION TESTING"
    
    local test_script="${PROJECT_ROOT}/tests/final_integration_test.py"
    local test_report="${REPORTS_DIR}/testing/integration_test_${TIMESTAMP}.json"
    
    if [ ! -f "$test_script" ]; then
        print_error "Integration test script not found: $test_script"
        return 1
    fi
    
    print_status "Running comprehensive integration tests..."
    
    # Set Python path
    export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/tests:${PROJECT_ROOT}/src:$PYTHONPATH"
    
    # Run integration tests
    if python3 "$test_script" \
        --environment "$ENVIRONMENT" \
        --region "$AWS_REGION" \
        --stack-name "$STACK_NAME" \
        --output "$test_report" \
        --timeout 30 \
        --parallel 5; then
        
        print_success "Integration tests completed successfully"
        return 0
    else
        print_error "Integration tests failed"
        return 1
    fi
}

# Function to run cost analysis
run_cost_analysis() {
    print_header "STEP 3: COST ANALYSIS AND OPTIMIZATION"
    
    local cost_script="${PROJECT_ROOT}/scripts/cost_analysis.py"
    local cost_report="${REPORTS_DIR}/cost_analysis/cost_analysis_${TIMESTAMP}.json"
    
    if [ ! -f "$cost_script" ]; then
        print_error "Cost analysis script not found: $cost_script"
        return 1
    fi
    
    print_status "Running cost analysis..."
    
    # Run cost analysis
    if python3 "$cost_script" \
        --environment "$ENVIRONMENT" \
        --region "$AWS_REGION" \
        --days 30 \
        --output "$cost_report"; then
        
        print_success "Cost analysis completed successfully"
        return 0
    else
        print_warning "Cost analysis completed with warnings (this is normal for new deployments)"
        return 0  # Don't fail the entire process for cost analysis issues
    fi
}

# Function to test specific agent functionality
test_agent_functionality() {
    print_header "STEP 4: HEALTHCARE AGENT FUNCTIONALITY TESTING"
    
    local agent_test_report="${REPORTS_DIR}/testing/agent_functionality_${TIMESTAMP}.json"
    
    print_status "Testing individual healthcare agents..."
    
    # Get API Gateway URL from CloudFormation stack
    local api_url
    api_url=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='APIGatewayURL'].OutputValue" \
        --output text 2>/dev/null)
    
    if [ -z "$api_url" ] || [ "$api_url" = "None" ]; then
        print_error "Could not retrieve API Gateway URL from stack outputs"
        return 1
    fi
    
    print_status "API Gateway URL: $api_url"
    
    # Test messages for each agent
    declare -A test_messages=(
        ["illness_monitor"]="I have a headache and feel dizzy"
        ["mental_health"]="I'm feeling really stressed about school"
        ["safety_guardian"]="I'm having chest pain and can't breathe"
        ["wellness_coach"]="How can I start exercising?"
    )
    
    local test_results=()
    local total_tests=0
    local passed_tests=0
    
    for agent in "${!test_messages[@]}"; do
        local message="${test_messages[$agent]}"
        print_status "Testing $agent agent with message: '$message'"
        
        # Make API request
        local response
        local http_code
        
        response=$(curl -s -w "%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{\"message\": \"$message\", \"user_id\": \"test_user\", \"conversation_id\": \"test_$(date +%s)\"}" \
            "$api_url/chat")
        
        http_code="${response: -3}"
        response_body="${response%???}"
        
        total_tests=$((total_tests + 1))
        
        if [ "$http_code" = "200" ]; then
            print_success "$agent agent test passed (HTTP $http_code)"
            passed_tests=$((passed_tests + 1))
            
            test_results+=("{\"agent\": \"$agent\", \"status\": \"PASSED\", \"http_code\": $http_code, \"message\": \"$message\"}")
        else
            print_error "$agent agent test failed (HTTP $http_code)"
            test_results+=("{\"agent\": \"$agent\", \"status\": \"FAILED\", \"http_code\": $http_code, \"message\": \"$message\", \"error\": \"HTTP $http_code\"}")
        fi
        
        # Small delay between tests
        sleep 1
    done
    
    # Create test report
    local success_rate=$((passed_tests * 100 / total_tests))
    
    cat > "$agent_test_report" << EOF
{
    "test_type": "agent_functionality",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT",
    "api_url": "$api_url",
    "summary": {
        "total_tests": $total_tests,
        "passed_tests": $passed_tests,
        "failed_tests": $((total_tests - passed_tests)),
        "success_rate": $success_rate
    },
    "test_results": [
        $(IFS=','; echo "${test_results[*]}")
    ]
}
EOF
    
    print_status "Agent functionality test results:"
    print_status "  Total tests: $total_tests"
    print_status "  Passed: $passed_tests"
    print_status "  Failed: $((total_tests - passed_tests))"
    print_status "  Success rate: $success_rate%"
    
    if [ $success_rate -ge 75 ]; then
        print_success "Agent functionality tests passed (≥75% success rate)"
        return 0
    else
        print_error "Agent functionality tests failed (<75% success rate)"
        return 1
    fi
}

# Function to test Live2D frontend
test_live2d_frontend() {
    print_header "STEP 5: LIVE2D FRONTEND TESTING"
    
    local frontend_test_report="${REPORTS_DIR}/testing/frontend_test_${TIMESTAMP}.json"
    
    print_status "Testing Live2D frontend accessibility..."
    
    # Get CloudFront URL from CloudFormation stack
    local cloudfront_url
    cloudfront_url=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='CloudFrontURL'].OutputValue" \
        --output text 2>/dev/null)
    
    if [ -z "$cloudfront_url" ] || [ "$cloudfront_url" = "None" ]; then
        print_error "Could not retrieve CloudFront URL from stack outputs"
        return 1
    fi
    
    print_status "CloudFront URL: $cloudfront_url"
    
    # Test frontend accessibility
    local frontend_tests=()
    local total_frontend_tests=0
    local passed_frontend_tests=0
    
    # Test main page
    print_status "Testing main page accessibility..."
    local main_response
    main_response=$(curl -s -w "%{http_code}" "$cloudfront_url/")
    local main_http_code="${main_response: -3}"
    
    total_frontend_tests=$((total_frontend_tests + 1))
    
    if [ "$main_http_code" = "200" ]; then
        print_success "Main page accessible (HTTP $main_http_code)"
        passed_frontend_tests=$((passed_frontend_tests + 1))
        frontend_tests+=("{\"test\": \"main_page\", \"status\": \"PASSED\", \"http_code\": $main_http_code}")
    else
        print_error "Main page not accessible (HTTP $main_http_code)"
        frontend_tests+=("{\"test\": \"main_page\", \"status\": \"FAILED\", \"http_code\": $main_http_code}")
    fi
    
    # Test static assets
    local assets=("assets/css/style.css" "assets/js/main.js" "config/aws-config.js")
    
    for asset in "${assets[@]}"; do
        print_status "Testing asset: $asset"
        local asset_response
        asset_response=$(curl -s -w "%{http_code}" "$cloudfront_url/$asset")
        local asset_http_code="${asset_response: -3}"
        
        total_frontend_tests=$((total_frontend_tests + 1))
        
        if [ "$asset_http_code" = "200" ]; then
            print_success "Asset $asset accessible (HTTP $asset_http_code)"
            passed_frontend_tests=$((passed_frontend_tests + 1))
            frontend_tests+=("{\"test\": \"$asset\", \"status\": \"PASSED\", \"http_code\": $asset_http_code}")
        else
            print_warning "Asset $asset not accessible (HTTP $asset_http_code) - may not be deployed yet"
            frontend_tests+=("{\"test\": \"$asset\", \"status\": \"FAILED\", \"http_code\": $asset_http_code}")
        fi
    done
    
    # Create frontend test report
    local frontend_success_rate=$((passed_frontend_tests * 100 / total_frontend_tests))
    
    cat > "$frontend_test_report" << EOF
{
    "test_type": "live2d_frontend",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT",
    "cloudfront_url": "$cloudfront_url",
    "summary": {
        "total_tests": $total_frontend_tests,
        "passed_tests": $passed_frontend_tests,
        "failed_tests": $((total_frontend_tests - passed_frontend_tests)),
        "success_rate": $frontend_success_rate
    },
    "test_results": [
        $(IFS=','; echo "${frontend_tests[*]}")
    ]
}
EOF
    
    print_status "Frontend test results:"
    print_status "  Total tests: $total_frontend_tests"
    print_status "  Passed: $passed_frontend_tests"
    print_status "  Failed: $((total_frontend_tests - passed_frontend_tests))"
    print_status "  Success rate: $frontend_success_rate%"
    
    if [ $frontend_success_rate -ge 50 ]; then
        print_success "Frontend tests passed (≥50% success rate)"
        return 0
    else
        print_error "Frontend tests failed (<50% success rate)"
        return 1
    fi
}

# Function to generate final comprehensive report
generate_final_report() {
    print_header "STEP 6: GENERATING FINAL COMPREHENSIVE REPORT"
    
    local final_report="${REPORTS_DIR}/final/final_integration_report_${TIMESTAMP}.json"
    local final_summary="${REPORTS_DIR}/final/final_summary_${TIMESTAMP}.txt"
    
    print_status "Generating final comprehensive report..."
    
    # Collect all test results
    local validation_status="UNKNOWN"
    local integration_status="UNKNOWN"
    local cost_analysis_status="UNKNOWN"
    local agent_status="UNKNOWN"
    local frontend_status="UNKNOWN"
    
    # Check validation results
    local validation_file="${REPORTS_DIR}/deployment/validation_${TIMESTAMP}.json"
    if [ -f "$validation_file" ]; then
        validation_status=$(jq -r '.validation_status // "UNKNOWN"' "$validation_file" 2>/dev/null || echo "UNKNOWN")
    fi
    
    # Check integration test results
    local integration_file="${REPORTS_DIR}/testing/integration_test_${TIMESTAMP}.json"
    if [ -f "$integration_file" ]; then
        local integration_success_rate
        integration_success_rate=$(jq -r '.test_results.summary.success_rate // 0' "$integration_file" 2>/dev/null || echo "0")
        if [ "$(echo "$integration_success_rate >= 80" | bc -l 2>/dev/null || echo "0")" = "1" ]; then
            integration_status="PASSED"
        else
            integration_status="FAILED"
        fi
    fi
    
    # Check cost analysis results
    local cost_file="${REPORTS_DIR}/cost_analysis/cost_analysis_${TIMESTAMP}.json"
    if [ -f "$cost_file" ]; then
        cost_analysis_status="COMPLETED"
    fi
    
    # Check agent test results
    local agent_file="${REPORTS_DIR}/testing/agent_functionality_${TIMESTAMP}.json"
    if [ -f "$agent_file" ]; then
        local agent_success_rate
        agent_success_rate=$(jq -r '.summary.success_rate // 0' "$agent_file" 2>/dev/null || echo "0")
        if [ "$agent_success_rate" -ge 75 ]; then
            agent_status="PASSED"
        else
            agent_status="FAILED"
        fi
    fi
    
    # Check frontend test results
    local frontend_file="${REPORTS_DIR}/testing/frontend_test_${TIMESTAMP}.json"
    if [ -f "$frontend_file" ]; then
        local frontend_success_rate
        frontend_success_rate=$(jq -r '.summary.success_rate // 0' "$frontend_file" 2>/dev/null || echo "0")
        if [ "$frontend_success_rate" -ge 50 ]; then
            frontend_status="PASSED"
        else
            frontend_status="FAILED"
        fi
    fi
    
    # Determine overall status
    local overall_status="FAILED"
    local passed_components=0
    local total_components=5
    
    for status in "$validation_status" "$integration_status" "$agent_status" "$frontend_status"; do
        if [ "$status" = "PASSED" ]; then
            passed_components=$((passed_components + 1))
        fi
    done
    
    if [ "$cost_analysis_status" = "COMPLETED" ]; then
        passed_components=$((passed_components + 1))
    fi
    
    if [ $passed_components -ge 4 ]; then
        overall_status="PASSED"
    elif [ $passed_components -ge 3 ]; then
        overall_status="PARTIAL"
    fi
    
    # Get deployment URLs
    local api_url
    local cloudfront_url
    
    api_url=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='APIGatewayURL'].OutputValue" \
        --output text 2>/dev/null || echo "N/A")
    
    cloudfront_url=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='CloudFrontURL'].OutputValue" \
        --output text 2>/dev/null || echo "N/A")
    
    # Create final JSON report
    cat > "$final_report" << EOF
{
    "final_integration_test_report": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "environment": "$ENVIRONMENT",
        "aws_region": "$AWS_REGION",
        "stack_name": "$STACK_NAME",
        "overall_status": "$overall_status",
        "component_results": {
            "deployment_validation": "$validation_status",
            "integration_testing": "$integration_status",
            "cost_analysis": "$cost_analysis_status",
            "agent_functionality": "$agent_status",
            "frontend_testing": "$frontend_status"
        },
        "deployment_urls": {
            "api_gateway": "$api_url",
            "cloudfront": "$cloudfront_url"
        },
        "report_files": {
            "validation": "$validation_file",
            "integration_test": "$integration_file",
            "cost_analysis": "$cost_file",
            "agent_functionality": "$agent_file",
            "frontend_test": "$frontend_file"
        },
        "summary": {
            "total_components": $total_components,
            "passed_components": $passed_components,
            "success_rate": $((passed_components * 100 / total_components))
        }
    }
}
EOF
    
    # Create human-readable summary
    cat > "$final_summary" << EOF
Healthcare AI Live2D System - Final Integration Test Summary
===========================================================

Test Execution: $(date)
Environment: $ENVIRONMENT
AWS Region: $AWS_REGION
Stack Name: $STACK_NAME

OVERALL STATUS: $overall_status

Component Test Results:
-----------------------
✓ Deployment Validation: $validation_status
✓ Integration Testing: $integration_status
✓ Cost Analysis: $cost_analysis_status
✓ Agent Functionality: $agent_status
✓ Frontend Testing: $frontend_status

Success Rate: $((passed_components * 100 / total_components))% ($passed_components/$total_components components passed)

Deployment URLs:
----------------
API Gateway: $api_url
CloudFront: $cloudfront_url

Report Files:
-------------
Final Report: $final_report
Summary: $final_summary
Validation: $validation_file
Integration Test: $integration_file
Cost Analysis: $cost_file
Agent Functionality: $agent_file
Frontend Test: $frontend_file

EOF
    
    # Add recommendations based on results
    cat >> "$final_summary" << EOF
Recommendations:
----------------
EOF
    
    if [ "$overall_status" = "PASSED" ]; then
        cat >> "$final_summary" << EOF
✅ System is ready for production use
📊 Set up regular monitoring and cost reviews
🔄 Implement automated testing in CI/CD pipeline
📚 Update documentation with deployment URLs
👥 Train users on the new AWS-based system
EOF
    elif [ "$overall_status" = "PARTIAL" ]; then
        cat >> "$final_summary" << EOF
⚠️  System has some issues but core functionality works
🔍 Review failed components and address issues
🛠️ Consider deploying with current functionality while fixing issues
📋 Monitor system closely after deployment
EOF
    else
        cat >> "$final_summary" << EOF
❌ System has significant issues and should not be deployed
🔍 Review all failed components and error logs
🛠️ Fix critical issues before attempting deployment
🔄 Re-run tests after fixes are implemented
EOF
    fi
    
    print_success "Final comprehensive report generated"
    print_status "Final report: $final_report"
    print_status "Summary: $final_summary"
    
    return 0
}

# Function to display final results
display_final_results() {
    print_header "FINAL INTEGRATION TEST RESULTS"
    
    local final_summary="${REPORTS_DIR}/final/final_summary_${TIMESTAMP}.txt"
    
    if [ -f "$final_summary" ]; then
        cat "$final_summary"
    else
        print_error "Final summary not found"
        return 1
    fi
    
    print_header "TEST EXECUTION COMPLETED"
}

# Main execution function
main() {
    print_header "HEALTHCARE AI LIVE2D SYSTEM - FINAL INTEGRATION TESTING"
    
    print_status "Starting final integration testing process..."
    print_status "Environment: $ENVIRONMENT"
    print_status "AWS Region: $AWS_REGION"
    print_status "Stack Name: $STACK_NAME"
    print_status "Timestamp: $TIMESTAMP"
    
    # Track overall success
    local overall_success=true
    
    # Step 0: Prerequisites and setup
    check_prerequisites || { overall_success=false; }
    setup_reports_directory || { overall_success=false; }
    
    # Step 1: Validate deployment
    if ! validate_deployment; then
        print_warning "Deployment validation failed, but continuing with other tests..."
        overall_success=false
    fi
    
    # Step 2: Run integration tests
    if ! run_integration_tests; then
        print_warning "Integration tests failed, but continuing with other tests..."
        overall_success=false
    fi
    
    # Step 3: Run cost analysis
    if ! run_cost_analysis; then
        print_warning "Cost analysis had issues, but continuing with other tests..."
        # Don't set overall_success=false for cost analysis issues
    fi
    
    # Step 4: Test agent functionality
    if ! test_agent_functionality; then
        print_warning "Agent functionality tests failed, but continuing with other tests..."
        overall_success=false
    fi
    
    # Step 5: Test Live2D frontend
    if ! test_live2d_frontend; then
        print_warning "Frontend tests failed, but continuing with other tests..."
        overall_success=false
    fi
    
    # Step 6: Generate final report
    generate_final_report || { overall_success=false; }
    
    # Display results
    display_final_results
    
    # Return appropriate exit code
    if [ "$overall_success" = true ]; then
        print_success "🎉 Final integration testing completed successfully!"
        exit 0
    else
        print_error "❌ Final integration testing completed with failures"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -e, --environment ENV     Environment name [default: test]"
            echo "  -r, --region REGION       AWS region [default: us-east-1]"
            echo "  -s, --stack-name NAME     CloudFormation stack name [default: healthcare-ai-ENV]"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"