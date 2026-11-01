# Lanza el agente (arranca Ollama si hace falta)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
} catch {
    Write-Host "Arrancando Ollama..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "No hay .venv. Ejecuta primero: .\scripts\setup.ps1" -ForegroundColor Red
    exit 1
}

if ($args.Count -gt 0) {
    & $py -m nemotron_agent @args
} else {
    & $py -m nemotron_agent
}
