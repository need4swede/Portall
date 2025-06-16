FROM python:3.11-slim

# Create non-root user and group
RUN groupadd -r portall && useradd -r -g portall -s /bin/false portall

# Set working directory
WORKDIR /app

# Install dependencies as root first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/instance && \
    chown -R portall:portall /app

# Switch to non-root user
USER portall

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]
