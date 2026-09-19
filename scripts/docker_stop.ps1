<#
.SYNOPSIS
    Stops the Irish Lotto Docker containers.
.DESCRIPTION
    Tears down docker-compose containers and removes temporary containers.
.EXAMPLE
    .\scripts\docker_stop.ps1
#>

[CmdletBinding()]
param()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $ProjectRoot

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " Irish Lotto System - Stopping Docker Containers (Windows PowerShell)" -ForegroundColor Cyan
Write-Host " Project root: $ProjectRoot" -ForegroundColor DarkGray
Write-Host "====================================================================" -ForegroundColor Cyan

try {
    Write-Host ">> Stopping docker-compose services..." -ForegroundColor Yellow
    docker compose down --remove-orphans
    Write-Host ">> Services stopped." -ForegroundColor Green
} catch {
    Write-Warning "Could not stop services cleanly: $_"
}
