"""Copia las keys de LiveKit desde la config del CLI `lk` (~/.livekit/cli-config.yaml)
a tu .env. Corre en tu PC: las keys nunca salen de tu máquina.

Uso:  python scripts/importar_livekit.py [nombre_proyecto]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

from scripts.utilidades_env import escribir_en_env  # noqa: E402

load_dotenv(RAIZ / ".env")
CONFIG = Path.home() / ".livekit" / "cli-config.yaml"


def main() -> None:
    if os.getenv("LIVEKIT_API_KEY") and "--forzar" not in sys.argv:
        print("✅ LiveKit ya está en tu .env")
        return
    if not CONFIG.exists():
        print(f"➖ No encontré {CONFIG}. Copia las keys a mano desde cloud.livekit.io → Settings → API Keys.")
        return
    import yaml

    datos = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    proyectos = datos.get("projects") or []
    if not proyectos:
        print("➖ Tu config de lk no tiene proyectos. Corre: lk cloud auth")
        return
    pedido = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    nombre = pedido or datos.get("default_project")
    proyecto = next((p for p in proyectos if p.get("name") == nombre), proyectos[0])
    for var, campo in (("LIVEKIT_URL", "url"), ("LIVEKIT_API_KEY", "api_key"), ("LIVEKIT_API_SECRET", "api_secret")):
        if not proyecto.get(campo):
            print(f"➖ Al proyecto '{proyecto.get('name')}' le falta {campo}.")
            return
        escribir_en_env(var, proyecto[campo])
    print(f"✅ Keys de LiveKit del proyecto '{proyecto.get('name')}' copiadas a tu .env")
    otros = [p.get("name") for p in proyectos if p is not proyecto]
    if otros:
        print(f"   (Otros proyectos disponibles: {', '.join(otros)}. Usa: python scripts/importar_livekit.py <nombre> --forzar)")


if __name__ == "__main__":
    main()
