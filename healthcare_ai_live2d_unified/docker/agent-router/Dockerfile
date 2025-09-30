# Agent Router Lambda Container
# ============================
# 
# Container image for the healthcare AI agent router Lambda function

FROM healthcare-ai-lambda-base:latest

# Copy agent router specific code
COPY src/lambda/agent_router/ ./

# Install any additional dependencies if needed
# RUN pip install --no-cache-dir additional-package

# Set the Lambda handler
CMD ["handler.lambda_handler"]