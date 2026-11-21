"""Tests de la fase 5: sin leakage en el walk-forward y métricas."""
import numpy as np
import pandas as pd
import pytest

from vhp import calendar as cal
from vhp import evaluate as ev
from vhp.models import baselines, ets, lgbm, mlp, sarimax


def _grilla(n_semanas=40, semilla=0):
    """Grilla sintética con tendencia, efecto lunes, ruido y los feriados reales de UY."""
    rng = np.random.default_rng(semilla)
    dias = pd.DatetimeIndex(cal.dias_habiles("2025-06-02", pd.Timestamp("2025-06-02") + pd.Timedelta(7 * n_semanas, unit="D")))
    y = pd.Series(500 + 5 * np.arange(len(dias)) + 100 * (dias.dayofweek == 0) + rng.normal(0, 20, len(dias)),
                  index=dias)
    todos = pd.date_range(dias.min(), dias.max())
    clima = pd.DataFrame({"fecha": todos, "temperature_2m_max": rng.normal(18, 5, len(todos)),
                          "precipitation_sum": rng.exponential(2, len(todos))})
    return ev.armar_grilla(y, clima)


MODELOS = {
    "naive_estacional": baselines.modelo("naive_estacional"),
    "ets": ets.modelo(),
    "sarima": sarimax.modelo(),
    "lgbm_directo": lgbm.directo(ev.EXOG_CAL),
    "mlp": mlp.modelo(ev.EXOG_CAL, epocas_max=5, paciencia=2),
    "sarimax": sarimax.modelo_calendario(ev.EXOG_CAL),  # el modelo del proyecto
}


@pytest.mark.parametrize("nombre", list(MODELOS))
def test_sin_leakage_cambiar_el_futuro_no_cambia_el_pronostico(nombre):
    """Si se altera todo lo posterior al origen (y y clima), el pronóstico no cambia.
    Cubre también el escalado del MLP (se ajusta solo con hist)."""
    g = _grilla()
    origen = [d for d in g.index if d.dayofweek == 5][-3]
    g2 = g.copy()
    despues = g2.index > origen
    g2.loc[despues, ["y", "y_modelo"]] *= 10
    g2.loc[g2.index > origen + pd.Timedelta(7, unit="D"), ev.EXOG_CLIMA] += 30  # clima después de la semana objetivo
    p1 = MODELOS[nombre](*ev.partir(g, origen))
    p2 = MODELOS[nombre](*ev.partir(g2, origen))
    pd.testing.assert_frame_equal(p1, p2)


def test_partir_no_entrega_y_futura():
    g = _grilla()
    origen = [d for d in g.index if d.dayofweek == 5][-2]
    hist, fut = ev.partir(g, origen)
    assert hist.index.max() == origen and fut.index.min() > origen
    assert "y" not in fut and "y_modelo" not in fut and len(fut) == 6


def test_origenes_son_sabados_y_la_ultima_semana_termina_en_fin_test():
    g = _grilla()
    fin = [d for d in g.index if d.dayofweek == 5][-1]
    o = ev.origenes(g, 4, fin)
    assert len(o) == 4 and all(d.dayofweek == 5 for d in o)
    assert o[-1] + pd.Timedelta(7, unit="D") == fin


def test_grilla_alinea_periodo_y_rellena_cerrados_con_la_semana_anterior():
    dias = pd.bdate_range("2026-08-03", "2026-08-31", freq="C", weekmask="Mon Tue Wed Thu Fri Sat")
    dias = dias[dias != "2026-08-25"]  # feriado no laborable
    y = pd.Series(np.arange(len(dias), dtype=float) + 1, index=dias)
    clima = pd.DataFrame({"fecha": pd.date_range("2026-08-01", "2026-09-01"), "temperature_2m_max": 15.0,
                          "precipitation_sum": 0.0})
    g = ev.armar_grilla(y, clima)
    assert g.loc["2026-08-25", "abierto"] == 0 and np.isnan(g.loc["2026-08-25", "y"])
    assert g.loc["2026-08-25", "y_modelo"] == g.loc["2026-08-18", "y"]
    assert (g["t"].diff().dropna() == 1).all()


def test_escalado_del_mlp_no_usa_validacion_ni_futuro(monkeypatch):
    """El StandardScaler del MLP se ajusta solo con filas de entrenamiento: su día
    objetivo es anterior al tramo de validación (últimas 4 semanas de hist)."""
    g = _grilla()
    origen = [d for d in g.index if d.dayofweek == 5][-3]
    hist, fut = ev.partir(g, origen)
    vistos = []
    original = mlp.StandardScaler.fit

    def espia(self, X, *a, **k):
        vistos.append(len(X))
        return original(self, X, *a, **k)

    monkeypatch.setattr(mlp.StandardScaler, "fit", espia)
    mlp.modelo(ev.EXOG_CAL, epocas_max=2, paciencia=1, semanas_validacion=4)(hist, fut)
    _, _, pos, _, _ = lgbm.rasgos(hist, fut, ev.EXOG_CAL)
    assert vistos == [int((pos < len(hist) - 6 * 4).sum())]


