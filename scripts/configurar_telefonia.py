"""Configura TODA la telefonía automáticamente:

  Twilio Elastic SIP Trunk  ->  credenciales  ->  número  ->  troncal saliente en LiveKit

Al final escribe SIP_OUTBOUND_TRUNK_ID en tu .env.

Uso:  python scripts/configurar_telefonia.py
Requiere en .env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, LIVEKIT_URL,
LIVEKIT_API_KEY, LIVEKIT_API_SECRET. Opcional: TWILIO_NUMERO (si ya tienes uno).
"""

from __future__ import annotations

import asyncio
import os
import secrets
import string
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from livekit import api  # noqa: E402
from twilio.rest import Client  # noqa: E402

from chasqui import config  # noqa: E402  (carga el .env)
from scripts.utilidades_env import escribir_en_env  # noqa: E402


def _password() -> str:
    alfabeto = string.ascii_letters + string.digits
    while True:
        p = "".join(secrets.choice(alfabeto) for _ in range(24))
        if any(c.islower() for c in p) and any(c.isupper() for c in p) and any(c.isdigit() for c in p):
            return p


def configurar_twilio() -> tuple[str, str, str, str]:
    tw = Client()
    sufijo = secrets.token_hex(3)
    dominio = f"chasqui-{sufijo}.pstn.twilio.com"

    print("1/4 Creando Elastic SIP Trunk en Twilio...")
    trunk = tw.trunking.v1.trunks.create(friendly_name=f"chasqui-{sufijo}", domain_name=dominio)

    print("2/4 Creando credenciales para que LiveKit pueda usar el trunk...")
    usuario, clave = f"livekit{sufijo}", _password()
    cl = tw.sip.credential_lists.create(friendly_name=f"chasqui-livekit-{sufijo}")
    tw.sip.credential_lists(cl.sid).credentials.create(username=usuario, password=clave)
    tw.trunking.v1.trunks(trunk.sid).credentials_lists.create(credential_list_sid=cl.sid)

    print("3/4 Asignando un número de Twilio al trunk...")
    numero = os.getenv("TWILIO_NUMERO", "").strip()
    if numero:
        encontrados = tw.incoming_phone_numbers.list(phone_number=numero, limit=1)
        if not encontrados:
            sys.exit(f"No encontré {numero} en tu cuenta de Twilio.")
        num = encontrados[0]
    else:
        disponible = tw.available_phone_numbers("US").local.list(voice_enabled=True, limit=1)
        if not disponible:
            sys.exit("Twilio no devolvió números disponibles. Compra uno en la consola y ponlo en TWILIO_NUMERO.")
        elegido = disponible[0].phone_number
        ok = input(f"   ¿Compro el número {elegido} (usa tu crédito de Twilio)? [s/N] ").strip().lower()
        if ok != "s":
            sys.exit("Cancelado. Pon un número existente en TWILIO_NUMERO y vuelve a correr.")
        num = tw.incoming_phone_numbers.create(phone_number=elegido)
    tw.trunking.v1.trunks(trunk.sid).phone_numbers.create(phone_number_sid=num.sid)
    escribir_en_env("TWILIO_NUMERO", num.phone_number)
    return dominio, num.phone_number, usuario, clave


async def configurar_livekit(dominio: str, numero: str, usuario: str, clave: str) -> str:
    print("4/4 Registrando el troncal saliente en LiveKit...")
    async with api.LiveKitAPI() as lk:
        trunk = await lk.sip.create_outbound_trunk(
            api.CreateSIPOutboundTrunkRequest(
                trunk=api.SIPOutboundTrunkInfo(
                    name="chasqui-twilio",
                    address=dominio,
                    numbers=[numero],
                    auth_username=usuario,
                    auth_password=clave,
                )
            )
        )
    return trunk.sip_trunk_id


def main() -> None:
    dominio, numero, usuario, clave = configurar_twilio()
    trunk_id = asyncio.run(configurar_livekit(dominio, numero, usuario, clave))
    escribir_en_env("SIP_OUTBOUND_TRUNK_ID", trunk_id)
    print(f"\n✅ Listo. Número Twilio: {numero} | Troncal LiveKit: {trunk_id}")
    print("   Ya quedó guardado en tu .env. Te llamarán a:", config.mi_telefono())


if __name__ == "__main__":
    main()
