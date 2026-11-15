$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
docker build -t nexis-demo-lab:latest ./docker/demo-lab
if ($LASTEXITCODE -ne 0) { throw 'Docker image build failed' }
Write-Host 'Demo lab image built. Update backend/.env: NEXIS_ALLOW_DOCKER=true' -ForegroundColor Green