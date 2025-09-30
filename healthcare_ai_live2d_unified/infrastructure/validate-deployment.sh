#!/bin/bash

# Healthcare AI Live2D System - Deployment Validation Script
# This script validates that the deployed infrastructure is working correctly

set -e

# Configuration
STACK_NAME="healthcare-ai-live2d"
REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to get stack output
get_stack_output() {
    local output_key="$1"
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null
}

# Function to test HTTP endpoint
test_http_endpoint() {
    local url="$1"
    local description="$2"
    
    print_status "Testing $description: $url"
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|404"; then
        print_success "$description is accessible"
        return 0
    else
        print_error "$description is not accessible"
        return 1
    fi
}

# Function to test API endpoint
test_api_endpoint() {
    local api_url="$1"
    local endpoint="$2"
    local description="$3"
    
    local full_url="${api_url}${endpoint}"
    print_status "Testing $description: $full_url"
    
    local response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{"message": "test", "conversation_id": "test123"}' \
        "$full_url")
    
    local http_code="${response: -3}"
    
    if [[ "$http_code" =~ ^[2-4][0-9][0-9]$ ]]; then
        print_success "$description responded with HTTP $http_code"
        return 0
    else
        print_error "$description failed with HTTP $http_code"
        return 1
    fi
}

# Function to test DynamoDB table
test_dynamodb_table() {
    local table_name="$1"
    local description="$2"
    
    print_status "Testing $description: $table_name"
    
    if aws dynamodb describe-table --table-name "$table_name" --region "$REGION" >/dev/null 2>&1; then
        print_success "$description is accessible"
        return 0
    else
        print_error "$description is not accessible"
        return 1
    fi
}

# Function to test S3 bucket
test_s3_bucket() {
    local bucket_name="$1"
    local description="$2"
    
    print_status "Testing $description: $bucket_name"
    
    if aws s3 ls "s3://$bucket_name" >/dev/null 2>&1; then
        print_success "$description is accessible"
        return 0
    else
        print_error "$description is not accessible"
        return 1
    fi
}

# Function to test Lambda function
test_lambda_function() {
    local function_name="$1"
    local description="$2"
    
    print_status "Testing $description: $function_name"
    
    local response=$(aws lambda invoke \
        --function-name "$function_name" \
        --region "$REGION" \
        --payload '{"test": true}' \
        --output json \
        /tmp/lambda-response.json 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        local status_code=$(echo "$response" | jq -r '.StatusCode // empty')
        if [ "$status_code" = "200" ]; then
            print_success "$description executed successfully"
            return 0
        else
            print_error "$description failed with status code: $status_code"
            return 1
        fi
    else
        print_error "$description is not accessible"
        return 1
    fi
}

# Main validation function
main() {
    echo "=== Healthcare AI Live2D System - Deployment Validation ==="
    echo ""
    
    # Check if stack exists
    print_status "Checking if CloudFormation stack exists..."
    if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" >/dev/null 2>&1; then
        print_error "CloudFormation stack '$STACK_NAME' not found in region '$REGION'"
        exit 1
    fi
    print_success "CloudFormation stack found"
    
    # Get stack outputs
    print_status "Retrieving stack outputs..."
    local api_url=$(get_stack_output "APIGatewayURL")
    local cloudfront_url=$(get_stack_output "CloudFrontURL")
    local website_bucket=$(get_stack_output "WebsiteBucketName")
    local data_bucket=$(get_stack_output "DataBucketName")
    local conversations_table=$(get_stack_output "ConversationsTableName")
    local users_table=$(get_stack_output "UserProfilesTableName")
    
    if [ -z "$api_url" ] || [ -z "$cloudfront_url" ] || [ -z "$website_bucket" ]; then
        print_error "Failed to retrieve required stack outputs"
        exit 1
    fi
    print_success "Stack outputs retrieved"
    
    echo ""
    echo "=== TESTING INFRASTRUCTURE COMPONENTS ==="
    echo ""
    
    # Test S3 buckets
    test_s3_bucket "$website_bucket" "Website S3 Bucket"
    test_s3_bucket "$data_bucket" "Data S3 Bucket"
    
    # Test DynamoDB tables
    test_dynamodb_table "$conversations_table" "Conversations DynamoDB Table"
    test_dynamodb_table "$users_table" "Users DynamoDB Table"
    
    # Test CloudFront distribution
    test_http_endpoint "$cloudfront_url" "CloudFront Distribution"
    
    # Test API Gateway endpoints
    test_api_endpoint "$api_url" "/chat" "Chat API Endpoint"
    test_api_endpoint "$api_url" "/speech" "Speech API Endpoint"
    test_api_endpoint "$api_url" "/upload" "Upload API Endpoint"
    
    # Test Lambda functions
    local environment=$(echo "$conversations_table" | cut -d'-' -f1)
    test_lambda_function "${environment}-healthcare-agent-router" "Agent Router Lambda"
    test_lambda_function "${environment}-healthcare-illness-monitor" "Illness Monitor Lambda"
    test_lambda_function "${environment}-healthcare-mental-health" "Mental Health Lambda"
    test_lambda_function "${environment}-healthcare-safety-guardian" "Safety Guardian Lambda"
    test_lambda_function "${environment}-healthcare-wellness-coach" "Wellness Coach Lambda"
    test_lambda_function "${environment}-healthcare-speech-processor" "Speech Processor Lambda"
    test_lambda_function "${environment}-healthcare-file-processor" "File Processor Lambda"
    
    echo ""
    echo "=== VALIDATION SUMMARY ==="
    echo ""
    print_success "Infrastructure validation completed"
    echo ""
    echo "Key URLs:"
    echo "  API Gateway: $api_url"
    echo "  CloudFront:  $cloudfront_url"
    echo ""
    echo "Next steps:"
    echo "1. Upload frontend files to S3 bucket: $website_bucket"
    echo "2. Update frontend configuration with API URL: $api_url"
    echo "3. Deploy actual Lambda function code (currently using placeholders)"
    echo "4. Test end-to-end functionality"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -s, --stack-name NAME     CloudFormation stack name [default: healthcare-ai-live2d]"
            echo "  -r, --region REGION       AWS region [default: us-east-1]"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check prerequisites
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    print_error "curl is not installed"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    print_warning "jq is not installed - Lambda function testing may be limited"
fi

# Run main validation
main "$@"