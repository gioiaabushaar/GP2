$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot 'backend')
& ./.venv/Scripts/python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }