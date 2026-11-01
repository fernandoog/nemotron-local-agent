# Setup de Nemotron Local Agent (Windows + GPU NVIDIA)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Nemotron Local Agent setup" -ForegroundColor Cyan
Write-Host "Carpeta: $Root"

# .env
if (-not (Test-Path "$Root\.env")) {
    Copy-Item "$Root\.env.example" "$Root\.env"
    Write-Host "Creado .env desde .env.example"
}

# Ollama
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host "Ollama no está instalado." -ForegroundColor Red
    Write-Host "Descárgalo en https://ollama.com/download e instálalo, luego vuelve a ejecutar este script."
    exit 1
}
Write-Host "Ollama: $($ollama.Source)"

# Arrancar Ollama si no responde
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
    Write-Host "Ollama ya está en marcha."
} catch {
    Write-Host "Arrancando ollama serve en segundo plano..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# Python venv
if (-not (Test-Path "$Root\.venv")) {
    Write-Host "Creando .venv..."
    python -m venv .venv
}
& "$Root\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$Root\.venv\Scripts\python.exe" -m pip install -e .

$model = "nemotron-3-nano:4b"
if (Test-Path "$Root\.env") {
    $line = Get-Content "$Root\.env" | Where-Object { $_ -match '^NEMOTRON_MODEL=' } | Select-Object -First 1
    if ($line) { $model = ($line -split '=', 2)[1].Trim() }
}

Write-Host "Descargando modelo $model (cabe en RTX 8GB)..." -ForegroundColor Yellow
ollama pull $model

Write-Host ""
Write-Host "Listo." -ForegroundColor Green
Write-Host "Ejecuta:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  nemotron-agent"
Write-Host "o:"
Write-Host "  python -m nemotron_agent `"dime la hora y crea un archivo hola.txt`""
