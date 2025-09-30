# Final Integration Testing Guide

This document provides comprehensive guidance for running the final integration tests for the Healthcare AI Live2D system deployed on AWS.

## Overview

The final integration testing validates that the complete Healthcare AI system works correctly after deployment to AWS. It includes:

1. **Deployment Validation** - Verifies infrastructure is properly deployed
2. **Agent Functionality Testing** - Tests all four healthcare agents
3. **Live2D Frontend Testing** - Validates frontend accessibility and configuration
4. **Speech Functionality Testing** - Tests AWS Transcribe/Polly integration
5. **Cost Analysis** - Reviews costs and provides optimization recommendations
6. **Performance Testing** - Validates response times and concurrent handling
7. **Security Testing** - Checks security configurations
8. **Monitoring Testing** - Validates logging and alerting setup

## Prerequisites

### Required Tools

- **AWS CLI** - Configured with appropriate credentials
- **Python 3.8+** - With pip package manager
- **curl** - For HTTP testing
- **jq** (optional) - For JSON processing in bash scripts

### Python Dependencies

```bash
pip install boto3 requests pytest asyncio
```

### AWS Permissions

Your AWS credentials need the following permissions:

- CloudFormation: `describe-stacks`
- Lambda: `get-function`, `invoke`
- DynamoDB: `describe-table`
- S3: `list-bucket`, `get-object`
- API Gateway: `get-*`
- CloudWatch: `describe-alarms`, `get-metric-statistics`
- Cost Explorer: `get-cost-and-usage`

## Quick Start

### Option 1: Automated Testing Script (Recommended)

**Linux/macOS:**
```bash
cd healthcare_ai_live2d_unified
chmod +x scripts/run_final_tests.sh
./scripts/run_final_tests.sh --environment test --region us-east-1
```

**Windows PowerShell:**
```powershell
cd healthcare_ai_live2d_unified
.\scripts\run_final_tests.ps1 -Environment test -AwsRegion us-east-1
```

### Option 2: Manual Testing

```bash
# 1. Run deployment validation
./infrastructure/validate-deployment.sh --stack-name healthcare-ai-test

# 2. Run comprehensive integration tests
python tests/final_integration_test.py --environment test --stack-name healthcare-ai-test --output reports/integration_test.json

# 3. Run cost analysis
python scripts/cost_analysis.py --environment test --output reports/cost_analysis.json

# 4. Deploy and test everything together
python scripts/deploy_and_test.py --environment test
```

## Test Configuration

### Environment Variables

```bash
export ENVIRONMENT=test
export AWS_REGION=us-east-1
export STACK_NAME=healthcare-ai-test
export AWS_PROFILE=your-profile  # Optional
```

### Configuration Files

The testing framework uses these configuration files:

- `deployment/config.json` - Deployment configuration
- `tests/test_config.json` - Test-specific settings
- `frontend/config/aws-config.js` - Frontend API configuration

## Test Categories

### 1. Deployment Validation

**What it tests:**
- CloudFormation stack status
- Required outputs exist
- Lambda functions are active
- DynamoDB tables are accessible
- S3 buckets are configured correctly

**Success criteria:**
- All infrastructure components are in "ACTIVE" or "COMPLETE" state
- Required stack outputs are present
- No deployment errors

### 2. Agent Functionality Testing

**What it tests:**
- Agent Router correctly routes messages
- All four healthcare agents respond appropriately:
  - Illness Monitor (Hiyori)
  - Mental Health Support (Xiaoxing)
  - Safety Guardian
  - Wellness Coach
- Traditional Chinese language support
- Emergency detection and routing

**Test messages:**
```json
{
  "illness_monitor": [
    "I have a headache and feel dizzy",
    "我頭痛同頭暈"
  ],
  "mental_health": [
    "I'm feeling really stressed about school",
    "我對學校感到很大壓力"
  ],
  "safety_guardian": [
    "I'm having chest pain and can't breathe",
    "我胸痛，呼吸困難"
  ],
  "wellness_coach": [
    "How can I start exercising?",
    "我怎樣開始運動？"
  ]
}
```

**Success criteria:**
- ≥75% of agent tests pass
- Responses are contextually appropriate
- Language detection works correctly
- Emergency messages route to Safety Guardian

