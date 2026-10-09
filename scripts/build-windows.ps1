param([string]$OutputDir = "dist")
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$version = python -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
$stage = Join-Path (Get-Location) "build/windows-stage"
New-Item -ItemType Directory -Force "$stage/site" | Out-Null
python -m pip install --no-compile --target "$stage/site" .
@'
@echo off
set "PYTHONPATH=%~dp0site;%PYTHONPATH%"
py -3.12 -m chatgpt_tun %*
'@ | Set-Content "$stage/ctun.cmd" -Encoding ascii
Copy-Item "$stage/ctun.cmd" "$stage/ctun.cmd"
@'
$ErrorActionPreference = "Stop"
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $env:LOCALAPPDATA "Programs\ctun"
New-Item -ItemType Directory -Force $target | Out-Null
Copy-Item -Force -Recurse (Join-Path $source "*") $target
Write-Host "Installed CTUN to $target"
Write-Host "Add $target to your user PATH, then run ctun.cmd --help"
Write-Host "Requires Python 3.12 and ngrok on PATH."
'@ | Set-Content "$stage/install.ps1" -Encoding utf8
New-Item -ItemType Directory -Force $OutputDir | Out-Null
Compress-Archive -Force -Path "$stage/*" -DestinationPath "$OutputDir/ctun_${version}_windows_amd64.zip"
