# Importa un GGUF local a Ollama como nemotron-3-nano:4b
# Uso:
#   .\scripts\import-gguf.ps1
#   .\scripts\import-gguf.ps1 -GgufPath "D:\path\model.gguf"
param(
    [string]$GgufPath = "",
    [string]$ModelName = "nemotron-3-nano:4b"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $GgufPath) {
    $found = Get-ChildItem -Path "$Root\models" -Recurse -Filter "*.gguf" -ErrorAction SilentlyContinue |
        Sort-Object Length -Descending |
        Select-Object -First 1
    if (-not $found) {
        Write-Host "No hay .gguf en models\. Descarga primero, por ejemplo:" -ForegroundColor Red
        Write-Host "  .\.venv\Scripts\python.exe -c `"from huggingface_hub import hf_hub_download; print(hf_hub_download('nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF', 'NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf', local_dir='models/nemotron-4b-gguf'))`""
        exit 1
    }
    $GgufPath = $found.FullName
}

if (-not (Test-Path $GgufPath)) {
    Write-Host "No existe: $GgufPath" -ForegroundColor Red
    exit 1
}

$abs = (Resolve-Path $GgufPath).Path
$modelfile = Join-Path $Root "Modelfile.nemotron"
@"
FROM $abs
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER num_ctx 8192
SYSTEM Eres Nemotron Local Agent. Usa herramientas cuando haga falta y responde en el idioma del usuario.
"@ | Set-Content -Path $modelfile -Encoding utf8

Write-Host "Creando modelo Ollama $ModelName desde:" -ForegroundColor Cyan
Write-Host "  $abs"
ollama create $ModelName -f $modelfile
Write-Host "Listo. Prueba: ollama run $ModelName" -ForegroundColor Green
