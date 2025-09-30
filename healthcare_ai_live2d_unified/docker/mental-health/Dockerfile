# Mental Health Lambda Container
# ==============================
# 
# Container image for the mental health support Lambda function

FROM healthcare-ai-lambda-base:latest

# Copy mental health specific code
COPY src/lambda/mental_health/ ./

# Set the Lambda handler
CMD ["handler.lambda_handler"]