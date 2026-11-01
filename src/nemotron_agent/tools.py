from __future__ import annotations

import ast
import json
import operator
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from duckduckgo_search import DDGS


ToolFn = Callable[..., str]


class ToolError(Exception):
    pass


class ToolBox:
    """Herramientas del agente, acotadas al workspace local."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, relative: str) -> Path:
        candidate = (self.workspace / relative).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise ToolError(
                f"Ruta fuera del workspace: {relative!r}. "
                f"Solo se permite trabajar dentro de {self.workspace}"
            ) from exc
        return candidate

    def list_dir(self, path: str = ".") -> str:
        target = self.resolve_path(path)
        if not target.exists():
            raise ToolError(f"No existe: {path}")
        if not target.is_dir():
            raise ToolError(f"No es un directorio: {path}")
        entries = []
        for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            kind = "dir" if item.is_dir() else "file"
            size = item.stat().st_size if item.is_file() else "-"
            entries.append({"name": item.name, "type": kind, "size": size})
        return json.dumps({"path": path, "entries": entries}, ensure_ascii=False, indent=2)

    def read_file(self, path: str, max_chars: int = 20000) -> str:
        target = self.resolve_path(path)
        if not target.is_file():
            raise ToolError(f"Archivo no encontrado: {path}")
        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            return text[:max_chars] + f"\n\n...[truncado, {len(text)} chars totales]"
        return text

    def write_file(self, path: str, content: str) -> str:
        target = self.resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return json.dumps(
            {"ok": True, "path": path, "bytes": len(content.encode("utf-8"))},
            ensure_ascii=False,
        )

    def append_file(self, path: str, content: str) -> str:
        target = self.resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(content)
        return json.dumps({"ok": True, "path": path, "appended": len(content)}, ensure_ascii=False)

    def run_command(self, command: str, timeout_sec: int = 60) -> str:
        """Ejecuta un comando de shell dentro del workspace (Windows PowerShell/cmd)."""
        if not command or not command.strip():
            raise ToolError("command vacío")
        blocked = ("format ", "del /s", "rm -rf /", "shutdown", "reg delete")
        lowered = command.lower()
        if any(b in lowered for b in blocked):
            raise ToolError("Comando bloqueado por seguridad")

        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(self.workspace),
            capture_output=True,
            text=True,
            timeout=max(1, min(timeout_sec, 120)),
            encoding="utf-8",
            errors="replace",
        )
        payload = {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-8000:],
            "stderr": completed.stderr[-4000:],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def get_datetime(self, timezone_name: str = "") -> str:
        now = datetime.now().astimezone()
        return json.dumps(
            {
                "iso": now.isoformat(),
                "local": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "timezone_hint": timezone_name or str(now.tzinfo),
            },
            ensure_ascii=False,
        )

    def calculator(self, expression: str) -> str:
        """Evalúa expresiones aritméticas simples de forma segura."""
        allowed_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def _eval(node: ast.AST) -> float:
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return float(node.value)
            if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
                return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
                return allowed_ops[type(node.op)](_eval(node.operand))
            raise ToolError(f"Expresión no permitida: {expression!r}")

        try:
            tree = ast.parse(expression, mode="eval")
            result = _eval(tree)
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(f"No se pudo calcular: {exc}") from exc
        return json.dumps({"expression": expression, "result": result}, ensure_ascii=False)

    def web_search(self, query: str, max_results: int = 5) -> str:
        max_results = max(1, min(int(max_results), 8))
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        simplified = [
            {
                "title": r.get("title"),
                "href": r.get("href"),
                "body": r.get("body"),
            }
            for r in results
        ]
        return json.dumps({"query": query, "results": simplified}, ensure_ascii=False, indent=2)

    def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        mapping: dict[str, ToolFn] = {
            "list_dir": self.list_dir,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "append_file": self.append_file,
            "run_command": self.run_command,
            "get_datetime": self.get_datetime,
            "calculator": self.calculator,
            "web_search": self.web_search,
        }
        if name not in mapping:
            raise ToolError(f"Herramienta desconocida: {name}")
        try:
            return mapping[name](**arguments)
        except TypeError as exc:
            raise ToolError(f"Argumentos inválidos para {name}: {exc}") from exc


OLLAMA_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Lista archivos y carpetas dentro del workspace del agente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Ruta relativa al workspace. Por defecto '.'.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lee un archivo de texto del workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta relativa del archivo"},
                    "max_chars": {
                        "type": "integer",
                        "description": "Máximo de caracteres a devolver",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Crea o sobrescribe un archivo de texto en el workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_file",
            "description": "Añade texto al final de un archivo del workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Ejecuta un comando de shell en el workspace "
                "(útil para python, git status, dir, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout_sec": {"type": "integer"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Devuelve la fecha y hora local actuales.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone_name": {
                        "type": "string",
                        "description": "Pista opcional de zona horaria",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Calcula una expresión aritmética (+ - * / ** %).",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Busca información actual en la web con DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
]


SYSTEM_PROMPT = """Eres Nemotron Local Agent, un asistente de NVIDIA Nemotron que corre 100% en local con GPU.
Tu objetivo es completar tareas del usuario usando herramientas cuando haga falta.

Reglas:
- Trabaja solo dentro del workspace asignado para archivos.
- Prefiere herramientas concretas antes de inventar datos (fecha, cálculos, ficheros, web).
- Si creas o editas archivos, confirma la ruta relativa.
- Responde en el idioma del usuario.
- Sé directo y útil; resume el resultado final con claridad.
"""
