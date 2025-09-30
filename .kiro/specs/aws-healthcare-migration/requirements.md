# Requirements Document

## Introduction

This document outlines the requirements for migrating the existing local Healthcare AI Live2D Unified System to AWS cloud infrastructure with a focus on **cost optimization** and **easy deployment**. The current system is a comprehensive healthcare AI assistant that needs to be transformed into a cost-effective, serverless solution that can be deployed with minimal configuration.

**Primary Goals:**
- **Minimize AWS costs** through serverless architecture and pay-per-use services
- **Simplify deployment** using existing CloudFormation template as foundation
- **Replace local dependencies** (OpenRouter, local TTS/STT) with native AWS services
- **Maintain core functionality** while optimizing for cloud-native patterns

The current local system includes:
- Healthcare AI V2 Backend with multi-agent architecture (FastAPI + PostgreSQL + Redis)
- Live2D Avatar Frontend with 4 specialized healthcare assistants
- OpenRouter API for AI models (needs migration to AWS Bedrock)
- Local speech processing (needs migration to AWS Transcribe/Polly)
- File uploads and processing
- Hong Kong healthcare data integration
- Docker-based deployment (needs containerization for AWS Lambda/ECR)

**Existing AWS Foundation:**
Your teammate has provided a CloudFormation template that includes the basic AWS infrastructure. This migration will build upon that foundation to create a complete, cost-optimized solution.

## Requirements

### Requirement 1: Cost-Optimized Infrastructure Migration

**User Story:** As a business owner, I want to migrate the local Healthcare AI system to AWS with minimal costs, so that I can run the system affordably while maintaining all functionality.

#### Acceptance Criteria

1. WHEN the system is deployed THEN it SHALL use only pay-per-use AWS services (Lambda, DynamoDB on-demand, S3, etc.)
2. WHEN the system is idle THEN it SHALL cost near zero (no always-running servers)
3. WHEN users access the system THEN response times SHALL be under 3 seconds for AI interactions
4. WHEN the system scales THEN costs SHALL increase proportionally to actual usage only
5. IF monthly costs exceed $50 for demo usage THEN automatic cost alerts SHALL be triggered

### Requirement 2: One-Click Deployment Setup

**User Story:** As a developer, I want to deploy the entire system with a single CloudFormation command, so that setup is simple and reproducible without complex configuration.

#### Acceptance Criteria

1. WHEN I run the CloudFormation template THEN the entire system SHALL be deployed automatically
2. WHEN deployment completes THEN I SHALL receive working URLs for the API and frontend
3. WHEN the system starts THEN it SHALL work immediately without additional configuration steps
4. WHEN I need to update THEN I SHALL be able to redeploy with a single command
5. IF deployment fails THEN clear error messages SHALL indicate what needs to be fixed

### Requirement 3: Replace External Dependencies with AWS Services

**User Story:** As a developer, I want to replace all external API dependencies (OpenRouter, local TTS/STT) with native AWS services, so that the system is self-contained and cost-optimized.

#### Acceptance Criteria

1. WHEN AI processing is needed THEN AWS Bedrock SHALL be used instead of OpenRouter API
2. WHEN speech-to-text is needed THEN AWS Transcribe SHALL be used instead of local STT
3. WHEN text-to-speech is needed THEN AWS Polly SHALL be used instead of local TTS
4. WHEN the system processes requests THEN no external API calls SHALL be made outside AWS
5. IF AWS services are unavailable THEN graceful fallback messages SHALL be provided

### Requirement 4: Serverless Multi-Agent Architecture

**User Story:** As a system architect, I want to convert the FastAPI multi-agent system into serverless Lambda functions, so that each agent can scale independently and costs are minimized.

#### Acceptance Criteria

1. WHEN users interact with different agents THEN each agent (illness_monitor, mental_health, safety_guardian, wellness_coach) SHALL run as separate Lambda functions
2. WHEN an agent is not being used THEN it SHALL cost nothing (true serverless)
3. WHEN multiple users access the same agent THEN Lambda SHALL automatically handle concurrent requests
4. WHEN agent logic is updated THEN individual agents SHALL be deployable without affecting others
5. IF an agent fails THEN other agents SHALL continue working normally

### Requirement 5: Database Migration from PostgreSQL to DynamoDB

**User Story:** As a developer, I want to migrate from PostgreSQL/Redis to DynamoDB, so that the database is serverless and costs scale with usage.

#### Acceptance Criteria

1. WHEN user data is stored THEN it SHALL use DynamoDB with on-demand billing (no fixed costs)
2. WHEN conversation history is accessed THEN it SHALL be retrieved efficiently from DynamoDB
3. WHEN caching is needed THEN DynamoDB TTL SHALL replace Redis functionality
4. WHEN the database is idle THEN it SHALL cost nothing (no always-running database servers)
5. IF data needs to be migrated THEN a migration script SHALL convert existing PostgreSQL data to DynamoDB format

### Requirement 6: Live2D Frontend Migration to S3/CloudFront