def test_intervalo_usa_solo_los_12_origenes_previos():
    """El intervalo de un origen sale de y/ŷ en los 12 orígenes anteriores, no del propio origen."""
    sab = pd.date_range("2026-01-03", periods=14, freq="7D")
    filas = []
    for i, o in enumerate(sab):
        r = 1.0 + 0.01 * i if i < 13 else 5.0  # el último origen tiene un error enorme
        filas.append({"modelo": "m", "origen": o, "fecha": o + pd.Timedelta(2, unit="D"), "h": 1, "y": 100 * r,
                      "q0.1": np.nan, "q0.5": 100.0, "q0.9": np.nan, "escala_mase": 1.0})
    res = pd.DataFrame(filas)
    out = ev.intervalos(res, [sab[12], sab[13]], semanas=12)
    r12 = 1.0 + 0.01 * np.arange(12)
    assert out.loc[0, "q0.1"] == pytest.approx(100 * np.percentile(r12, 10))
    assert out.loc[1, "q0.9"] == pytest.approx(100 * np.percentile(1.0 + 0.01 * np.arange(1, 13), 90))


def test_metricas_mase_y_wape():
    res = pd.DataFrame({"modelo": "m", "y": [10.0, 20.0], "q0.1": [5, 15], "q0.5": [12, 18], "q0.9": [15, 25],
                        "escala_mase": [2.0, 2.0]})
    m = ev.metricas(res).iloc[0]
    assert m["MAE"] == 2 and m["MASE"] == 1 and m["WAPE"] == pytest.approx(4 / 30) and m["cobertura_80"] == 1


def test_diebold_mariano_detecta_al_mejor():
    rng = np.random.default_rng(1)
    e1, e2 = rng.normal(0, 1, 200), rng.normal(0, 3, 200)
    dm, p = ev.diebold_mariano(e1, e2)
    assert dm < 0 and p < 0.01


@pytest.mark.parametrize("modelo", ["lgbm_directo", "sarimax"])
@pytest.mark.parametrize("uid", ["Total", "Total/particulares", "Total/empresas"])
def test_series_del_backtest_no_miran_el_futuro(uid, modelo):
    """Con las series reales del backtest (Total y segmentos, datos públicos × K):
    alterar lo posterior al origen no cambia el pronóstico de LightGBM directo ni de SARIMAX."""
    from vhp import pronostico
    try:
        g = pronostico.grilla_total(None, uid)
    except FileNotFoundError:
        pytest.skip("faltan los datos procesados")
    if uid == "Total/empresas":  # cierre propio del segmento (config: serie.cierres_segmento)
        assert g.loc["2025-05-24", "abierto"] == 0
    origen = [d for d in g.index if d.dayofweek == 5][-3]
    g2 = g.copy()
    g2.loc[g2.index > origen, ["y", "y_modelo"]] *= 10
    f = lgbm.directo(ev.EXOG_CAL) if modelo == "lgbm_directo" else sarimax.modelo_calendario(ev.EXOG_CAL)
    pd.testing.assert_frame_equal(f(*ev.partir(g, origen)), f(*ev.partir(g2, origen)))


def test_coeficientes_sarimax_una_fila_por_variable_que_varia():
    """`sarimax_coeficientes.csv`: una fila por serie × variable de calendario que varía
    en el entrenamiento del último origen, y efecto % = (e^β − 1) × 100."""
    from vhp import pronostico
    from vhp.config import ruta
    from vhp.models.comun import columnas_variables
    f = ruta("tablas") / "sarimax_coeficientes.csv"
    if not f.exists():
        pytest.skip("falta correr python main.py backtest")
    c = pd.read_csv(f)
    cfg = pronostico.cargar_config()
    for uid in pronostico.SERIES:
        g = pronostico.grilla_total(cfg, uid)
        o = ev.origenes(g, cfg["pronostico"]["semanas_test"], cfg["pronostico"]["fin_test"])[-1]
        hist, _ = ev.partir(g, o)
        assert sorted(c.loc[c["serie"] == uid, "variable"]) == sorted(columnas_variables(hist, ev.EXOG_CAL))
    assert np.allclose(c["efecto_pct"], 100 * np.expm1(c["beta"]), atol=0.01)
    assert (c["efecto_ic_inf"] <= c["efecto_pct"]).all() and (c["efecto_pct"] <= c["efecto_ic_sup"]).all()


def test_puestos_y_peor_caso():
    """Puesto 1 = menor MASE en cada serie × ventana; peor caso = máximo % sobre el mejor."""
    from vhp.pronostico import tabla_peor_caso, tabla_puestos
    m = pd.DataFrame({
        "modelo": ["a", "b", "a", "b"], "MASE": [1.0, 1.1, 0.9, 0.8],
        "serie": ["Total", "Total", "Total", "Total"], "ventana": ["anterior", "anterior", "nueva", "nueva"],
        "periodo": ["p1", "p1", "p2", "p2"]})
    pu = tabla_puestos(m).set_index(["ventana", "modelo"])["puesto"]
    assert pu[("anterior", "a")] == 1 and pu[("nueva", "b")] == 1
    peor = tabla_peor_caso(m).set_index("modelo")
    assert round(peor.loc["a", "peor_pct_sobre_mejor"], 2) == 12.5  # 0,9 / 0,8 − 1
    assert peor.loc["a", "ventana_peor"] == "nueva"
    assert round(peor.loc["b", "peor_pct_sobre_mejor"], 2) == 10.0
    assert list(tabla_peor_caso(m)["modelo"]) == ["b", "a"]
