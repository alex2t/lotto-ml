#!/usr/bin/env bash
# ==============================================================================
# Irish Lotto System - Docker Stop Script (Linux & macOS)
# ==============================================================================
# Usage:
#   ./scripts/docker_stop.sh
# ==============================================================================

set -e

# Resolve repository root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "===================================================================="
echo " Irish Lotto System - Stopping Docker Containers (Linux / macOS)"
echo " Project root: $PROJECT_ROOT"
echo "===================================================================="

if command -v docker &> /dev/null; then
    echo ">> Stopping and removing docker-compose containers..."
    docker compose down --remove-orphans || true

    # Stop standalone container if running
    if docker ps -q --filter "name=lotto-data-engine" | grep -q .; then
        echo ">> Stopping lotto-data-engine container..."
        docker stop lotto-data-engine 2>/dev/null || true
    fi
    echo ">> Docker services stopped successfully."
else
    echo "Docker not found in PATH."
fi
