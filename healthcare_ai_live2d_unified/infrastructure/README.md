# Healthcare AI Live2D System - AWS Infrastructure

This directory contains the CloudFormation template and deployment scripts for migrating the Healthcare AI Live2D system to AWS with cost-optimized, serverless architecture.

## 🏗️ Architecture Overview

The infrastructure includes:

- **Frontend**: S3 static website hosting + CloudFront CDN
- **API**: API Gateway + Lambda functions (serverless)
- **Database**: DynamoDB with on-demand billing
- **AI Services**: AWS Bedrock integration
- **Speech**: AWS Transcribe + Polly
- **Storage**: S3 with lifecycle policies
- **Monitoring**: CloudWatch + SNS cost alerts

## 💰 Cost Optimization Features

- **Pay-per-use only**: No fixed costs when idle
- **DynamoDB on-demand**: Scales with usage
- **Lambda reserved concurrency**: Prevents runaway costs
- **S3 lifecycle policies**: Auto-archive old files
- **CloudWatch log retention**: 14-day retention for cost savings
- **TTL auto-cleanup**: Automatic data expiration

**Estimated Costs:**
- Light usage (100 conversations/day): $5-10/month
- Medium usage (500 conversations/day): $15-25/month
- Heavy usage (1000 conversations/day): $25-40/month

## 🚀 Quick Deployment

### Prerequisites

1. **AWS CLI installed and configured**
   ```bash
   # Install AWS CLI
   pip install awscli
   
   # Configure with your credentials
   aws configure
   ```

2. **Required permissions**: Your AWS user/role needs permissions for:
   - CloudFormation
   - Lambda
   - DynamoDB
   - S3
   - API Gateway
   - CloudFront
   - IAM
   - CloudWatch
   - SNS

### One-Click Deployment

#### Linux/macOS:
```bash
cd healthcare_ai_live2d_unified/infrastructure
./deploy.sh --email your-email@example.com
```

#### Windows (PowerShell):
```powershell
cd healthcare_ai_live2d_unified\infrastructure
.\deploy.ps1 -CostAlertEmail your-email@example.com
```

### Deployment Options

```bash
# Basic deployment
./deploy.sh --email admin@example.com

# Production deployment
./deploy.sh --environment prod --region us-west-2 --email admin@example.com

# Custom stack name and cost threshold
./deploy.sh --stack-name my-healthcare-stack --threshold 50 --email admin@example.com
```

## 📋 Deployment Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `Environment` | Environment name (dev/staging/prod) | `dev` | No |
| `Region` | AWS region | `us-east-1` | No |
| `StackName` | CloudFormation stack name | `healthcare-ai-live2d` | No |
| `CostAlertEmail` | Email for cost alerts | - | Yes |
| `CostThreshold` | Cost alert threshold (USD) | `20` | No |

## 🔧 Post-Deployment Steps

After successful deployment:

1. **Upload Frontend Files**
   ```bash
   # Get the S3 bucket name from stack outputs
   aws cloudformation describe-stacks --stack-name healthcare-ai-live2d --query 'Stacks[0].Outputs[?OutputKey==`WebsiteBucketName`].OutputValue' --output text
   
   # Upload Live2D frontend files
   aws s3 sync ../src/web/live2d/frontend/ s3://YOUR-BUCKET-NAME/
   ```

2. **Update Frontend Configuration**
   - Update API endpoints in your frontend code to use the deployed API Gateway URL
   - Update asset paths to use CloudFront URLs

3. **Deploy Lambda Code**
   - Follow tasks 2-6 in the implementation plan to deploy actual Lambda function code
   - The current deployment includes placeholder Lambda functions

4. **Test the System**
   - Access the CloudFront URL to test the frontend
   - Test API endpoints using the API Gateway URL

## 📊 Monitoring and Alerts

### Cost Monitoring
- **Billing alerts**: Configured to alert when costs exceed threshold
- **CloudWatch dashboards**: Monitor Lambda execution, DynamoDB usage, S3 storage
- **SNS notifications**: Email alerts for cost thresholds

### Operational Monitoring
- **Lambda logs**: Available in CloudWatch Logs (14-day retention)
- **API Gateway logs**: Request/response logging
- **DynamoDB metrics**: Read/write capacity and throttling
- **S3 access logs**: File access patterns

### Useful Monitoring Commands
```bash
# View stack status
aws cloudformation describe-stacks --stack-name healthcare-ai-live2d

# View recent stack events
aws cloudformation describe-stack-events --stack-name healthcare-ai-live2d --max-items 10

# View Lambda function logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/dev-healthcare"

# View current month's estimated charges
aws cloudwatch get-metric-statistics --namespace AWS/Billing --metric-name EstimatedCharges --dimensions Name=Currency,Value=USD --start-time $(date -u -d '1 month ago' +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 86400 --statistics Maximum
```

## 🗑️ Cleanup

To delete all resources and stop incurring costs:

```bash
# Delete the CloudFormation stack
aws cloudformation delete-stack --stack-name healthcare-ai-live2d

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name healthcare-ai-live2d
```

**Note**: This will delete all data. Make sure to backup any important data before deletion.

## 🔍 Troubleshooting

### Common Issues

1. **Stack creation fails with permissions error**
   - Ensure your AWS user has all required permissions
   - Check IAM policies and roles

2. **Email validation fails**
   - Ensure email format is valid
   - Check SNS subscription confirmation in your email

3. **Lambda functions timeout**
   - Check CloudWatch logs for specific errors
   - Verify environment variables are set correctly

4. **DynamoDB throttling**
   - On-demand billing should handle most cases
   - Check for inefficient query patterns

5. **S3 access denied**
   - Verify bucket policies are correctly applied
   - Check CORS configuration for frontend access

### Getting Help

1. **Check CloudFormation events**:
   ```bash
   aws cloudformation describe-stack-events --stack-name healthcare-ai-live2d
   ```

2. **View Lambda logs**:
   ```bash
   aws logs tail /aws/lambda/dev-healthcare-agent-router --follow
   ```

3. **Check stack outputs**:
   ```bash
   aws cloudformation describe-stacks --stack-name healthcare-ai-live2d --query 'Stacks[0].Outputs'
   ```

## 📁 File Structure

```
infrastructure/
├── cloudformation-template.yaml    # Main CloudFormation template
├── deploy.sh                      # Linux/macOS deployment script
├── deploy.ps1                     # Windows PowerShell deployment script
└── README.md                      # This file
```

## 🔐 Security Considerations

- **IAM roles**: Least privilege access for Lambda functions
- **S3 bucket policies**: Public read for website, private for data
- **API Gateway**: CORS configured for frontend access
- **DynamoDB**: Encryption at rest enabled
- **CloudFront**: HTTPS redirect enforced
- **Parameter Store**: Secure configuration management

## 📈 Scaling Considerations

- **Lambda concurrency**: Reserved concurrency limits prevent cost spikes
- **DynamoDB**: On-demand billing scales automatically
- **CloudFront**: Global CDN handles traffic spikes
- **API Gateway**: Built-in throttling and caching
- **S3**: Unlimited storage with lifecycle policies

## 🔄 Updates and Maintenance

To update the infrastructure:

1. Modify the CloudFormation template
2. Run the deployment script again (it will perform an update)
3. Monitor the update progress in CloudFormation console

The deployment script automatically detects if the stack exists and performs an update instead of create.