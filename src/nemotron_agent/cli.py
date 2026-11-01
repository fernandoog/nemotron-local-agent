from __future__ import annotations

import argparse
import sys
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from .agent import NemotronAgent
from .config import load_settings

console = Console()


def _on_event(kind: str, payload: Any) -> None:
    if kind == "thinking":
        console.print(
            Panel(
                str(payload)[:2500],
                title="thinking",
                border_style="dim",
                expand=False,
            )
        )
    elif kind == "tool_call":
        console.print(
            f"[cyan]→ tool[/] [bold]{payload['name']}[/] "
            f"[dim]{payload['arguments']}[/]"
        )
    elif kind == "tool_result":
        preview = str(payload["result"]).replace("\n", " ")
        if len(preview) > 160:
            preview = preview[:160] + "…"
        console.print(f"[green]← {payload['name']}[/] [dim]{preview}[/]")


def run_repl(one_shot: str | None = None) -> int:
    settings = load_settings()
    agent = NemotronAgent(settings)

    console.print(
        Panel.fit(
            f"[bold]Nemotron Local Agent[/]\n"
            f"Modelo: [cyan]{settings.model}[/]\n"
            f"Ollama: [cyan]{settings.ollama_host}[/]\n"
            f"Workspace: [cyan]{settings.workspace}[/]\n"
            f"Think: [cyan]{settings.think}[/]",
            border_style="green",
        )
    )

    try:
        agent.ensure_model()
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/] {exc}")
        console.print(
            "Asegúrate de que Ollama está en marcha y el modelo descargado:\n"
            "  ollama serve\n"
            f"  ollama pull {settings.model}"
        )
        return 1

    if one_shot is not None:
        console.print(Rule("[bold]tarea[/]"))
        console.print(f"[bold]tú>[/] {one_shot}")
        answer = agent.run(one_shot, on_event=_on_event)
        console.print(Markdown(answer or "_(sin respuesta)_"))
        return 0

    console.print(
        "[dim]Comandos: /reset  /exit  /help — escribe una tarea y Enter[/]\n"
    )

    while True:
        try:
            user = console.input("[bold green]tú>[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Adiós.[/]")
            return 0

        if not user:
            continue
        if user in {"/exit", "/quit", ":q"}:
            return 0
        if user == "/reset":
            agent.reset()
            console.print("[yellow]Memoria reiniciada.[/]")
            continue
        if user == "/help":
            console.print(
                "Herramientas: list_dir, read_file, write_file, append_file, "
                "run_command, get_datetime, calculator, web_search\n"
                "El agente puede crear scripts, consultar la web y ejecutar comandos "
                "dentro de ./workspace"
            )
            continue

        console.print(Rule("[dim]agente[/]"))
        try:
            answer = agent.run(user, on_event=_on_event)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Fallo al hablar con Ollama:[/] {exc}")
            continue
        console.print()
        console.print(Markdown(answer or "_(sin respuesta)_"))
        console.print()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="nemotron-agent",
        description="Agente local NVIDIA Nemotron (Ollama + GPU)",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Tarea opcional en una sola línea (si se omite, abre chat interactivo)",
    )
    args = parser.parse_args(argv)
    one_shot = " ".join(args.prompt) if args.prompt else None
    raise SystemExit(run_repl(one_shot))


if __name__ == "__main__":
    main(sys.argv[1:])
