# Multi-stage Dockerfile for NeuroLearn FastAPI Backend
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies needed for compiling psycopg2 if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

# Ensure non-root user execution
RUN useradd -m neurolearn && chown -R neurolearn:neurolearn /app
USER neurolearn

ENV HOST=0.0.0.0
ENV PORT=8000
ENV ENVIRONMENT=production
ENV DEBUG=false

EXPOSE 8000

# Run database migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
