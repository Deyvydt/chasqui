"""Configuración central: todo sale de variables de entorno (.env)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def _req(nombre: str) -> str:
    valor = os.getenv(nombre, "").strip()
    if not valor:
        raise RuntimeError(
            f"Falta la variable {nombre} en tu .env (mira .env.example y el README)."
        )
    return valor


def _opt(nombre: str, defecto: str = "") -> str:
    return os.getenv(nombre, defecto).strip()


# --- Tú ---
def mi_telefono() -> str:
    return _req("MI_TELEFONO")  # formato E.164, ej. +51999999999


ZONA_HORARIA = _opt("ZONA_HORARIA", "America/Lima")
CIUDAD = _opt("CIUDAD", "Lima")
PAIS = _opt("PAIS", "PE")
DIAS_ADELANTE = int(_opt("DIAS_ADELANTE", "45"))

# --- Filtro de importancia ---
UMBRAL_IMPORTANCIA = int(_opt("UMBRAL_IMPORTANCIA", "80"))
MAX_EVENTOS_POR_LLAMADA = int(_opt("MAX_EVENTOS_POR_LLAMADA", "3"))
MAX_CANDIDATOS = int(_opt("MAX_CANDIDATOS", "15"))

# --- LLM para buscar e investigar (OpenAI Responses API + web_search) ---
MODELO_INVESTIGADOR = _opt("MODELO_INVESTIGADOR", "gpt-5-mini")

# --- LiveKit (voz) ---
AGENT_NAME = _opt("AGENT_NAME", "chasqui")
STT_VOZ = _opt("STT_VOZ", "deepgram/nova-3")
LLM_VOZ = _opt("LLM_VOZ", "openai/gpt-4.1-mini")
# Daniela: voz femenina latina (es-MX) de Cartesia vía LiveKit Inference
TTS_VOZ = _opt("TTS_VOZ", "cartesia/sonic-3:5c5ad5e7-1020-476b-8b91-fdcbe9cc313c")


def sip_trunk_id() -> str:
    return _req("SIP_OUTBOUND_TRUNK_ID")


# --- Twilio WhatsApp ---
TWILIO_WHATSAPP_FROM = _opt("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # sandbox
WHATSAPP_CONTENT_SID = _opt("WHATSAPP_CONTENT_SID")  # plantilla aprobada (opcional)

# --- Google Calendar ---
GOOGLE_SERVICE_ACCOUNT_FILE = _opt(
    "GOOGLE_SERVICE_ACCOUNT_FILE", str(RAIZ / "credenciales" / "google-sa.json")
)


def google_calendar_id() -> str:
    return _req("GOOGLE_CALENDAR_ID")  # tu correo de Gmail


# --- Archivos locales ---
DATA_DIR = RAIZ / "data"
DATA_DIR.mkdir(exist_ok=True)
ARCHIVO_EVENTOS = DATA_DIR / "eventos.json"
ARCHIVO_NOTIFICADOS = DATA_DIR / "notificados.json"
ARCHIVO_PERFIL = RAIZ / "perfil.md"
