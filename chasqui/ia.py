"""LLM con búsqueda web para buscar e investigar eventos.

Soporta 3 proveedores (elige con PROVEEDOR_IA en tu .env):
  - gemini    -> Gemini API + Grounding with Google Search   (GEMINI_API_KEY)
  - openai    -> OpenAI Responses API + web_search            (OPENAI_API_KEY)
  - anthropic -> Claude Messages API + web_search             (ANTHROPIC_API_KEY)
Si no defines PROVEEDOR_IA, usa el primero que tenga key en ese orden.
"""

from __future__ import annotations

import json
import logging
import os
import re

import httpx

from . import config

log = logging.getLogger("chasqui.ia")
TIMEOUT = httpx.Timeout(180.0)

KEYS = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
MODELOS = {"gemini": "gemini-2.5-flash", "openai": "gpt-5-mini", "anthropic": "claude-haiku-5-5"}


def proveedor() -> str:
    elegido = os.getenv("PROVEEDOR_IA", "").strip().lower()
    if elegido:
        if elegido not in KEYS:
            raise RuntimeError(f"PROVEEDOR_IA debe ser uno de {list(KEYS)}")
        return elegido
    for nombre, var in KEYS.items():
        if os.getenv(var, "").strip():
            return nombre
    raise RuntimeError("Pon GEMINI_API_KEY, OPENAI_API_KEY o ANTHROPIC_API_KEY en tu .env")


def modelo(prov: str) -> str:
    return os.getenv("MODELO_INVESTIGADOR", "").strip() or MODELOS[prov]


def extraer_json(texto: str):
    """Saca el primer bloque JSON (objeto o lista) de un texto del modelo."""
    texto = texto.strip()
    bloque = re.search(r"```(?:json)?\s*(.+?)```", texto, re.S)
    if bloque:
        texto = bloque.group(1).strip()
    for abre, cierra in (("[", "]"), ("{", "}")):
        i, j = texto.find(abre), texto.rfind(cierra)
        if i != -1 and j > i:
            try:
                return json.loads(texto[i : j + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"El modelo no devolvió JSON válido: {texto[:300]}")


def _gemini(prompt: str) -> str:
    m = modelo("gemini")
    r = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json={"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    partes = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in partes)


def _openai(prompt: str) -> str:
    r = httpx.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={
            "model": modelo("openai"),
            "input": prompt,
            "tools": [{
                "type": "web_search",
                "user_location": {"type": "approximate", "city": config.CIUDAD,
                                  "country": config.PAIS, "timezone": config.ZONA_HORARIA},
            }],
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    textos = [
        c.get("text", "")
        for item in r.json().get("output", []) if item.get("type") == "message"
        for c in item.get("content", []) if c.get("type") == "output_text"
    ]
    return "".join(textos)


def _anthropic(prompt: str) -> str:
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
        json={
            "model": modelo("anthropic"),
            "max_tokens": 8000,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [{
                "type": "web_search_20250305", "name": "web_search", "max_uses": 8,
                "user_location": {"type": "approximate", "city": config.CIUDAD,
                                  "country": config.PAIS, "timezone": config.ZONA_HORARIA},
            }],
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")


_LLAMADAS = {"gemini": _gemini, "openai": _openai, "anthropic": _anthropic}


def preguntar_con_busqueda(prompt: str):
    """Ejecuta el prompt con búsqueda web en el proveedor elegido y devuelve el JSON."""
    prov = proveedor()
    log.info("Investigando con %s (%s)", prov, modelo(prov))
    return extraer_json(_LLAMADAS[prov](prompt))
