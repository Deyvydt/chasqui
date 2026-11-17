"""Agenda eventos en tu Google Calendar con una cuenta de servicio.

La cuenta de servicio no necesita login en el navegador: solo compartes tu
calendario con su correo (permiso "Hacer cambios en eventos").
"""

from __future__ import annotations

import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build

from . import config
from .modelos import Evento

log = logging.getLogger("chasqui.calendario")
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _servicio():
    cred = service_account.Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=cred, cache_discovery=False)


def cuerpo_evento(ev: Evento) -> dict:
    ini, fin = ev.inicio_dt(), ev.fin_dt()
    if ini is None:
        raise ValueError(f"'{ev.nombre}' no tiene fecha: no se puede agendar")
    descripcion = "\n\n".join(
        x for x in [ev.por_que, ev.url and f"Más info: {ev.url}", "Agendado por Chasqui 🏃"] if x
    )
    return {
        "summary": ev.nombre,
        "location": ", ".join(x for x in [ev.lugar, ev.direccion] if x) or None,
        "description": descripcion,
        "start": {"dateTime": ini.isoformat(), "timeZone": config.ZONA_HORARIA},
        "end": {"dateTime": fin.isoformat(), "timeZone": config.ZONA_HORARIA},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 24 * 60}, {"method": "popup", "minutes": 120}],
        },
    }


def configurado() -> bool:
    import os
    from pathlib import Path

    return Path(config.GOOGLE_SERVICE_ACCOUNT_FILE).exists() and bool(os.getenv("GOOGLE_CALENDAR_ID", "").strip())


def link_agregar(ev: Evento) -> str | None:
    """Link de 'Agregar a Google Calendar' (funciona sin ninguna configuración)."""
    from urllib.parse import urlencode
    from zoneinfo import ZoneInfo

    ini, fin = ev.inicio_dt(), ev.fin_dt()
    if ini is None:
        return None
    utc = ZoneInfo("UTC")
    fmt = "%Y%m%dT%H%M%SZ"
    params = {
        "action": "TEMPLATE",
        "text": ev.nombre,
        "dates": f"{ini.astimezone(utc).strftime(fmt)}/{fin.astimezone(utc).strftime(fmt)}",
        "details": "\n\n".join(x for x in [ev.por_que, ev.url] if x),
        "location": ", ".join(x for x in [ev.lugar, ev.direccion] if x),
        "ctz": config.ZONA_HORARIA,
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def agendar(ev: Evento) -> str:
    creado = (
        _servicio()
        .events()
        .insert(calendarId=config.google_calendar_id(), body=cuerpo_evento(ev))
        .execute()
    )
    log.info("Agendado en Calendar: %s", creado.get("htmlLink"))
    return creado.get("htmlLink", "")