**User Story:** As a user, I want to access the Live2D avatar interface through a fast, cost-effective web hosting solution, so that the frontend loads quickly without expensive server costs.

#### Acceptance Criteria

1. WHEN users access the Live2D interface THEN it SHALL be served from S3 static website hosting
2. WHEN Live2D assets are loaded THEN they SHALL be cached by CloudFront for fast global access
3. WHEN the frontend makes API calls THEN they SHALL connect to the Lambda-based backend through API Gateway
4. WHEN the system is not being used THEN frontend hosting SHALL cost minimal amounts (S3 storage only)
5. IF users are globally distributed THEN CloudFront SHALL provide fast access from multiple regions

### Requirement 7: Cost Monitoring and Optimization

**User Story:** As a business owner, I want automatic cost monitoring and optimization, so that AWS bills stay predictable and low.

#### Acceptance Criteria

1. WHEN AWS costs exceed $20/month THEN automatic alerts SHALL be sent via SNS
2. WHEN Lambda functions run longer than 10 seconds THEN they SHALL be optimized for faster execution
3. WHEN DynamoDB usage is high THEN the system SHALL implement efficient query patterns
4. WHEN S3 storage grows THEN lifecycle policies SHALL automatically archive old files
5. IF costs spike unexpectedly THEN detailed cost breakdown SHALL be available through CloudWatch dashboards

### Requirement 8: Simplified Configuration Management

**User Story:** As a developer, I want all configuration to be managed through environment variables and CloudFormation parameters, so that no manual setup steps are required after deployment.

#### Acceptance Criteria

1. WHEN the CloudFormation stack is deployed THEN all necessary environment variables SHALL be automatically configured
2. WHEN API keys are needed THEN they SHALL be managed through AWS Systems Manager Parameter Store
3. WHEN configuration changes are needed THEN they SHALL be made through CloudFormation updates only
4. WHEN the system starts THEN it SHALL automatically discover all AWS resource ARNs and endpoints
5. IF configuration is missing THEN clear error messages SHALL indicate what needs to be set

### Requirement 9: Container Migration to AWS Lambda

**User Story:** As a developer, I want to convert the Docker-based application to Lambda-compatible code, so that the system can run serverlessly without container orchestration costs.

#### Acceptance Criteria

1. WHEN the current FastAPI application is migrated THEN it SHALL be split into multiple Lambda functions
2. WHEN Lambda functions are deployed THEN they SHALL use the existing ECR repository for container images
3. WHEN dependencies are packaged THEN they SHALL be optimized for Lambda cold start performance
4. WHEN the system handles requests THEN Lambda functions SHALL start quickly (under 2 seconds)
5. IF container images are too large THEN they SHALL be optimized to stay under Lambda limits

### Requirement 10: Speech Services Integration

**User Story:** As a user, I want to continue using voice interactions with the healthcare assistants through AWS native services, so that I can communicate naturally without external dependencies.

#### Acceptance Criteria

1. WHEN users speak to the system THEN AWS Transcribe SHALL convert speech to text with support for English and Traditional Chinese
2. WHEN the AI responds THEN AWS Polly SHALL convert text to speech with appropriate voices for each healthcare agent
3. WHEN speech processing occurs THEN it SHALL be processed through Lambda functions to minimize costs
4. WHEN voice interactions happen THEN they SHALL be processed efficiently with reasonable latency
5. IF speech services fail THEN the system SHALL gracefully fallback to text-only interaction

### Requirement 11: Hong Kong Healthcare Data Integration

**User Story:** As a Hong Kong user, I want the AWS deployment to maintain full support for Traditional Chinese and Hong Kong healthcare data, so that the system remains culturally relevant and locally useful.

#### Acceptance Criteria

1. WHEN users interact in Traditional Chinese THEN AWS Bedrock SHALL process and respond appropriately in Traditional Chinese
2. WHEN Hong Kong healthcare data is needed THEN it SHALL be cached in DynamoDB with appropriate TTL
3. WHEN cultural context is required THEN the system SHALL maintain Hong Kong-specific healthcare knowledge
4. WHEN emergency situations are detected THEN the system SHALL reference Hong Kong emergency services
5. IF language detection is needed THEN the system SHALL automatically identify and respond in the appropriate language

### Requirement 12: Migration and Testing Strategy

**User Story:** As a developer, I want a clear migration path from the local system to AWS, so that I can test and validate functionality before going live.

#### Acceptance Criteria

1. WHEN the migration is performed THEN a side-by-side comparison SHALL be possible between local and AWS versions
2. WHEN testing occurs THEN all four healthcare agents SHALL work identically to the local version
3. WHEN Live2D avatars are tested THEN they SHALL display and interact correctly through the AWS frontend
4. WHEN speech functionality is tested THEN AWS Transcribe/Polly SHALL provide equivalent functionality to local TTS/STT
5. IF issues are found THEN they SHALL be clearly documented with specific steps to reproduce and fix