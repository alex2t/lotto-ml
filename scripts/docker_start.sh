#!/usr/bin/env bash
# ==============================================================================
# Irish Lotto System - Docker Start Script (Linux & macOS)
# ==============================================================================
# Usage:
#   ./scripts/docker_start.sh               # Run data engine, then start Streamlit
#   ./scripts/docker_start.sh --build       # Rebuild images before running
#   ./scripts/docker_start.sh --engine-only # Run only data engine without web UI
# ==============================================================================

set -e

# Resolve repository root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "===================================================================="
echo " Irish Lotto System - Docker Launcher (Linux / macOS)"
echo " Project root: $PROJECT_ROOT"
echo "===================================================================="

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH."
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running."
    echo "Please start the Docker service before running this script."
    exit 1
fi

# Ensure data directory exists on host
mkdir -p data/analysis

# Parse command line flags
BUILD_FLAG=""
ENGINE_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --build)
            BUILD_FLAG="true"
            ;;
        --engine-only)
            ENGINE_ONLY=true
            ;;
        --help|-h)
            echo "Usage: $0 [--build] [--engine-only]"
            echo "  --build        Rebuild the Docker images before running"
            echo "  --engine-only  Run only data-engine analysis without web dashboard"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

if [ "$BUILD_FLAG" = "true" ]; then
    echo ">> Rebuilding Docker images..."
    docker compose build
fi

echo ">> Step 1: Running data-engine to generate ~24 JSON artifacts..."
docker compose run --rm data-engine

if [ "$ENGINE_ONLY" = true ]; then
    echo ">> Engine-only run complete. Data artifacts updated in ./data"
    exit 0
fi

echo ">> Step 2: Starting Streamlit Web Dashboard..."
docker compose up -d --no-deps streamlit-web

echo "===================================================================="
echo " SUCCESS: Data analysis complete & Streamlit dashboard is running!"
echo " Open your browser at: http://localhost:8501"
echo " To stop: ./scripts/docker_stop.sh"
echo "===================================================================="
