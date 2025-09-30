# Agent Router Lambda Deployment Guide

This guide explains how to deploy the Agent Router Lambda function to AWS.

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Python 3.11 or later
3. boto3 library installed (`pip install boto3`)
4. CloudFormation stack already deployed with basic infrastructure

## Deployment Methods

### Method 1: Using the Deployment Script

1. **Navigate to the Agent Router directory:**
   ```bash
   cd healthcare_ai_live2d_unified/src/lambda/agent_router
   ```

2. **Install dependencies (if needed):**
   ```bash
   pip install boto3
   ```

3. **Run the deployment script:**
   ```bash
   python deploy.py [environment]
   ```
   
   Example:
   ```bash
   python deploy.py dev
   ```

### Method 2: Manual Deployment

1. **Create deployment package:**
   ```bash
   cd healthcare_ai_live2d_unified/src/lambda/agent_router
   zip -r agent_router_deployment.zip handler.py requirements.txt
   ```

2. **Update Lambda function using AWS CLI:**
   ```bash
   aws lambda update-function-code \
     --function-name dev-healthcare-agent-router \
     --zip-file fileb://agent_router_deployment.zip
   ```

### Method 3: CloudFormation Update

1. **Package the code:**
   ```bash
   cd healthcare_ai_live2d_unified/src/lambda/agent_router
   zip -r ../../../infrastructure/agent_router.zip handler.py
   ```

2. **Upload to S3 (if using S3 for deployment):**
   ```bash
   aws s3 cp ../../../infrastructure/agent_router.zip s3://your-deployment-bucket/
   ```

3. **Update CloudFormation template to reference S3 object:**
   ```yaml
   Code:
     S3Bucket: your-deployment-bucket
     S3Key: agent_router.zip
   ```

## Environment Configuration

The Lambda function requires the following environment variables (automatically set by CloudFormation):

- `ENVIRONMENT`: Deployment environment (dev/staging/prod)
- `CONVERSATIONS_TABLE`: DynamoDB table name for conversations
- `USERS_TABLE`: DynamoDB table name for user profiles
- `DATA_BUCKET`: S3 bucket name for data storage

## Testing Deployment

### 1. Test via AWS CLI

```bash
aws lambda invoke \
  --function-name dev-healthcare-agent-router \
  --payload '{"message": "I have a headache", "user_id": "test_user"}' \
  response.json

cat response.json
```

### 2. Test via API Gateway

```bash
curl -X POST https://your-api-gateway-url/dev/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I feel anxious",
    "user_id": "test_user"
  }'
```

### 3. Test Emergency Routing

```bash
curl -X POST https://your-api-gateway-url/dev/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Emergency! I can'\''t breathe!",
    "user_id": "test_user"
  }'
```

## Monitoring and Troubleshooting

### CloudWatch Logs

View logs in CloudWatch:
```bash
aws logs tail /aws/lambda/dev-healthcare-agent-router --follow
```

### Common Issues

1. **Import Errors:**
   - Ensure all dependencies are included in the deployment package
   - Check Python version compatibility

2. **Permission Errors:**
   - Verify IAM role has necessary permissions for DynamoDB, Lambda invoke, etc.
   - Check resource ARNs in IAM policies

3. **Timeout Issues:**
   - Increase Lambda timeout if needed
   - Optimize code for faster execution

4. **Agent Invocation Failures:**
   - Ensure target agent Lambda functions exist
   - Check function naming convention matches environment

### Performance Optimization

1. **Cold Start Optimization:**
   - Keep deployment package small
   - Initialize clients outside handler function
   - Use connection pooling where appropriate

2. **Memory Optimization:**
   - Monitor memory usage in CloudWatch
   - Adjust memory allocation based on actual usage
   - Consider using Lambda Power Tuning tool

3. **Cost Optimization:**
   - Set appropriate reserved concurrency limits
   - Monitor invocation patterns
   - Use CloudWatch cost monitoring

## Rollback Procedure

If deployment fails or causes issues:

1. **Revert to previous version:**
   ```bash
   aws lambda update-function-code \
     --function-name dev-healthcare-agent-router \
     --zip-file fileb://previous_version.zip
   ```

2. **Check CloudFormation stack:**
   ```bash
   aws cloudformation describe-stacks \
     --stack-name dev-healthcare-ai-stack
   ```

3. **Restore from backup if needed:**
   - Use CloudFormation rollback functionality
   - Restore from version control

## Security Considerations

1. **IAM Permissions:**
   - Follow principle of least privilege
   - Regularly audit permissions
   - Use resource-specific ARNs

2. **Data Handling:**
   - Ensure sensitive data is encrypted
   - Implement proper logging without exposing PII
   - Use secure communication channels

3. **Network Security:**
   - Deploy in VPC if required
   - Configure security groups appropriately
   - Use AWS WAF for API Gateway protection

## Maintenance

### Regular Tasks

1. **Update Dependencies:**
   - Keep boto3 and other libraries updated
   - Test compatibility with new versions

2. **Monitor Performance:**
   - Review CloudWatch metrics regularly
   - Optimize based on usage patterns
   - Update memory/timeout settings as needed

3. **Code Updates:**
   - Follow version control best practices
   - Test changes in development environment first
   - Document all changes and deployments

### Scaling Considerations

1. **Concurrency Limits:**
   - Monitor concurrent executions
   - Adjust reserved concurrency as needed
   - Consider provisioned concurrency for consistent performance

2. **Error Handling:**
   - Implement circuit breaker patterns
   - Add retry logic with exponential backoff
   - Monitor error rates and patterns

3. **Integration Points:**
   - Ensure downstream services can handle load
   - Implement proper timeout and retry strategies
   - Monitor end-to-end latency