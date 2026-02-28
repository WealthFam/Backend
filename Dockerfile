# Stage 1: Build Frontend
FROM node:20 AS frontend-build
WORKDIR /app
COPY version.json ./
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
ARG VITE_APP_BUILD=0000
ENV VITE_APP_BUILD=$VITE_APP_BUILD
RUN npm run build

# Stage 2: Final Image
FROM python:3.11-slim

# 1. System Installations
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Python Dependency Installation
COPY backend/requirements.txt ./backend-reqs.txt
COPY parser/requirements.txt ./parser-reqs.txt
RUN pip install --no-cache-dir -r backend-reqs.txt && \
    pip install --no-cache-dir -r parser-reqs.txt

# 3. Static Infrastructure Configs (Change infrequently)
COPY frontend/nginx.conf /etc/nginx/sites-available/default
# Create entrypoint.sh inline to avoid CRLF/BOM issues
RUN printf "#!/bin/bash\nnginx\npython run_backend.py\n" > entrypoint.sh && chmod +x entrypoint.sh

# 4. Application Code (Changes frequently)
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html
COPY backend/ ./backend/
COPY parser/ ./parser/
COPY run_backend.py ./
COPY version.json ./

# Environment variables
ENV APP_DATABASE_URL="duckdb:////data/family_finance_v3.duckdb"
ENV PARSER_SERVICE_URL="http://localhost:8001/v1"
ENV PARSER_DATABASE_URL="duckdb:////data/ingestion_engine_parser.duckdb"
ENV SECRET_KEY="CHANGE_THIS_TO_A_SECURE_SECRET_IN_PRODUCTION"
ENV ALGORITHM="HS256"
ENV DEMO_MODE="false"
ENV PYTHONPATH="/app"

EXPOSE 80 8000 8001

ENTRYPOINT ["./entrypoint.sh"]
