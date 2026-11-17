"""Agente de voz de Chasqui (LiveKit Agents).

Se ejecuta como worker:  python -m chasqui.agent dev
Cuando `python -m chasqui llamar` lo despacha, el agente:
  1. Te llama a tu celular por el troncal SIP (Twilio).
  2. Te cuenta el/los evento(s) y por qué te conviene ir.
  3. Si le dices que sí, lo agenda en tu Google Calendar.
  4. Te deja el resumen por WhatsApp (siempre, aunque cuelgues antes).
"""

from __future__ import annotations

import asyncio
import json
import logging

from livekit import api
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    inference,
)
from livekit.agents.beta import EndCallTool
from livekit.plugins import silero

from . import calendario, config, whatsapp
from .modelos import Evento

log = logging.getLogger("chasqui.agent")
IDENTIDAD_DAVID = "david"


def instrucciones(eventos: list[Evento], modo_demo: bool) -> str:
    lista = "\n".join(
        f"{i}. {e.nombre} | {e.fecha_legible()} | {e.lugar or 'lugar por confirmar'}"
        f"{' (' + e.direccion + ')' if e.direccion else ''} | puntaje {e.puntaje}/100\n"
        f"   Por qué ir: {e.por_que or 'sin detalle'}"
        for i, e in enumerate(eventos, start=1)
    )
    aviso_demo = (
        "\nIMPORTANTE: esta es una llamada de PRUEBA de la demo. No se encontró "
        "ningún evento imperdible, así que cuéntale que es una prueba y preséntale "
        "el mejor evento que se encontró, siendo honesta con que no es imperdible.\n"
        if modo_demo
        else ""
    )
    return f"""Eres Chasqui, la asistente personal de David por teléfono. David es
ingeniero de software e IA en Lima. Lo llamas SOLO cuando hay eventos tech que
realmente no debería perderse.
{aviso_demo}
Cómo hablas:
- Español peruano, limeño, cálido y natural. Puedes usar muletillas suaves
  ("ya", "oye", "mira", "bacán", "chévere") sin exagerar.
- Es una llamada: frases cortas, nada de listas, nada de emojis ni símbolos.
- No leas URLs en voz alta; di que se las mandas por WhatsApp.
- Di las fechas de forma natural ("el jueves 4 de diciembre a las 6 de la tarde").

Guion:
1. Saluda: "¡Hola David! Te habla Chasqui" y pregunta si tiene un minuto.
2. Cuéntale el evento (o eventos) y por qué le conviene ir, en 2-3 frases.
3. Pregúntale si quiere que lo agende en su calendario. Si dice que sí, usa
   la herramienta agendar_en_calendario. Si duda, responde sus preguntas con
   la información que tienes; si no sabes algo, dilo con honestidad.
4. Usa enviar_resumen_whatsapp para cada evento y avísale que ya le llegó.
5. Despídete corto y usa end_call para colgar.
Si David está ocupado: dile que le mandas todo por WhatsApp, envíalo y cuelga.

Eventos (numerados desde 1):
{lista}
"""


