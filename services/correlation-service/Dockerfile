FROM python:3.11-slim
WORKDIR /app

# Copy and install aiops_core dependency first
COPY ../../aiops_core /tmp/aiops_core
RUN pip install --no-cache-dir /tmp/aiops_core

# Install service requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY . .

CMD ["python", "correlation_service.py"]
