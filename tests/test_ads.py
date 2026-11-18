"""Tests de la fase 8: regresión y Granger sobre datos sintéticos."""
import numpy as np
import pandas as pd

from vhp import ads


def _sinteticos(n=120, semilla=42):
    """y depende de x con 1 semana de rezago; x autocorrelacionado."""
    rng = np.random.default_rng(semilla)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = 0.7 * x[t - 1] + rng.normal()
    y = np.r_[0.0, 0.8 * x[:-1]] + rng.normal(0, 0.5, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="W-MON")
    return pd.DataFrame({"y": y, "x": x}, index=idx)


def test_granger_un_rezago_detecta_la_direccion_correcta():
    d = _sinteticos()
    assert ads.granger(d, "y", "x").p_valor.iat[0] < 0.01
    assert ads.granger(d, "x", "y").p_valor.iat[0] > 0.01
    assert ads.granger(d, "y", "x").rezagos.iat[0] == ads.REZAGO_GRANGER == 1


def test_regresion_recupera_la_elasticidad():
    rng = np.random.default_rng(42)
    n = 200
    d = pd.DataFrame({"x": rng.normal(size=n), "verano": (np.arange(n) % 10 == 0).astype(float)})
    d["y"] = 1 + 0.5 * d["x"] - 0.3 * d["verano"] + rng.normal(0, 0.2, n)
    r = ads.regresion(d, "y", "x", "verano").set_index("termino")
    assert r.loc["x", "ic95_inf"] < 0.5 < r.loc["x", "ic95_sup"]
    assert r.loc["x", "p_valor"] < 0.01


def test_regresion_saca_el_control_constante():
    rng = np.random.default_rng(1)
    d = pd.DataFrame({"x": rng.normal(size=60), "verano": 0.0})
    d["y"] = 0.3 * d["x"] + rng.normal(0, 0.1, 60)
    r = ads.regresion(d, "y", "x", "verano")
    assert list(r["termino"]) == ["x"] and r["control"].iat[0].startswith("verano constante")
