FROM python:3.13-alpine

# Install required packages
RUN pip install pyyaml requests cryptography jsonschema

# Set working directory
WORKDIR /app

# Create directory for schema
RUN mkdir -p /app/bookmark-schema

# Copy application structure
COPY app/ /app/app/
COPY scripts/ /app/scripts/

# Grant execution permission to main script
RUN chmod +x /app/scripts/validate_bookmarks.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set entrypoint
ENTRYPOINT ["python3", "/app/scripts/validate_bookmarks.py"]