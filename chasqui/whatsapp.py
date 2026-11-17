"""Envío del resumen por WhatsApp con Twilio.

- Demo (sandbox): mensaje libre. Funciona si en las últimas 24 h le escribiste
  "join <código>" al número del sandbox.
- Producción: si defines WHATSAPP_CONTENT_SID (plantilla aprobada por Meta,
  ver scripts/crear_plantilla_whatsapp.py), se envía con la plantilla.
"""

from __future__ import annotations

import json
import logging

from twilio.rest import Client

from . import config
from .modelos import Evento

log = logging.getLogger("chasqui.whatsapp")


def texto_resumen(ev: Evento) -> str:
    lineas = [
        "🏃 *Chasqui* — evento tech que no te puedes perder",
        "",
        f"📌 *{ev.nombre}*",
        f"📅 {ev.fecha_legible()}",
        f"📍 {ev.lugar or 'Lugar por confirmar'}" + (f" — {ev.direccion}" if ev.direccion and ev.direccion != ev.lugar else ""),
    ]
    if ev.url:
        lineas.append(f"🔗 {ev.url}")
    if ev.por_que:
        lineas += ["", f"💡 {ev.por_que}"]
    return "\n".join(lineas)


def variables_plantilla(ev: Evento) -> dict[str, str]:
    """Variables {{1}}..{{4}} de la plantilla 'chasqui_evento'."""
    return {
        "1": ev.nombre,
        "2": ev.fecha_legible(),
        "3": ev.lugar or ev.direccion or "Por confirmar",
        "4": ev.url or "—",
    }


def enviar(ev: Evento, telefono: str | None = None) -> str:
    telefono = telefono or config.mi_telefono()
    cliente = Client()  # lee TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN
    destino = f"whatsapp:{telefono}"
    if config.WHATSAPP_CONTENT_SID:
        msg = cliente.messages.create(
            from_=config.TWILIO_WHATSAPP_FROM,
            to=destino,
            content_sid=config.WHATSAPP_CONTENT_SID,
            content_variables=json.dumps(variables_plantilla(ev), ensure_ascii=False),
        )
    else:
        msg = cliente.messages.create(
            from_=config.TWILIO_WHATSAPP_FROM, to=destino, body=texto_resumen(ev)
        )
    log.info("WhatsApp enviado (%s) para '%s'", msg.sid, ev.nombre)
    return msg.sid
