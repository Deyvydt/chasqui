"""Guarda eventos evaluados y cuáles ya te avisó (para no llamarte dos veces)."""

from __future__ import annotations

import json

from . import config
from .modelos import Evento, ahora


def guardar_eventos(eventos: list[Evento]) -> None:
    config.ARCHIVO_EVENTOS.write_text(
        json.dumps([e.a_dict() for e in eventos], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def cargar_eventos() -> list[Evento]:
    if not config.ARCHIVO_EVENTOS.exists():
        return []
    datos = json.loads(config.ARCHIVO_EVENTOS.read_text(encoding="utf-8"))
    return [Evento.de_dict(d) for d in datos]


def notificados() -> set[str]:
    if not config.ARCHIVO_NOTIFICADOS.exists():
        return set()
    return set(json.loads(config.ARCHIVO_NOTIFICADOS.read_text(encoding="utf-8")))


def marcar_notificados(eventos: list[Evento]) -> None:
    ids = notificados() | {e.id for e in eventos}
    config.ARCHIVO_NOTIFICADOS.write_text(json.dumps(sorted(ids), indent=2), encoding="utf-8")


def seleccionar(eventos: list[Evento], forzar: bool = False) -> tuple[list[Evento], bool]:
    """Devuelve (eventos_a_avisar, es_modo_demo).

    Solo pasan eventos futuros, verificados, con puntaje >= umbral y no avisados.
    Con forzar=True y sin imperdibles, toma el mejor futuro (modo demo).
    """
    ya = notificados()
    limite = ahora()
    futuros = [
        e for e in eventos
        if e.id not in ya and (e.inicio_dt() is None or e.inicio_dt() >= limite)
    ]
    importantes = [
        e for e in futuros
        if e.verificado and (e.puntaje or 0) >= config.UMBRAL_IMPORTANCIA
    ]
    importantes.sort(key=lambda e: e.puntaje or 0, reverse=True)
    if importantes:
        return importantes[: config.MAX_EVENTOS_POR_LLAMADA], False
    if forzar:
        candidatos = sorted(
            [e for e in futuros if e.puntaje is not None],
            key=lambda e: (e.verificado, e.puntaje or 0),
            reverse=True,
        )
        return candidatos[:1], True
    return [], False
