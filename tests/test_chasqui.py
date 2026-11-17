"""Tests offline (sin APIs): modelos, selección, mensajes y parsing."""

from __future__ import annotations

from datetime import timedelta

import pytest

from chasqui import calendario, config, estado, whatsapp
from chasqui.agent import instrucciones
from chasqui.evaluador import aplicar_resultado
from chasqui.fuentes import deduplicar
from chasqui.fuentes.luma import _a_evento
from chasqui.ia import extraer_json
from chasqui.modelos import Evento, ahora


@pytest.fixture(autouse=True)
def datos_temporales(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ARCHIVO_EVENTOS", tmp_path / "eventos.json")
    monkeypatch.setattr(config, "ARCHIVO_NOTIFICADOS", tmp_path / "notificados.json")


def ev(nombre="AWS Community Day Lima", dias=5, puntaje=92, verificado=True, **kw):
    ini = (ahora() + timedelta(days=dias)).replace(hour=9, minute=0, second=0, microsecond=0)
    return Evento(nombre=nombre, fuente="buscador", fecha_inicio=ini.isoformat(),
                  puntaje=puntaje, verificado=verificado, lugar="UTEC", **kw)


def test_fecha_legible_en_espanol():
    e = Evento(nombre="x", fuente="t", fecha_inicio="2026-12-05T18:30:00-05:00")
    assert e.fecha_legible() == "sábado 5 de diciembre, 6:30 pm"


def test_fin_por_defecto_dos_horas():
    e = Evento(nombre="x", fuente="t", fecha_inicio="2026-12-05T18:00:00-05:00")
    assert (e.fin_dt() - e.inicio_dt()) == timedelta(hours=2)


def test_seleccion_solo_imperdibles():
    eventos = [ev("A", puntaje=95), ev("B", puntaje=60), ev("C", puntaje=90, verificado=False)]
    elegidos, demo = estado.seleccionar(eventos)
    assert [e.nombre for e in elegidos] == ["A"] and demo is False


def test_seleccion_ignora_pasados_y_notificados():
    a, b = ev("A", dias=-1), ev("B")
    estado.marcar_notificados([b])
    assert estado.seleccionar([a, b]) == ([], False)


def test_forzar_activa_modo_demo():
    elegidos, demo = estado.seleccionar([ev("Meetup", puntaje=55)], forzar=True)
    assert demo is True and elegidos[0].nombre == "Meetup"


def test_extraer_json_con_texto_alrededor():
    assert extraer_json('Aquí va:\n```json\n[{"a": 1}]\n```') == [{"a": 1}]
    assert extraer_json('blah {"x": 2} blah') == {"x": 2}


def test_deduplicar_completa_campos():
    a = Evento(nombre="DevFest Lima 2026", fuente="luma")
    b = Evento(nombre="DevFest  Lima 2026!", fuente="buscador", url="https://devfest.pe")
    unicos = deduplicar([a, b])
    assert len(unicos) == 1 and unicos[0].url == "https://devfest.pe"


def test_evaluador_no_acepta_links_de_linkedin():
    e = Evento(nombre="x", fuente="linkedin-titular")
    aplicar_resultado(e, {"puntaje": 130, "verificado": True, "url": "https://www.linkedin.com/events/123"})
    assert e.puntaje == 100 and e.url is None


def test_mensaje_whatsapp():
    texto = whatsapp.texto_resumen(ev(url="https://ejemplo.pe", por_que="Hay speakers de AWS."))
    for parte in ("AWS Community Day Lima", "📅", "UTEC", "https://ejemplo.pe", "speakers"):
        assert parte in texto


def test_cuerpo_calendario():
    cuerpo = calendario.cuerpo_evento(ev())
    assert cuerpo["summary"] == "AWS Community Day Lima"
    assert cuerpo["start"]["timeZone"] == "America/Lima"


def test_luma_filtra_ciudad():
    lima = {"event": {"name": "IA Lima", "url": "abc", "start_at": "2030-01-01T23:00:00Z",
                      "geo_address_info": {"city": "Lima", "full_address": "Av. X, Lima, Perú"}}}
    sf = {"event": {"name": "SF AI", "geo_address_info": {"city": "San Francisco"}}}
    assert _a_evento(lima).url == "https://lu.ma/abc"
    assert _a_evento(sf) is None


def test_instrucciones_incluyen_eventos_y_demo():
    texto = instrucciones([ev(por_que="Te conviene.")], modo_demo=True)
    assert "AWS Community Day Lima" in texto and "PRUEBA" in texto


def test_proveedor_ia_elige_la_key_disponible(monkeypatch):
    from chasqui import ia
    for var in ("PROVEEDOR_IA", "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert ia.proveedor() == "anthropic"
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    assert ia.proveedor() == "gemini"
    monkeypatch.setenv("PROVEEDOR_IA", "openai")
    assert ia.proveedor() == "openai"


def test_link_calendario_en_whatsapp():
    e = Evento(nombre="DevFest Lima", fuente="t", fecha_inicio="2026-12-05T18:00:00-05:00")
    link = calendario.link_agregar(e)
    assert "dates=20261205T230000Z%2F20261206T010000Z" in link
    assert "Agregar a tu calendario" in whatsapp.texto_resumen(e)
