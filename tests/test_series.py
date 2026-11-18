"""Tests de la fase 3: categorías y jerarquía."""
import numpy as np
import pandas as pd
import pytest

from vhp import series
from vhp.config import ruta

LINEAS = ruta("interim") / "lineas.parquet"


def test_categorias_yaml_sin_platos_repetidos():
    mapa, _ = series.cargar_categorias()
    assert len(set(mapa.values())) == 7


def test_plato_base_quita_xl():
    assert series.plato_base(pd.Series(["Bife a la portuguesa [XL]"])).iat[0] == "Bife a la portuguesa"


@pytest.mark.skipif(not LINEAS.exists(), reason="faltan datos privados")
def test_todas_las_viandas_tienen_categoria():
    l = pd.read_parquet(LINEAS, columns=["tipo_producto", "producto"])
    mapa, _ = series.cargar_categorias()
    out = series.asignar_categoria(l, mapa)
    assert out["categoria"].notna().all()


def test_jerarquia_suma_en_todos_los_niveles():
    idx = pd.DatetimeIndex(pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03"]))
    d = pd.DataFrame({
        "fecha": ["2026-06-01", "2026-06-01", "2026-06-02", "2026-06-01"],
        "segmento": ["particulares", "empresas", "particulares", "particulares"],
        "tipo_producto": ["Vianda", "Vianda", "Vianda", "Postre"],
        "categoria": ["pollo", "pastas", "pollo", "postre"],
        "unidades": [3, 2, 5, 9],
    })
    Y, S, tags = series.jerarquia(d, idx)
    w = Y.pivot(index="ds", columns="unique_id", values="y")
    assert len(w) == 3 and w.loc["2026-06-03"].sum() == 0  # día hábil sin ventas = cero
    assert w["Total"].tolist() == [5, 5, 0]                # el postre no entra
    hojas = tags["total/segmento/categoria"]
    assert np.allclose(w[S.index].to_numpy(), w[hojas].to_numpy() @ S.T.to_numpy())
    for s in tags["total/segmento"]:
        assert (w[s] == w[[h for h in hojas if h.startswith(s + "/")]].sum(axis=1)).all()


def test_jerarquia_rechaza_ventas_fuera_del_indice():
    d = pd.DataFrame({"fecha": ["2026-06-07"], "segmento": ["empresas"], "tipo_producto": ["Vianda"],
                      "categoria": ["pollo"], "unidades": [1]})
    with pytest.raises(ValueError):
        series.jerarquia(d, pd.DatetimeIndex(["2026-06-08"]))


def test_cierre_de_un_segmento_saca_el_dia_solo_de_ese_segmento():
    idx = pd.DatetimeIndex(pd.to_datetime(["2026-06-01", "2026-06-02"]))
    d = pd.DataFrame({"fecha": ["2026-06-01", "2026-06-02", "2026-06-01"], "segmento": ["particulares"] * 2 + ["empresas"],
                      "tipo_producto": ["Vianda"] * 3, "categoria": ["pollo"] * 3, "unidades": [3, 4, 2]})
    Y, _, _ = series.jerarquia(d, idx, {"empresas": ["2026-06-02"]})
    emp = Y[Y.unique_id.str.startswith("Total/empresas")]
    assert pd.Timestamp("2026-06-02") not in set(emp.ds)
    assert Y[(Y.unique_id == "Total") & (Y.ds == "2026-06-02")].y.iat[0] == 4
    with pytest.raises(ValueError):  # no se puede marcar cierre un día con ventas
        series.jerarquia(d, idx, {"empresas": ["2026-06-01"]})


def test_fin_segmento_corta_segmento_y_total():
    from vhp import series
    idx = pd.DatetimeIndex(pd.date_range("2026-08-27", periods=6, freq="D"))
    idx = idx[idx.dayofweek <= 5]
    filas = [{"fecha": d, "segmento": s, "tipo_producto": "Vianda", "categoria": "pollo", "unidades": 5}
             for d in idx for s in ["particulares", "empresas"] if not (s == "empresas" and d > pd.Timestamp("2026-08-29"))]
    Y, _, _ = series.jerarquia(pd.DataFrame(filas), idx, fin_segmento={"empresas": "2026-08-29"})
    ultimo = Y.groupby("unique_id")["ds"].max()
    assert ultimo["Total/empresas"] == pd.Timestamp("2026-08-29") and ultimo["Total"] == pd.Timestamp("2026-08-29")
    assert ultimo["Total/particulares"] == idx.max()
    assert not ((Y["unique_id"] == "Total/empresas/pollo") & (Y["ds"] > "2026-08-29")).any()
