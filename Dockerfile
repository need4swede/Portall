FROM python:3.11-slim

# Install netcat for connectivity testing
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -r portall && useradd -r -g portall -s /bin/false portall

# Set working directory
WORKDIR /app

# Install dependencies as root first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create instance directory with proper permissions
RUN mkdir -p /app/instance && \
    chmod 777 /app/instance && \
    chown -R portall:portall /app

# Switch to non-root user
USER portall

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expose port
EXPOSE 8080

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["python", "app.py"]