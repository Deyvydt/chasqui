"""Investiga cada evento en otras fuentes y le pone un puntaje según tu perfil."""

from __future__ import annotations

import json
import logging

from . import config
from .ia import preguntar_con_busqueda
from .modelos import Evento, ahora

log = logging.getLogger("chasqui.evaluador")

RUBRICA = """Rúbrica de puntaje (0-100), sé exigente: hay muchísimos meetups.
- 90-100 IMPERDIBLE: conferencia/summit grande o única en el año (ej. AWS Summit,
  Google I/O Extended o DevFest grande, Microsoft AI Tour), hackathon con premios
  o contratación, speakers internacionales de alto nivel, o networking directo
  con empresas que contratan AI/MLOps/Cloud engineers.
- 75-89 MUY BUENO: muy alineado a su perfil y con algo diferencial (taller
  práctico de LLMOps/agentes, certificación gratis, comunidad fuerte).
- 50-74 NORMAL: meetup o charla estándar.
- 0-49 NO VALE LA PENA: poco relacionado, comercial, o información dudosa.
Si el evento ya pasó, es online-only, o no se puede confirmar fecha y lugar,
baja el puntaje a menos de 50."""


def _prompt(perfil: str, lote: list[Evento]) -> str:
    entrada = [
        {
            "idx": i,
            "nombre": e.nombre,
            "fuente": e.fuente,
            "fecha_inicio": e.fecha_inicio,
            "lugar": e.lugar,
            "url": e.url,
            "organizador": e.organizador,
            "descripcion": e.descripcion,
        }
        for i, e in enumerate(lote)
    ]
    return f"""Eres el asistente que filtra eventos tech para esta persona:

{perfil}

Hoy es {ahora().strftime('%Y-%m-%d')} y la persona vive en {config.CIUDAD}, Perú.

Para CADA evento de la lista, investiga con el buscador en fuentes distintas a
LinkedIn (web oficial, Meetup, Eventbrite, Luma, redes de la comunidad, noticias)
de qué trata, quién lo organiza, speakers, fecha exacta, hora y lugar.
Los eventos con fuente "linkedin-titular" solo tienen un titular: confirma sus
datos en otras fuentes.

{RUBRICA}

Eventos:
{json.dumps(entrada, ensure_ascii=False, indent=1)}

Devuelve SOLO una lista JSON, un elemento por evento:
{{"idx": int, "puntaje": int, "verificado": bool (fecha y lugar confirmados),
 "por_que": "2-3 frases en español, hablándole de tú, de por qué le conviene ir
            según su perfil (o por qué no)",
 "fecha_inicio": "YYYY-MM-DDTHH:MM:SS-05:00" o null,
 "fecha_fin": str o null, "lugar": str o null, "direccion": str o null,
 "url": "enlace oficial (no LinkedIn)" o null,
 "fuentes": [urls consultadas]}}"""


def evaluar(eventos: list[Evento], tam_lote: int = 5) -> list[Evento]:
    perfil = config.ARCHIVO_PERFIL.read_text(encoding="utf-8")
    eventos = eventos[: config.MAX_CANDIDATOS]
    for i in range(0, len(eventos), tam_lote):
        lote = eventos[i : i + tam_lote]
        try:
            resultados = preguntar_con_busqueda(_prompt(perfil, lote))
        except Exception as e:  # noqa: BLE001
            log.warning("No pude evaluar el lote %d: %s", i // tam_lote, e)
            continue
        for r in resultados if isinstance(resultados, list) else []:
            try:
                ev = lote[int(r["idx"])]
            except (KeyError, ValueError, IndexError, TypeError):
                continue
            aplicar_resultado(ev, r)
    return sorted(eventos, key=lambda e: e.puntaje or 0, reverse=True)


def aplicar_resultado(ev: Evento, r: dict) -> None:
    ev.puntaje = max(0, min(100, int(r.get("puntaje") or 0)))
    ev.verificado = bool(r.get("verificado"))
    ev.por_que = r.get("por_que") or ev.por_que
    ev.fuentes_investigadas = [u for u in r.get("fuentes") or [] if isinstance(u, str)]
    for campo in ("fecha_inicio", "fecha_fin", "lugar", "direccion"):
        if r.get(campo):
            setattr(ev, campo, r[campo])
    url = r.get("url")
    if url and "linkedin.com" not in url:
        ev.url = url
