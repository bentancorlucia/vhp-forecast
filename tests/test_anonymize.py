"""Tests de la fase 2: data/processed/ no tiene datos personales ni montos reales."""
import re

import numpy as np

import pandas as pd
import pytest

from vhp import anonymize
from vhp.config import ruta

PROCESADOS = sorted(ruta("processed").glob("*.csv"))
LINEAS = ruta("interim") / "lineas.parquet"
hay_datos = pytest.mark.skipif(not LINEAS.exists() or not PROCESADOS, reason="faltan datos (correr main.py prepare anonymize)")


def test_hash_es_estable_y_depende_de_la_sal():
    s = pd.Series(["000000001", None])
    h1, h2 = anonymize.hashear(s, "a"), anonymize.hashear(s, "b")
    assert h1.iat[0] == anonymize.hashear(s, "a").iat[0]
    assert h1.iat[0] != h2.iat[0] and len(h1.iat[0]) == 64
    assert pd.isna(h1.iat[1])


def test_indice_base_100():
    df = pd.DataFrame({"x": [50.0, 150.0]})
    assert anonymize.indice_base_100(df, ["x"], 100.0)["x"].tolist() == [50.0, 150.0]


@hay_datos
def test_processed_sin_columnas_prohibidas():
    for p in PROCESADOS:
        cols = set(pd.read_csv(p, nrows=1).columns)
        assert not cols & anonymize.COLUMNAS_PROHIBIDAS, p.name


@hay_datos
def test_processed_sin_telefonos_ni_empresas():
    l = pd.read_parquet(LINEAS, columns=["telefono", "empresa"])
    texto = "".join(p.read_text() for p in PROCESADOS)
    assert not re.search(r"\d{8,}", texto)
    empresas = [e for e in l["empresa"].dropna().unique() if len(e) > 3]
    assert not [e for e in empresas if e in texto]


@hay_datos
def test_montos_de_meta_no_son_reales():
    real = pd.read_csv(ruta("meta_ads"))
    pub = pd.read_csv(ruta("processed") / "meta_ads_semanal_indice.csv")
    for c in [c for c in real.columns if c.startswith("gasto_")]:
        r, p = real[c].dropna(), pub[c].dropna()
        assert not (r.values == p.values).any(), c


def test_mayor_resto_conserva_total_y_cada_celda():
    x = pd.Series([1, 1, 1, 2, 7, 1])
    out = anonymize.escalar_conservando_total(x, 0.73)
    assert out.sum() == round(0.73 * x.sum())
    assert ((out - 0.73 * x).abs() < 1).all()


@hay_datos
def test_unidades_estan_escaladas():
    """Totales diarios por segmento × tipo = round(K × real), a ±0,5."""
    _, k = anonymize.secretos()
    l = pd.read_parquet(LINEAS, columns=["fecha_entrega", "segmento", "tipo_producto", "cantidad"])
    d = pd.read_csv(ruta("processed") / "ventas_diarias.csv", parse_dates=["fecha"])
    real = l.groupby(["fecha_entrega", "segmento", "tipo_producto"])["cantidad"].sum() * k
    pub = d.groupby(["fecha", "segmento", "tipo_producto"])["unidades"].sum()
    assert ((pub.to_numpy() - real.to_numpy()) <= 0.5 + 1e-9).all()
    assert ((pub.to_numpy() - real.to_numpy()) >= -0.5 - 1e-9).all()


def test_xl_semanal_es_proporcion():
    from vhp import anonymize as an
    lineas = pd.DataFrame({"fecha_entrega": pd.to_datetime(["2026-11-02", "2026-11-03", "2026-11-03"]),
                           "segmento": "particulares", "tipo_producto": "Vianda", "cantidad": [3, 1, 4],
                           "es_xl": [False, True, False]})
    x = an.xl_semanal(lineas)
    assert len(x) == 1 and np.isclose(x["prop_xl"].iat[0], 1 / 8)
