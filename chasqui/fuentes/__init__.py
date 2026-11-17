"""Fuentes de eventos. Cada una devuelve list[Evento] y nunca rompe el pipeline."""

from __future__ import annotations

import logging

from ..modelos import Evento, normalizar
from . import buscador, luma

log = logging.getLogger("chasqui.fuentes")


def recolectar() -> list[Evento]:
    todos: list[Evento] = []
    todos += luma.buscar()
    todos += buscador.eventos_web()
    todos += buscador.titulares_linkedin()
    return deduplicar(todos)


def deduplicar(eventos: list[Evento]) -> list[Evento]:
    """Une eventos repetidos entre fuentes (mismo nombre normalizado)."""
    vistos: dict[str, Evento] = {}
    for ev in eventos:
        clave = normalizar(ev.nombre)[:60]
        if clave in vistos:
            base = vistos[clave]
            for campo in ("fecha_inicio", "fecha_fin", "lugar", "direccion", "url", "organizador", "descripcion"):
                if not getattr(base, campo) and getattr(ev, campo):
                    setattr(base, campo, getattr(ev, campo))
        else:
            vistos[clave] = ev
    log.info("Candidatos únicos: %d", len(vistos))
    return list(vistos.values())
