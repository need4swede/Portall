#!/bin/bash

# Portall Entrypoint Script
# Handles automatic setup and permissions before starting the application

set -e

echo "🐳 Portall Starting..."
echo "====================="

# Function to ensure instance directory has correct permissions
setup_instance_directory() {
    echo "📁 Setting up instance directory..."

    # Create instance directory if it doesn't exist
    mkdir -p /app/instance

    # Check if we can write to the instance directory
    if [ -w /app/instance ]; then
        echo "✅ Instance directory is writable"
    else
        echo "⚠️  Instance directory is not writable, attempting to fix..."

        # Try to fix permissions
        chmod 777 /app/instance 2>/dev/null || {
            echo "❌ Cannot fix instance directory permissions"
            echo "   This might be a bind mount permission issue"
            echo "   The database will be created in a temporary location"

            # Use a temporary directory instead
            export DATABASE_URL="sqlite:////tmp/portall.db"
            echo "   Database URL changed to: $DATABASE_URL"
        }
    fi
}

# Function to wait for socket proxy if needed
wait_for_socket_proxy() {
    if [ "${DOCKER_ENABLED:-true}" = "true" ]; then
        echo "🔌 Checking Docker socket proxy..."

        # Extract host and port from DOCKER_HOST
        PROXY_HOST=$(echo "${DOCKER_HOST:-tcp://socket-proxy:2375}" | sed 's|tcp://||' | cut -d: -f1)
        PROXY_PORT=$(echo "${DOCKER_HOST:-tcp://socket-proxy:2375}" | sed 's|tcp://||' | cut -d: -f2)

        # Wait for socket proxy to be available (with timeout)
        timeout=30
        counter=0

        while [ $counter -lt $timeout ]; do
            if nc -z "$PROXY_HOST" "$PROXY_PORT" 2>/dev/null; then
                echo "✅ Socket proxy is available"
                break
            fi

            if [ $counter -eq 0 ]; then
                echo "⏳ Waiting for socket proxy at $PROXY_HOST:$PROXY_PORT..."
            fi

            sleep 1
            counter=$((counter + 1))
        done

        if [ $counter -eq $timeout ]; then
            echo "⚠️  Socket proxy not available after ${timeout}s, continuing anyway..."
            echo "   Docker features may not work properly"
        fi
    fi
}

# Function to validate environment
validate_environment() {
    echo "🔍 Validating environment..."

    # Check if running as root (which we don't want for security)
    if [ "$(id -u)" = "0" ]; then
        echo "⚠️  Running as root user"
        echo "   This is not recommended for security reasons"
        echo "   Consider using USER_ID and GROUP_ID environment variables"
    else
        echo "✅ Running as non-root user ($(id -u):$(id -g))"
    fi

    # Log key configuration
    echo "📋 Configuration:"
    echo "   Database URL: ${DATABASE_URL:-sqlite:///portall.db}"
    echo "   Docker Host: ${DOCKER_HOST:-tcp://socket-proxy:2375}"
    echo "   Docker Enabled: ${DOCKER_ENABLED:-true}"
    echo "   Secret Key: ${SECRET_KEY:+[SET]}${SECRET_KEY:-[NOT SET]}"
}

# Function to handle database setup
setup_database() {
    echo "🗄️  Setting up database..."

    # The Python app will handle database initialization
    # We just need to ensure the directory exists and is writable
    setup_instance_directory
}

# Function to start the application
start_application() {
    echo "🚀 Starting Portall application..."
    echo ""

    # Execute the original command (usually "python app.py")
    exec "$@"
}

# Main execution flow
main() {
    # Validate environment
    validate_environment

    # Setup database directory
    setup_database

    # Wait for dependencies
    wait_for_socket_proxy

    # Start the application
    start_application "$@"
}

# Handle special cases
case "${1:-}" in
    --help|-h)
        echo "Portall Container Entrypoint"
        echo ""
        echo "This script automatically sets up the environment and starts Portall."
        echo "It handles permissions, validates configuration, and waits for dependencies."
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL     - Database connection string"
        echo "  DOCKER_HOST      - Docker socket proxy URL"
        echo "  DOCKER_ENABLED   - Enable Docker integration (true/false)"
        echo "  SECRET_KEY       - Flask secret key"
        echo "  USER_ID          - User ID to run as (set in docker-compose)"
        echo "  GROUP_ID         - Group ID to run as (set in docker-compose)"
        echo ""
        echo "Usage: docker run ... portall [python app.py]"
        exit 0
        ;;
    --version)
        echo "Portall Container Entrypoint v1.0"
        exit 0
        ;;
    *)
        # Normal startup
        main "$@"
        ;;
esac