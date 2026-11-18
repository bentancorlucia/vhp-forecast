"""Tests de la fase 9: el colchón usa solo semanas previas, el plan crece con p y las cuentas cierran."""
import numpy as np
import pandas as pd

from vhp import decision as dc


def _sem(n_origenes=20, semilla=0):
    """Semanas sintéticas: 2 categorías de tamaños distintos en un segmento."""
    rng = np.random.default_rng(semilla)
    filas = []
    for o in pd.date_range("2026-01-03", periods=n_origenes, freq="7D"):
        for c, nivel in (("a", 100.0), ("b", 10.0)):
            filas.append({"origen": o, "segmento": "s", "categoria": c, "lgbm": nivel,
                          "naive_estacional": nivel, "y": nivel * rng.uniform(0.5, 1.5)})
    return pd.DataFrame(filas)


def test_colchon_usa_solo_las_12_semanas_previas():
    sem = _sem()
    test = [pd.Timestamp(x) for x in sem["origen"].unique()[-3:]]
    pl = dc.planes(sem, test, ["lgbm"], [80])
    for o in test:
        prev = dc.semanas_previas(sem, o, 12)
        assert prev["origen"].max() <= o - pd.Timedelta(days=7)  # la semana previa ya terminó
        assert prev["origen"].nunique() == 12
        assert (pl.loc[pl["origen"] == o, "n_errores"] == 12 * 2).all()  # se juntan las categorías
    # si la semana de test tiene un outlier, el plan de esa semana no cambia
    sem2 = sem.copy()
    sem2.loc[sem2["origen"] == test[-1], "y"] = 1e6
    pl2 = dc.planes(sem2, test, ["lgbm"], [80])
    assert np.allclose(pl.loc[pl["origen"] == test[-1], "plan"], pl2.loc[pl2["origen"] == test[-1], "plan"])


def test_factor_es_percentil_del_cociente():
    prev = pd.DataFrame({"segmento": "s", "lgbm": 10.0, "y": np.arange(1.0, 22.0)})  # r = 0,1 … 2,1
    f = dc.factores(prev, "lgbm", [50, 90]).iloc[0]
    assert np.isclose(f[50], np.percentile(prev["y"] / 10, 50))
    assert np.isclose(f[90], np.percentile(prev["y"] / 10, 90))


def test_plan_monotono_en_p():
    sem = _sem()
    pl = dc.planes(sem, list(sem["origen"].unique()[-2:]), ["lgbm"], [40, 60, 80, 95])
    ancho = pl.pivot_table(index=["origen", "categoria"], columns="p", values="plan")
    assert (ancho.diff(axis=1).iloc[:, 1:] >= 0).all().all()


def test_semanal_suma_los_dias():
    pred = pd.DataFrame({"origen": pd.Timestamp("2026-01-03"), "segmento": "s", "categoria": ["a"] * 6 + ["b"] * 6,
                         "lgbm": 1.0, "naive_estacional": 2.0, "y": 3.0})
    sem = dc.semanal(pred)
    assert (sem["lgbm"] == 6).all() and (sem["naive_estacional"] == 12).all() and (sem["y"] == 18).all()


def test_simular_cuentas_y_eleccion():
    pl = pd.DataFrame({"metodo": "m", "p": 50, "y": [10.0, 10.0], "plan": [12.0, 7.0]})
    r = dc.simular(pl, cf=150, cs=200).iloc[0]
    assert r["sobrante_pct"] == 10 and r["faltante_pct"] == 15 and r["cobertura"] == 0.5
    assert np.isclose(r["costo_por_vianda"], (200 * 2 + 150 * 3) / 20)
    curva = pd.DataFrame({"metodo": "lgbm", "p": [40, 45, 50], "costo_por_vianda": [5.0, 3.0, 3.0]})
    assert dc.elegir_p(curva) == 45  # mínimo; si empatan, el p más chico


def test_costos_ponderados_por_xl():
    pl = pd.DataFrame({"metodo": "m", "p": 50, "y": [10.0, 10.0], "plan": [12.0, 7.0], "prop_xl": [0.5, 0.5]})
    r = dc.simular(pl, cf=150, cs=200, cs_xl=260, cf_xl=155).iloc[0]
    # sobrante 2 × (200·0,5 + 260·0,5) = 460; faltante 3 × (150·0,5 + 155·0,5) = 457,5
    assert np.isclose(r["costo_por_vianda"], (2 * 230 + 3 * 152.5) / 20)
    # sin cs_xl/cf_xl se ignora prop_xl (costos fijos de antes)
    assert np.isclose(dc.simular(pl, cf=150, cs=200).iloc[0]["costo_por_vianda"], (200 * 2 + 150 * 3) / 20)


def test_prop_xl_usa_solo_semanas_previas():
    xl = pd.DataFrame({"semana_ini": pd.date_range("2026-01-05", periods=20, freq="7D"), "segmento": "s",
                       "prop_xl": np.arange(20) / 100})
    o = pd.Timestamp("2026-05-16")  # sábado; su semana empieza el lunes 11/05 (índice 18)
    x = dc.prop_xl_previa(xl, "s", o, 12)
    assert np.isclose(x, np.arange(7, 19).mean() / 100)
