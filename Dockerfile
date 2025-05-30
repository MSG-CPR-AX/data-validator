FROM python:3.13-alpine

# Install required packages
RUN pip install pyyaml requests cryptography jsonschema

# Set working directory
WORKDIR /src

# Create directory for schema
RUN mkdir -p /src/bookmark-schema

# Copy application structure maintaining original layout
COPY app/ /src/app/
COPY scripts/ /src/scripts/

# Grant execution permission to main script
RUN chmod +x /src/scripts/validate_bookmarks.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/src

# Set entrypoint
ENTRYPOINT ["python3", "/src/scripts/validate_bookmarks.py"]