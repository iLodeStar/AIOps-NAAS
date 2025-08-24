FROM python:3.12-alpine

# Install system dependencies for science packages
RUN apk add --no-cache gcc musl-dev curl g++ gfortran openblas-dev

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8086

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8086/health || exit 1

# Run the application
CMD ["python", "benchmarking_service.py"]