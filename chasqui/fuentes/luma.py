"""Fuente: Luma (lu.ma). Usa el endpoint público de 'discover' que usa la web.

Es un endpoint no oficial: si Luma lo cambia, esta fuente devuelve [] y el
resto del pipeline sigue funcionando con el buscador.
"""

from __future__ import annotations

import logging

import httpx

from .. import config
from ..modelos import Evento, ahora, parsear_fecha

log = logging.getLogger("chasqui.luma")

URL = "https://api.lu.ma/discover/get-paginated-events"
LIMA = {"geo_latitude": "-12.0464", "geo_longitude": "-77.0428"}
PALABRAS_CIUDAD = ("lima", "miraflores", "san isidro", "barranco", "surco", "peru", "perú")


def _a_evento(item: dict) -> Evento | None:
    ev = item.get("event") or item
    nombre = ev.get("name")
    if not nombre:
        return None
    geo = ev.get("geo_address_info") or {}
    ciudad = " ".join(
        str(geo.get(k, "")) for k in ("city", "city_state", "full_address", "region", "country")
    ).lower()
    if ciudad and not any(p in ciudad for p in PALABRAS_CIUDAD):
        return None
    slug = ev.get("url") or ""
    cal = item.get("calendar") or {}
    return Evento(
        nombre=nombre,
        fuente="luma",
        fecha_inicio=ev.get("start_at"),
        fecha_fin=ev.get("end_at"),
        lugar=geo.get("address") or geo.get("city") or ("Online" if ev.get("location_type") == "online" else None),
        direccion=geo.get("full_address"),
        url=f"https://lu.ma/{slug}" if slug and not slug.startswith("http") else slug or None,
        organizador=cal.get("name"),
    )


def buscar() -> list[Evento]:
    params = {**LIMA, "pagination_limit": "50"}
    try:
        r = httpx.get(URL, params=params, timeout=20, headers={"User-Agent": "chasqui/0.1"})
        r.raise_for_status()
        datos = r.json()
    except Exception as e:  # noqa: BLE001
        log.warning("Luma no respondió (%s). Sigo sin esta fuente.", e)
        return []

    limite = ahora()
    eventos = []
    for item in datos.get("entries", []):
        ev = _a_evento(item)
        if ev is None:
            continue
        ini = parsear_fecha(ev.fecha_inicio)
        if ini and ini < limite:
            continue
        eventos.append(ev)
    log.info("Luma: %d eventos en %s", len(eventos), config.CIUDAD)
    return eventos
