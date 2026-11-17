"""CLI de Chasqui.

  python -m chasqui buscar              # recolecta + investiga + puntúa
  python -m chasqui ver                 # muestra lo último evaluado
  python -m chasqui llamar [--forzar]   # te llama si hay algo imperdible
  python -m chasqui correr [--forzar]   # buscar + llamar (lo que corre el cron)
  python -m chasqui probar-whatsapp     # te manda un WhatsApp de prueba
  python -m chasqui probar-calendario   # crea un evento de prueba en Calendar
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import timedelta

from . import calendario, config, estado, evaluador, fuentes, llamada, whatsapp
from .modelos import Evento, ahora

log = logging.getLogger("chasqui")


def cmd_buscar() -> list[Evento]:
    candidatos = fuentes.recolectar()
    if not candidatos:
        print("No encontré candidatos. Revisa tu OPENAI_API_KEY y tu conexión.")
        return []
    print(f"Investigando {min(len(candidatos), config.MAX_CANDIDATOS)} eventos (toma 1-3 min)...")
    evaluados = evaluador.evaluar(candidatos)
    estado.guardar_eventos(evaluados)
    cmd_ver(evaluados)
    return evaluados


def cmd_ver(eventos: list[Evento] | None = None) -> None:
    eventos = eventos if eventos is not None else estado.cargar_eventos()
    if not eventos:
        print("Aún no hay eventos. Corre: python -m chasqui buscar")
        return
    print(f"\n{'PTS':>4}  {'OK':2}  {'FECHA':<28} EVENTO")
    for e in eventos:
        marca = "✔" if e.verificado else "·"
        imperdible = "  ⭐" if e.verificado and (e.puntaje or 0) >= config.UMBRAL_IMPORTANCIA else ""
        print(f"{e.puntaje if e.puntaje is not None else '-':>4}  {marca:2}  {e.fecha_legible():<28} {e.nombre}{imperdible}")
    print(f"\n⭐ = pasa el umbral ({config.UMBRAL_IMPORTANCIA}) y será motivo de llamada.\n")


def cmd_llamar(forzar: bool) -> None:
    eventos = estado.cargar_eventos()
    elegidos, modo_demo = estado.seleccionar(eventos, forzar=forzar)
    if not elegidos:
        print("Nada imperdible por ahora: no te llamo. (Usa --forzar para la demo.)")
        return
    for e in elegidos:
        print(f"→ {e.nombre} ({e.puntaje}/100)")
    sala = asyncio.run(llamada.despachar(elegidos, modo_demo=modo_demo))
    estado.marcar_notificados(elegidos)
    print(f"📞 Chasqui te está llamando a {config.mi_telefono()} (sala {sala}).")
    if modo_demo:
        print("   (Modo demo: no había imperdibles, te llama con el mejor encontrado.)")


def _evento_prueba() -> Evento:
    ini = (ahora() + timedelta(days=1)).replace(hour=19, minute=0, second=0, microsecond=0)
    return Evento(
        nombre="[PRUEBA] Chasqui funciona",
        fuente="prueba",
        fecha_inicio=ini.isoformat(),
        lugar="Prueba de integración",
        por_que="Si ves esto, la integración funciona. Puedes borrarlo.",
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="chasqui", description="Tu chasqui de eventos tech en Lima")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("buscar")
    sub.add_parser("ver")
    for nombre in ("llamar", "correr"):
        sp = sub.add_parser(nombre)
        sp.add_argument("--forzar", action="store_true", help="modo demo: llama aunque no haya imperdibles")
    sub.add_parser("probar-whatsapp")
    sub.add_parser("probar-calendario")
    args = p.parse_args()

    if args.cmd == "buscar":
        cmd_buscar()
    elif args.cmd == "ver":
        cmd_ver()
    elif args.cmd == "llamar":
        cmd_llamar(args.forzar)
    elif args.cmd == "correr":
        cmd_buscar()
        cmd_llamar(args.forzar)
    elif args.cmd == "probar-whatsapp":
        sid = whatsapp.enviar(_evento_prueba())
        print(f"✅ WhatsApp enviado ({sid}). Revisa tu celular.")
    elif args.cmd == "probar-calendario":
        link = calendario.agendar(_evento_prueba())
        print(f"✅ Evento de prueba creado: {link}")


if __name__ == "__main__":
    main()