### 3. Live2D Frontend Testing

**What it tests:**
- CloudFront distribution accessibility
- Static assets loading (CSS, JS, Live2D models)
- API configuration in frontend
- HTTPS enforcement
- CORS configuration

**Success criteria:**
- ≥50% of frontend tests pass
- Main page loads successfully
- Critical assets are accessible
- API endpoints are properly configured

### 4. Speech Functionality Testing

**What it tests:**
- Text-to-Speech with AWS Polly
- Speech-to-Text with AWS Transcribe
- Multi-language support (English, Traditional Chinese)
- Agent-specific voice selection

**Success criteria:**
- TTS generates audio successfully
- STT processes audio files
- Language-specific voices work
- Audio quality is acceptable

### 5. Cost Analysis

**What it analyzes:**
- Current AWS costs by service
- Monthly cost projections
- Usage patterns and optimization opportunities
- Cost alert configuration

**Optimization recommendations:**
- Lambda memory optimization
- DynamoDB TTL configuration
- S3 lifecycle policies
- Bedrock model selection optimization

**Success criteria:**
- Monthly costs under $50 for test environment
- Cost monitoring is configured
- Optimization recommendations are provided

### 6. Performance Testing

**What it tests:**
- API response times (target: <3 seconds)
- Concurrent request handling
- Lambda cold start performance
- Database query efficiency

**Success criteria:**
- Average response time <3 seconds
- ≥80% success rate for concurrent requests
- No timeout errors under normal load

### 7. Security Testing

**What it tests:**
- HTTPS enforcement
- CORS configuration
- S3 bucket security
- API authentication (if configured)
- Data encryption in transit

**Success criteria:**
- All HTTP requests redirect to HTTPS
- CORS headers are properly configured
- Data buckets are not publicly accessible

### 8. Monitoring Testing

**What it tests:**
- CloudWatch log groups exist
- Cost alerts are configured
- Lambda function metrics are collected
- Error alerting is working

**Success criteria:**
- All log groups are created and accessible
- Cost alerts are configured with appropriate thresholds
- Metrics are being collected

## Test Reports

### Report Structure

All test reports are saved in the `reports/` directory:

```
reports/
├── deployment/
│   └── validation_YYYYMMDD_HHMMSS.json
├── testing/
│   ├── integration_test_YYYYMMDD_HHMMSS.json
│   ├── agent_functionality_YYYYMMDD_HHMMSS.json
│   └── frontend_test_YYYYMMDD_HHMMSS.json
├── cost_analysis/
│   └── cost_analysis_YYYYMMDD_HHMMSS.json
└── final/
    ├── final_integration_report_YYYYMMDD_HHMMSS.json
    └── final_summary_YYYYMMDD_HHMMSS.txt
```

### Report Contents

**Integration Test Report:**
```json
{
  "test_execution": {
    "timestamp": "2024-12-01T10:30:00Z",
    "environment": "test",
    "overall_status": "PASSED"
  },
  "test_results": {
    "deployment_validation": { "total_tests": 10, "passed": 10 },
    "agent_functionality": { "total_tests": 8, "passed": 7 },
    "live2d_frontend": { "total_tests": 5, "passed": 4 },
    "speech_functionality": { "total_tests": 4, "passed": 3 },
    "cost_analysis": { "estimated_monthly_cost": 25.50 },
    "performance_tests": { "avg_response_time": 1.2 },
    "summary": {
      "total_tests": 35,
      "passed": 32,
      "success_rate": 91.4,
      "overall_status": "PASSED"
    }
  },
  "recommendations": [
    "Configure DynamoDB TTL for automatic cleanup",
    "Optimize Lambda memory settings",
    "Set up S3 lifecycle policies"
  ],
  "next_steps": [
    "✅ System is ready for production use",
    "📊 Set up regular monitoring and cost reviews"
  ]
}
```

