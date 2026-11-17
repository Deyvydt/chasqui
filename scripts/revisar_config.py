"""Revisa que tu .env tenga todo lo necesario antes de la demo."""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from chasqui import config  # noqa: E402  (carga el .env)

REQUERIDAS = {
    "MI_TELEFONO": "tu celular (+51...)",
    "OPENAI_API_KEY": "buscar e investigar eventos",
    "LIVEKIT_URL": "LiveKit Cloud",
    "LIVEKIT_API_KEY": "LiveKit Cloud",
    "LIVEKIT_API_SECRET": "LiveKit Cloud",
    "TWILIO_ACCOUNT_SID": "Twilio (llamadas + WhatsApp)",
    "TWILIO_AUTH_TOKEN": "Twilio (llamadas + WhatsApp)",
    "SIP_OUTBOUND_TRUNK_ID": "lo crea scripts/configurar_telefonia.py",
    "GOOGLE_CALENDAR_ID": "tu correo de Gmail",
}


def main() -> None:
    faltan = 0
    for var, para in REQUERIDAS.items():
        ok = bool(os.getenv(var, "").strip())
        faltan += not ok
        print(f"{'✅' if ok else '❌'} {var:<24} {para}")
    sa = Path(config.GOOGLE_SERVICE_ACCOUNT_FILE)
    print(f"{'✅' if sa.exists() else '❌'} {'google-sa.json':<24} {sa}")
    faltan += not sa.exists()
    print("\nTodo listo 🚀" if not faltan else f"\nFaltan {faltan} cosas (mira el README).")
    sys.exit(1 if faltan else 0)


if __name__ == "__main__":
    main()