class Chasqui(Agent):
    def __init__(self, eventos: list[Evento], modo_demo: bool, telefono: str) -> None:
        super().__init__(
            instructions=instrucciones(eventos, modo_demo),
            tools=[EndCallTool(end_instructions="Despídete de David en una frase corta.")],
        )
        self.eventos = eventos
        self.telefono = telefono
        self.whatsapp_enviados: set[int] = set()
        self.agendados: set[int] = set()

    def _evento(self, numero_evento: int) -> Evento:
        if not 1 <= numero_evento <= len(self.eventos):
            raise ValueError(f"No existe el evento {numero_evento}")
        return self.eventos[numero_evento - 1]

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Saluda a David por su nombre, preséntate como Chasqui y pregúntale si tiene un minuto."
        )

    @function_tool()
    async def agendar_en_calendario(self, context: RunContext, numero_evento: int) -> str:
        """Agenda un evento en el Google Calendar de David. Úsala solo cuando
        David confirme que quiere ir o que lo agendes.

        Args:
            numero_evento: número del evento en la lista (empieza en 1).
        """
        if numero_evento in self.agendados:
            return "Ese evento ya está agendado."
        ev = self._evento(numero_evento)
        if not calendario.configurado():
            self.agendados.add(numero_evento)
            return ("Calendar automático no está configurado: dile a David que en el "
                    "WhatsApp le llega un link para agregarlo a su calendario con un toque.")
        try:
            await asyncio.to_thread(calendario.agendar, ev)
        except Exception as e:  # noqa: BLE001
            log.exception("Falló Calendar")
            return f"No se pudo agendar ({e}). Dile a David que se lo mandas por WhatsApp."
        self.agendados.add(numero_evento)
        return f"Listo: '{ev.nombre}' quedó en su calendario con recordatorios."

    @function_tool()
    async def enviar_resumen_whatsapp(self, context: RunContext, numero_evento: int) -> str:
        """Envía a David por WhatsApp el nombre, fecha, lugar, link y el porqué
        del evento.

        Args:
            numero_evento: número del evento en la lista (empieza en 1).
        """
        if numero_evento in self.whatsapp_enviados:
            return "Ese resumen ya se envió."
        ev = self._evento(numero_evento)
        try:
            await asyncio.to_thread(whatsapp.enviar, ev, self.telefono)
        except Exception as e:  # noqa: BLE001
            log.exception("Falló WhatsApp")
            return f"No se pudo enviar el WhatsApp ({e})."
        self.whatsapp_enviados.add(numero_evento)
        return "WhatsApp enviado."

    async def enviar_pendientes(self) -> None:
        """Al colgar: manda por WhatsApp lo que no se alcanzó a enviar."""
        for n in range(1, len(self.eventos) + 1):
            if n not in self.whatsapp_enviados:
                try:
                    await asyncio.to_thread(whatsapp.enviar, self.eventos[n - 1], self.telefono)
                    self.whatsapp_enviados.add(n)
                except Exception:  # noqa: BLE001
                    log.exception("No se pudo enviar WhatsApp pendiente")


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name=config.AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    datos = json.loads(ctx.job.metadata or "{}")
    telefono = datos.get("telefono") or config.mi_telefono()
    eventos = [Evento.de_dict(d) for d in datos.get("eventos", [])]
    if not eventos:
        log.error("La llamada llegó sin eventos; no llamo.")
        ctx.shutdown()
        return

    await ctx.connect()
    log.info("Llamando a %s por %d evento(s)", telefono, len(eventos))
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=config.sip_trunk_id(),
                sip_call_to=telefono,
                participant_identity=IDENTIDAD_DAVID,
                participant_name="David",
                wait_until_answered=True,
            )
        )
    except (api.TwirpError, api.SipCallError) as e:
        log.error("No se pudo llamar (¿no contestaste o falla del troncal SIP?): %s", e)
        # Igual te deja el WhatsApp para que no te pierdas el evento
        for ev in eventos:
            try:
                await asyncio.to_thread(whatsapp.enviar, ev, telefono)
            except Exception:  # noqa: BLE001
                log.exception("Tampoco salió el WhatsApp")
        ctx.shutdown()
        return

    agente = Chasqui(eventos, bool(datos.get("modo_demo")), telefono)
    ctx.add_shutdown_callback(agente.enviar_pendientes)

    session = AgentSession(
        stt=inference.STT(model=config.STT_VOZ, language="es"),
        llm=inference.LLM(model=config.LLM_VOZ),
        tts=inference.TTS(model=config.TTS_VOZ, language="es"),
        vad=ctx.proc.userdata["vad"],
    )
    await ctx.wait_for_participant(identity=IDENTIDAD_DAVID)
    await session.start(agent=agente, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
