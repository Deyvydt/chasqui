"""Cliente OpenAI (Responses API) con búsqueda web y salida JSON."""

from __future__ import annotations

import json
import logging
import re

from openai import OpenAI

from . import config

log = logging.getLogger("chasqui.ia")
_cliente: OpenAI | None = None


def cliente() -> OpenAI:
    global _cliente
    if _cliente is None:
        _cliente = OpenAI()  # lee OPENAI_API_KEY del entorno
    return _cliente


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


def preguntar_con_busqueda(prompt: str, dominios: list[str] | None = None):
    """Ejecuta un prompt con la herramienta web_search y devuelve el JSON."""
    herramienta: dict = {
        "type": "web_search",
        "user_location": {
            "type": "approximate",
            "city": config.CIUDAD,
            "country": config.PAIS,
            "timezone": config.ZONA_HORARIA,
        },
    }
    if dominios:
        herramienta["filters"] = {"allowed_domains": dominios}
    resp = cliente().responses.create(
        model=config.MODELO_INVESTIGADOR,
        tools=[herramienta],
        input=prompt,
    )
    return extraer_json(resp.output_text)
