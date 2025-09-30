# Wellness Coach Lambda Container
# ===============================
# 
# Container image for the wellness coach Lambda function

FROM healthcare-ai-lambda-base:latest

# Copy wellness coach specific code
COPY src/lambda/wellness_coach/ ./

# Set the Lambda handler
CMD ["handler.lambda_handler"]