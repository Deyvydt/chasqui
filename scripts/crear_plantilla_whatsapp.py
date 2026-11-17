"""Crea la plantilla de WhatsApp 'chasqui_evento' en Twilio y la envía a
aprobación de Meta (categoría UTILITY).

Solo hace falta cuando pases del sandbox a un número de WhatsApp propio
(producción). En el sandbox de la demo NO es necesaria: Chasqui manda el
mensaje libre dentro de la ventana de 24 h.

Uso:  python scripts/crear_plantilla_whatsapp.py
Luego, cuando esté aprobada, el script deja WHATSAPP_CONTENT_SID en tu .env.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from chasqui import config  # noqa: E402,F401  (carga el .env)
from scripts.utilidades_env import escribir_en_env  # noqa: E402

BASE = "https://content.twilio.com/v1/Content"
PLANTILLA = {
    "friendly_name": "chasqui_evento",
    "language": "es",
    "variables": {
        "1": "AWS Community Day Lima",
        "2": "sábado 6 de diciembre, 9:00 am",
        "3": "UTEC, Barranco",
        "4": "https://ejemplo.com/evento",
    },
    "types": {
        "twilio/text": {
            "body": (
                "Hola David, Chasqui te recuerda un evento tech importante:\n\n"
                "Evento: {{1}}\nFecha: {{2}}\nLugar: {{3}}\nMás info: {{4}}"
            )
        }
    },
}


def main() -> None:
    auth = (os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    r = httpx.post(BASE, json=PLANTILLA, auth=auth, timeout=30)
    r.raise_for_status()
    sid = r.json()["sid"]
    print(f"Plantilla creada: {sid}")

    a = httpx.post(
        f"{BASE}/{sid}/ApprovalRequests/whatsapp",
        json={"name": "chasqui_evento", "category": "UTILITY"},
        auth=auth,
        timeout=30,
    )
    a.raise_for_status()
    print("Enviada a aprobación de Meta. Estado:", a.json().get("status"))
    escribir_en_env("# WHATSAPP_CONTENT_SID", sid)
    print(
        "Cuando Meta la apruebe y cambies TWILIO_WHATSAPP_FROM a tu número propio,\n"
        f"descomenta en tu .env:  WHATSAPP_CONTENT_SID={sid}"
    )


if __name__ == "__main__":
    main()
