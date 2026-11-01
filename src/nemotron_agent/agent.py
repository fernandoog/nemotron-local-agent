from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from ollama import Client

from .config import Settings
from .tools import OLLAMA_TOOLS, SYSTEM_PROMPT, ToolBox, ToolError


class NemotronAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Client(host=settings.ollama_host)
        self.tools = ToolBox(settings.workspace)
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def ensure_model(self) -> None:
        names = {m.model for m in self.client.list().models}
        if self.settings.model not in names:
            # Also accept tags without exact match variants listed by Ollama
            short = {n.split(":")[0] for n in names}
            model_base = self.settings.model.split(":")[0]
            if self.settings.model not in names and model_base not in short:
                raise RuntimeError(
                    f"Modelo {self.settings.model!r} no está en Ollama. "
                    f"Ejecuta: ollama pull {self.settings.model}"
                )

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _parse_args(self, raw: Any) -> dict[str, Any]:
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return {}
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {"value": raw}
        return {}

    def run(self, user_text: str, on_event: Callable[[str, Any], None] | None = None) -> str:
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(self.settings.max_steps):
            kwargs: dict[str, Any] = {
                "model": self.settings.model,
                "messages": self.messages,
                "tools": OLLAMA_TOOLS,
            }
            # Ollama think flag (Nemotron reasoning)
            try:
                response = self.client.chat(**kwargs, think=self.settings.think)
            except TypeError:
                response = self.client.chat(**kwargs)

            message = response.message
            thinking = getattr(message, "thinking", None)
            if thinking and on_event:
                on_event("thinking", thinking)

            tool_calls = getattr(message, "tool_calls", None) or []
            content = message.content or ""

            assistant_msg: dict[str, Any] = {"role": "assistant", "content": content}
            if thinking:
                assistant_msg["thinking"] = thinking
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self.messages.append(assistant_msg)

            if not tool_calls:
                if on_event and content:
                    on_event("answer", content)
                return content

            for call in tool_calls:
                fn = call.function
                name = fn.name
                args = self._parse_args(fn.arguments)
                if on_event:
                    on_event("tool_call", {"name": name, "arguments": args})
                try:
                    result = self.tools.dispatch(name, args)
                except ToolError as exc:
                    result = json.dumps({"error": str(exc)}, ensure_ascii=False)
                except Exception as exc:  # noqa: BLE001
                    result = json.dumps(
                        {"error": f"Fallo inesperado en {name}: {exc}"},
                        ensure_ascii=False,
                    )
                if on_event:
                    on_event("tool_result", {"name": name, "result": result[:2000]})
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": result,
                    }
                )

        fallback = (
            "He alcanzado el límite de pasos de herramientas. "
            "Prueba a reformular la tarea en partes más pequeñas."
        )
        if on_event:
            on_event("answer", fallback)
        return fallback
