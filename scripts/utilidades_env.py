"""Escribe o actualiza una variable en el archivo .env."""

from __future__ import annotations

from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / ".env"


def escribir_en_env(clave: str, valor: str) -> None:
    lineas = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    nueva = f"{clave}={valor}"
    for i, linea in enumerate(lineas):
        if linea.split("=", 1)[0].strip() == clave:
            lineas[i] = nueva
            break
    else:
        lineas.append(nueva)
    ENV.write_text("\n".join(lineas) + "\n", encoding="utf-8")
