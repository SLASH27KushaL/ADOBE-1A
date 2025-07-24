# docker/Dockerfile
FROM --platform=linux/amd64 python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source + configs + entrypoint
COPY src/ src/
COPY configs/ configs/
COPY docker/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Optional: declare volumes for clarity (the judge will -v mount anyway)
VOLUME ["/app/input", "/app/output"]

ENTRYPOINT ["/app/entrypoint.sh"]
