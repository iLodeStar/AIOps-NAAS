FROM python:3.11-slim
WORKDIR /app

# Note: Build this image from repository root with:
# docker build -f services/correlation-service/Dockerfile -t correlation-service:v3 .

# Copy and install aiops_core dependency first
COPY aiops_core /tmp/aiops_core
RUN pip install --no-cache-dir /tmp/aiops_core

# Install service requirements
COPY services/correlation-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/correlation-service/ .

CMD ["python", "correlation_service.py"]
