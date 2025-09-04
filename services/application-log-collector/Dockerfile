FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_log_collector.py .

EXPOSE 8090 5140

CMD ["python", "app_log_collector.py"]