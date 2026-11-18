"""Tests de la fase 7: contrafactual sin leakage, detección de un efecto conocido y placebos."""
import numpy as np
import pandas as pd
import pytest

from vhp import calendar as cal
from vhp import evaluate as ev
from vhp import intervention as iv


def _grilla(salto=0.0, n_semanas=45, semilla=0):
    """Serie sintética con efecto lunes, ruido y un salto multiplicativo desde la semana 35."""
    rng = np.random.default_rng(semilla)
    dias = pd.DatetimeIndex(cal.dias_habiles("2025-06-02", pd.Timestamp("2025-06-02") + pd.Timedelta(7 * n_semanas, unit="D")))
    y = 300 * (1 + 0.3 * (dias.dayofweek == 0)) * np.exp(rng.normal(0, 0.08, len(dias)))
    fecha = dias[dias >= pd.Timestamp("2025-06-02") + pd.Timedelta(7 * 35, unit="D")][0]
    y = pd.Series(np.where(dias >= fecha, y * (1 + salto), y), index=dias)
    todos = pd.date_range(dias.min(), dias.max())
    clima = pd.DataFrame({"fecha": todos, "temperature_2m_max": 18.0, "precipitation_sum": 0.0})
    return ev.armar_grilla(y, clima), fecha


def test_contrafactual_no_usa_datos_posteriores():
    g, fecha = _grilla()
    r1 = iv.contrafactual(g, fecha, 24, log=True, n_sim=200)
    g2 = g.copy()
    g2.loc[g2.index >= fecha, ["y", "y_modelo"]] *= 5
    r2 = iv.contrafactual(g2, fecha, 24, log=True, n_sim=200)
    pd.testing.assert_series_equal(r1["diario"]["cf_med"], r2["diario"]["cf_med"])
    assert r2["efecto_pct"] > r1["efecto_pct"] + 300


def test_detecta_un_salto_de_30_por_ciento_y_no_inventa_uno_nulo():
    g, fecha = _grilla(salto=0.30)
    r = iv.contrafactual(g, fecha, 24, log=True, n_sim=500)
    assert r["pct_inf"] > 10 and 15 < r["efecto_pct"] < 45
    g0, _ = _grilla(salto=0.0)
    r0 = iv.contrafactual(g0, fecha, 24, log=True, n_sim=500)
    assert r0["pct_inf"] < 0 < r0["pct_sup"]


def test_placebos_terminan_antes_del_evento_y_esquivan_eventos():
    g, fecha = _grilla()
    otro = fecha - pd.Timedelta(30, unit="D")
    fs = iv.fechas_placebo(g, fecha, 24, [fecha, otro], n=6)
    assert fs
    for f in fs:
        ventana = g.index[g.index.searchsorted(f):][:24]
        assert ventana.max() < fecha and not (ventana.min() <= otro <= ventana.max())


@pytest.mark.parametrize("clave", ["agencia_meta", "postres_web", "suba_precio"])
def test_eventos_yaml_tiene_fecha_y_series_conocidas(clave):
    e = iv.cargar_eventos()["eventos"][clave]
    pd.Timestamp(e["fecha"])
    assert set(e["series"]) <= {"viandas_particulares", "tasa_postre_particulares", "tasa_pan_particulares",
                                "tasa_extras_particulares"}
