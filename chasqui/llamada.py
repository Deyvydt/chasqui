"""Despacha al agente de voz para que te llame (LiveKit Agent Dispatch)."""

from __future__ import annotations

import json
import logging
import uuid

from livekit import api

from . import config
from .modelos import Evento

log = logging.getLogger("chasqui.llamada")


async def despachar(eventos: list[Evento], modo_demo: bool = False) -> str:
    sala = f"chasqui-{uuid.uuid4().hex[:8]}"
    metadata = json.dumps(
        {
            "telefono": config.mi_telefono(),
            "modo_demo": modo_demo,
            "eventos": [e.a_dict() for e in eventos],
        },
        ensure_ascii=False,
    )
    async with api.LiveKitAPI() as lk:  # lee LIVEKIT_URL / API_KEY / API_SECRET
        await lk.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=config.AGENT_NAME, room=sala, metadata=metadata
            )
        )
    log.info("Agente despachado a la sala %s", sala)
    return sala
