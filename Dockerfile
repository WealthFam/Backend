# Production Dockerfile for WealthFam Backend
FROM python:3.11-slim

# 1. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV APP_DATABASE_URL="duckdb:////data/family_finance_v3.duckdb"
ENV AGENT_SERVICE_URL="http://ai-agent:8002/api/v1"

# 2. Set working directory
WORKDIR /app

# 3. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copy application code
COPY app/ ./app/
COPY version.json .

# 6. Create data directory with appropriate permissions
RUN mkdir -p /data && chmod 777 /data

# 7. Expose port
EXPOSE 8000

# 8. Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
