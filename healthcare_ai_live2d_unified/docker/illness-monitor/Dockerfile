# Illness Monitor Lambda Container
# ===============================
# 
# Container image for the illness monitor healthcare agent Lambda function

FROM healthcare-ai-lambda-base:latest

# Copy illness monitor specific code
COPY src/lambda/illness_monitor/ ./

# Set the Lambda handler
CMD ["handler.lambda_handler"]