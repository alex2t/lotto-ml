<#
.SYNOPSIS
    Starts the Irish Lotto Docker services (Data Engine + Streamlit Dashboard).
.DESCRIPTION
    1. Executes the data-engine container to update ~24 JSON artifacts from data/irish500.csv.
    2. Starts the Streamlit web dashboard container on http://localhost:8501.
.PARAMETER Build
    Forces a rebuild of the Docker images before running.
.PARAMETER EngineOnly
    Runs only the data-engine analysis and exits without starting the web dashboard.
.EXAMPLE
    .\scripts\docker_start.ps1
    .\scripts\docker_start.ps1 -Build
    .\scripts\docker_start.ps1 -EngineOnly
#>

[CmdletBinding()]
param(
    [switch]$Build,
    [switch]$EngineOnly
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $ProjectRoot

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " Irish Lotto System - Docker Launcher (Windows PowerShell)" -ForegroundColor Cyan
Write-Host " Project root: $ProjectRoot" -ForegroundColor DarkGray
Write-Host "====================================================================" -ForegroundColor Cyan

# Check Docker availability
try {
    $null = docker version
} catch {
    Write-Error "Docker is not running or not found in PATH. Please start Docker Desktop."
    exit 1
}

# Ensure data/analysis exists
if (-not (Test-Path "data/analysis")) {
    New-Item -ItemType Directory -Path "data/analysis" -Force | Out-Null
}

if ($Build) {
    Write-Host ">> Rebuilding Docker images..." -ForegroundColor Yellow
    docker compose build
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker build failed."
        exit $LASTEXITCODE
    }
}

Write-Host ">> Step 1: Running data-engine to generate/update ~24 JSON artifacts..." -ForegroundColor Green
docker compose run --rm data-engine
if ($LASTEXITCODE -ne 0) {
    Write-Error "Data engine execution failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

if ($EngineOnly) {
    Write-Host ">> Engine-only mode complete. Data artifacts updated in ./data" -ForegroundColor Green
    exit 0
}

Write-Host ">> Step 2: Starting Streamlit Web Dashboard..." -ForegroundColor Green
docker compose up -d --no-deps streamlit-web
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start Streamlit web dashboard."
    exit $LASTEXITCODE
}

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " SUCCESS: Data analysis complete & Streamlit dashboard is running!" -ForegroundColor Green
Write-Host " Open your browser at: http://localhost:8501" -ForegroundColor Yellow
Write-Host " To stop: .\scripts\docker_stop.ps1" -ForegroundColor DarkGray
Write-Host "====================================================================" -ForegroundColor Cyan
