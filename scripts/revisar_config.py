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
    "LIVEKIT_URL": "LiveKit Cloud",
    "LIVEKIT_API_KEY": "LiveKit Cloud",
    "LIVEKIT_API_SECRET": "LiveKit Cloud",
    "TWILIO_ACCOUNT_SID": "Twilio (llamadas + WhatsApp)",
    "TWILIO_AUTH_TOKEN": "Twilio (llamadas + WhatsApp)",
    "SIP_OUTBOUND_TRUNK_ID": "lo crea scripts/configurar_telefonia.py",
}


def main() -> None:
    faltan = 0
    for var, para in REQUERIDAS.items():
        ok = bool(os.getenv(var, "").strip())
        faltan += not ok
        print(f"{'✅' if ok else '❌'} {var:<24} {para}")
    keys = [k for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY") if os.getenv(k, "").strip()]
    print(f"{'✅' if keys else '❌'} {'IA (una key)':<24} {', '.join(keys) or 'Gemini, OpenAI o Anthropic'}")
    faltan += not keys
    sa = Path(config.GOOGLE_SERVICE_ACCOUNT_FILE)
    estado_cal = "agenda automático" if sa.exists() else "opcional: sin esto llega link por WhatsApp"
    print(f"{'✅' if sa.exists() else '➖'} {'google-sa.json':<24} {estado_cal}")
    print("\nTodo listo 🚀" if not faltan else f"\nFaltan {faltan} cosas (mira el README).")
    sys.exit(1 if faltan else 0)


if __name__ == "__main__":
    main()
