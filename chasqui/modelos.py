"""Modelo de datos de un evento + utilidades de fechas en español."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import config

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


@dataclass
class Evento:
    nombre: str
    fuente: str  # "luma", "buscador", "linkedin-titular"
    fecha_inicio: str | None = None  # ISO 8601 con zona horaria
    fecha_fin: str | None = None
    lugar: str | None = None
    direccion: str | None = None
    url: str | None = None
    descripcion: str | None = None
    organizador: str | None = None
    # Lo llena el evaluador
    puntaje: int | None = None
    por_que: str | None = None
    verificado: bool = False
    fuentes_investigadas: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        dia = (self.fecha_inicio or "")[:10]
        base = f"{normalizar(self.nombre)}|{dia}"
        return hashlib.sha1(base.encode()).hexdigest()[:12]

    def inicio_dt(self) -> datetime | None:
        return parsear_fecha(self.fecha_inicio)

    def fin_dt(self) -> datetime | None:
        fin = parsear_fecha(self.fecha_fin)
        ini = self.inicio_dt()
        if fin is None and ini is not None:
            fin = ini + timedelta(hours=2)
        return fin

    def fecha_legible(self) -> str:
        ini = self.inicio_dt()
        if ini is None:
            return "fecha por confirmar"
        texto = f"{DIAS[ini.weekday()]} {ini.day} de {MESES[ini.month - 1]}"
        if ini.hour or ini.minute:
            texto += f", {ini.strftime('%I:%M %p').lstrip('0').lower()}"
        return texto

    def a_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return d

    @classmethod
    def de_dict(cls, d: dict) -> "Evento":
        campos = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**campos)


def parsear_fecha(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    tz = ZoneInfo(config.ZONA_HORARIA)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def ahora() -> datetime:
    return datetime.now(ZoneInfo(config.ZONA_HORARIA))
