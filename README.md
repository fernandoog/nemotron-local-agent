# Nemotron Local Agent

Agente local con **NVIDIA Nemotron 3 Nano 4B** vía [Ollama](https://ollama.com), usando la GPU NVIDIA del equipo para razonar y ejecutar tareas (archivos, comandos, búsqueda web, cálculos).

Pensado para GPUs de **8 GB VRAM** (p. ej. RTX 4060 Laptop). El tag `nemotron-3-nano:4b` ocupa ~2.8–2.9 GB y deja margen para contexto.

## Requisitos

- Windows 10/11 con driver NVIDIA reciente (CUDA 12.x)
- [Ollama](https://ollama.com/download) instalado
- Python 3.11+

## Arranque rápido

```powershell
cd nemotron-local-agent
.\scripts\setup.ps1
.\scripts\run.ps1
```

Chat interactivo:

```text
tú> crea un script python que liste los primos hasta 50 y ejecútalo
tú> busca qué es Nemotron 3 Nano y resume en 5 bullets
tú> /reset
tú> /exit
```

Una sola tarea:

```powershell
.\scripts\run.ps1 "qué hora es y escribe un archivo nota.md con un saludo"
```

## Modelo

| Modelo | VRAM aprox. | Cuándo usarlo |
|--------|-------------|----------------|
| `nemotron-3-nano:4b` (default) | ~3–4 GB | RTX 8 GB |
| `nemotron-3-nano:30b` / `latest` | ~18–24 GB | RTX 24 GB+ |

Cambia el modelo en `.env`:

```env
NEMOTRON_MODEL=nemotron-3-nano:4b
OLLAMA_HOST=http://127.0.0.1:11434
NEMOTRON_THINK=true
NEMOTRON_WORKSPACE=./workspace
```

Descarga manual:

```powershell
ollama serve
ollama pull nemotron-3-nano:4b
```

## Herramientas del agente

| Tool | Descripción |
|------|-------------|
| `list_dir` / `read_file` / `write_file` / `append_file` | Ficheros dentro de `./workspace` |
| `run_command` | Shell en el workspace |
| `get_datetime` | Fecha/hora local |
| `calculator` | Aritmética segura |
| `web_search` | DuckDuckGo |

## Arquitectura

```text
tú  →  CLI (Rich)
         →  NemotronAgent (tool loop)
              →  Ollama (Nemotron en GPU)
              →  ToolBox (workspace local)
```

## Desarrollo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m nemotron_agent
```

## Licencia

- Código de este repo: MIT
- Modelo Nemotron: [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/)

## Créditos

- [NVIDIA Nemotron](https://huggingface.co/nvidia)
- [Ollama – nemotron-3-nano](https://ollama.com/library/nemotron-3-nano)
