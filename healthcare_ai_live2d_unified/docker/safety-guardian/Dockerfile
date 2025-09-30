# Safety Guardian Lambda Container
# ================================
# 
# Container image for the safety guardian emergency response Lambda function

FROM healthcare-ai-lambda-base:latest

# Copy safety guardian specific code
COPY src/lambda/safety_guardian/ ./

# Set the Lambda handler
CMD ["handler.lambda_handler"]