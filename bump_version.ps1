<#
.SYNOPSIS
    Sonance Universal Version Bumper (PowerShell for Windows)
.DESCRIPTION
    Interactively prompts for new version or accepts it via argument, then
    propagates the version across the entire Sonance project.
.EXAMPLE
    .\bump_version.ps1
.EXAMPLE
    .\bump_version.ps1 2.25
.EXAMPLE
    .\bump_version.ps1 4.8
#>

param(
    [Parameter(Position=0, Mandatory=$false)]
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if ([string]::IsNullOrWhiteSpace($Version)) {
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host "       🎵 Sonance Audiophile Workstation - Version Bumper       " -ForegroundColor Cyan
    Write-Host "========================================================================" -ForegroundColor Cyan
    $Version = Read-Host "Enter new version (e.g. 2.25, 4.8, 3.7.0)"
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    Write-Error "[-] Error: Version cannot be empty."
    exit 1
}

# Run python engine
python update_version.py $Version
