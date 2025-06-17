#!/bin/sh

# Docker GID Detection Script
# This script detects the Docker socket GID and starts the socket proxy with the correct user

echo "Starting Docker GID detection..."

# Detect Docker socket GID for cross-platform compatibility
if [ -S /var/run/docker.sock ]; then
    # Try different stat command formats for different platforms
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || stat -f '%g' /var/run/docker.sock 2>/dev/null || echo '999')
    echo "Detected Docker socket GID: $DOCKER_GID"
else
    echo "Docker socket not found, using default GID 999"
    DOCKER_GID=999
fi

# Export the detected GID
export DOCKER_GID

echo "Starting socket proxy with user 0:$DOCKER_GID"

# Switch to the detected user and start the socket proxy
exec su-exec "0:$DOCKER_GID" "$@"
