$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot 'backend')
$python=Join-Path (Get-Location) '.venv/Scripts/python.exe'
if (!(Test-Path $python)) { throw 'Missing Python venv. Run NEXIS_Setup.ps1 again.' }
Write-Host 'NEXIS Swagger: http://127.0.0.1:8000/docs' -ForegroundColor Cyan
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload