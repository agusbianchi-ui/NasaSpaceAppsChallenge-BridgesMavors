$ErrorActionPreference = 'Stop'
$frontend = Join-Path $PSScriptRoot 'WebApp/frontend'
$backend = Join-Path $PSScriptRoot 'WebApp/backend'
$logs = Join-Path $PSScriptRoot 'integration-review'
if (-not (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath (Join-Path $backend '.venv/Scripts/python.exe') -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $backend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'backend.log') -RedirectStandardError (Join-Path $logs 'backend-error.log')
}
if (-not (Get-NetTCPConnection -LocalPort 4173 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath (Get-Command node).Source -ArgumentList 'node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','4173','--strictPort' -WorkingDirectory $frontend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'frontend.log') -RedirectStandardError (Join-Path $logs 'frontend-error.log')
}
Write-Host 'Open http://127.0.0.1:4173/explorer'
