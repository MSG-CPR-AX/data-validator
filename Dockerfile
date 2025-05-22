
FROM python:3.11-alpine

# Install required packages
RUN pip install pyyaml requests cryptography

# Set working directory
WORKDIR /app

# Copy all scripts
COPY scripts/*.py /app/

# Grant execution permission
RUN chmod +x /app/validate_bookmarks.py

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set entrypoint
ENTRYPOINT ["python3", "/app/validate_bookmarks.py"]
