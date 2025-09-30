# Healthcare AI Lambda Base Container
# =================================
# 
# Optimized base container for AWS Lambda with healthcare AI dependencies

FROM public.ecr.aws/lambda/python:3.11

# Set environment variables
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN yum update -y && \
    yum install -y \
        gcc \
        gcc-c++ \
        make \
        cmake \
        git \
        curl \
        wget \
        unzip && \
    yum clean all && \
    rm -rf /var/cache/yum

# Create application directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Clean up pip cache
    pip cache purge && \
    # Remove unnecessary files
    find /var/lang/lib/python3.11/site-packages -name "*.pyc" -delete && \
    find /var/lang/lib/python3.11/site-packages -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy shared AWS utilities
COPY src/aws/ ./aws/

# Set up proper permissions
RUN chmod -R 755 ${LAMBDA_TASK_ROOT}

# Health check script
COPY docker/lambda-base/healthcheck.py ./healthcheck.py
RUN chmod +x ./healthcheck.py

# Default command (will be overridden by specific Lambda functions)
CMD ["handler.lambda_handler"]