**Cost Analysis Report:**
```json
{
  "cost_summary": {
    "current_monthly_projection": 28.75,
    "total_potential_savings": 8.50,
    "optimized_monthly_cost": 20.25,
    "potential_savings_percentage": 29.6
  },
  "cost_breakdown": {
    "AWS Lambda": 3.50,
    "Amazon DynamoDB": 4.25,
    "Amazon Bedrock": 12.00,
    "Amazon S3": 2.00,
    "Amazon API Gateway": 3.00,
    "Amazon CloudFront": 1.50,
    "Amazon Transcribe": 1.25,
    "Amazon Polly": 1.25
  },
  "optimization_recommendations": [
    {
      "title": "Optimize Lambda Memory Configuration",
      "potential_savings": 3.50,
      "priority": "high",
      "implementation_effort": "low"
    }
  ]
}
```

## Troubleshooting

### Common Issues

**1. AWS Credentials Not Configured**
```bash
Error: AWS credentials not configured or invalid
```
**Solution:**
```bash
aws configure
# or
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1
```

**2. Stack Not Found**
```bash
Error: CloudFormation stack 'healthcare-ai-test' not found
```
**Solution:**
- Verify stack name: `aws cloudformation list-stacks`
- Check region: `aws configure get region`
- Deploy stack first if it doesn't exist

**3. Lambda Functions Not Active**
```bash
Error: Lambda function state is 'Pending'
```
**Solution:**
- Wait for deployment to complete
- Check CloudFormation stack events for errors
- Verify Lambda deployment packages are uploaded

**4. API Gateway Not Accessible**
```bash
Error: HTTP 403 Forbidden
```
**Solution:**
- Check API Gateway deployment stage
- Verify CORS configuration
- Check Lambda function permissions

**5. High Costs Detected**
```bash
Warning: Monthly projection exceeds $50
```
**Solution:**
- Review cost breakdown in report
- Implement optimization recommendations
- Check for resource leaks or over-provisioning

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export DEBUG=1
export PYTHONPATH=$PWD:$PWD/tests:$PWD/src
python -m pytest tests/ -v --tb=long
```

### Manual Verification

If automated tests fail, manually verify components:

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name healthcare-ai-test

# Test API directly
curl -X POST https://your-api-url/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "user_id": "test"}'

# Check Lambda logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/healthcare"

# Verify DynamoDB tables
aws dynamodb list-tables
```

## Success Criteria Summary

For the system to pass final integration testing:

| Component | Minimum Success Rate | Critical Requirements |
|-----------|---------------------|----------------------|
| Deployment Validation | 100% | All infrastructure active |
| Agent Functionality | 75% | At least 3/4 agents working |
| Frontend Testing | 50% | Main page accessible |
| Speech Functionality | 50% | Basic TTS/STT working |
| Cost Analysis | N/A | Monthly cost <$50 |
| Performance | 80% | Response time <3s |
| Security | 100% | HTTPS enforced |
| Monitoring | 80% | Logs and alerts configured |

**Overall Success:** ≥80% of all tests pass

## Next Steps After Testing

### If Tests Pass (≥80% success rate):
1. ✅ System is ready for production deployment
2. 📊 Set up regular monitoring and cost reviews
3. 🔄 Implement automated testing in CI/CD pipeline
4. 📚 Update documentation with deployment URLs
5. 👥 Train users on the new AWS-based system

### If Tests Partially Pass (60-79% success rate):
1. ⚠️ Review failed components and address critical issues
2. 🛠️ Consider deploying with current functionality while fixing issues
3. 📋 Monitor system closely after deployment
4. 🔄 Plan fixes for non-critical failures

### If Tests Fail (<60% success rate):
1. ❌ Do not deploy to production
2. 🔍 Review all failed components and error logs
3. 🛠️ Fix critical issues before attempting deployment
4. 🔄 Re-run tests after fixes are implemented
5. 📋 Consider rollback if already deployed

## Support

For issues with the testing framework:

1. Check the troubleshooting section above
2. Review test logs in the `reports/` directory
3. Verify AWS permissions and configuration
4. Check CloudFormation stack events for deployment issues
5. Review Lambda function logs in CloudWatch

## Contributing

To add new tests or improve the testing framework:

1. Add test functions to `tests/final_integration_test.py`
2. Update test configuration in `tests/test_config.json`
3. Add new test categories to the main test runner
4. Update this documentation with new test descriptions
5. Ensure new tests follow the existing patterns and error handling