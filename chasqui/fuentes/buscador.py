"""Fuente: buscador web (vía la herramienta web_search de OpenAI).

1) titulares_linkedin(): pide al buscador eventos de linkedin.com/events en Lima
   y se queda SOLO con el titular y la fecha que aparecen en los resultados.
   No se inicia sesión ni se automatiza nada dentro de LinkedIn.
2) eventos_web(): busca eventos tech en Lima en Meetup, Eventbrite, GDG,
   comunidades AWS/Azure, universidades, etc.
"""

from __future__ import annotations

import logging

from .. import config
from ..ia import preguntar_con_busqueda
from ..modelos import Evento, ahora

log = logging.getLogger("chasqui.buscador")

FORMATO = """Devuelve SOLO una lista JSON (sin texto extra). Cada elemento:
{"nombre": str, "fecha_inicio": "YYYY-MM-DDTHH:MM:SS-05:00" o null,
 "fecha_fin": str o null, "lugar": str o null, "direccion": str o null,
 "url": str o null, "organizador": str o null, "descripcion": str (1 frase) o null}"""


def _rango() -> str:
    hoy = ahora().date()
    return f"entre {hoy.isoformat()} y los próximos {config.DIAS_ADELANTE} días"


def titulares_linkedin() -> list[Evento]:
    prompt = f"""Usa el buscador para encontrar eventos de tecnología (IA, software,
cloud, data, DevOps, startups, developers) publicados en linkedin.com/events que
ocurran presencialmente en {config.CIUDAD}, Perú, {_rango()}.
Usa SOLO el título y el fragmento (snippet) que muestran los resultados del
buscador; no hace falta abrir LinkedIn. Máximo 10 eventos.
Pon "url": null (no copies enlaces de LinkedIn).
{FORMATO}"""
    try:
        datos = preguntar_con_busqueda(prompt)
    except Exception as e:  # noqa: BLE001
        log.warning("Buscador (titulares LinkedIn) falló: %s", e)
        return []
    eventos = [_a_evento(d, "linkedin-titular") for d in datos if isinstance(d, dict)]
    eventos = [e for e in eventos if e]
    log.info("Titulares de LinkedIn vía buscador: %d", len(eventos))
    return eventos


def eventos_web() -> list[Evento]:
    prompt = f"""Busca en la web eventos de tecnología importantes que ocurran
presencialmente en {config.CIUDAD}, Perú, {_rango()}: conferencias, summits,
hackathons, meetups de IA/ML, cloud (AWS, Google, Azure), data, DevOps,
developers y startups. Revisa Meetup, Eventbrite, Luma, GDG, AWS User Group,
comunidades, universidades (UTEC, PUCP, UNI) y webs oficiales.
Incluye solo eventos con fecha real encontrada en la fuente. Máximo 15 eventos.
{FORMATO}"""
    try:
        datos = preguntar_con_busqueda(prompt)
    except Exception as e:  # noqa: BLE001
        log.warning("Buscador (eventos web) falló: %s", e)
        return []
    eventos = [_a_evento(d, "buscador") for d in datos if isinstance(d, dict)]
    eventos = [e for e in eventos if e]
    log.info("Eventos web vía buscador: %d", len(eventos))
    return eventos


def _a_evento(d: dict, fuente: str) -> Evento | None:
    if not d.get("nombre"):
        return None
    url = d.get("url")
    if fuente == "linkedin-titular" or (url and "linkedin.com" in url):
        url = None
    return Evento(
        nombre=str(d["nombre"]).strip(),
        fuente=fuente,
        fecha_inicio=d.get("fecha_inicio"),
        fecha_fin=d.get("fecha_fin"),
        lugar=d.get("lugar"),
        direccion=d.get("direccion"),
        url=url,
        organizador=d.get("organizador"),
        descripcion=d.get("descripcion"),
    )
