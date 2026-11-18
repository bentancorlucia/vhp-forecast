"""SARIMA (statsmodels SARIMAX, sin exógenas, período 6) sobre log(y_modelo).

Se modela el logaritmo porque la varianza crece con el nivel; el pronóstico
vuelve a la escala original con exp (exp de la media en log = mediana).

Órdenes: (p, 0, q)(P, 1, Q)[6] con constante. D = 1 (diferencia estacional de 6
días: la serie diferenciada así es estacionaria según el EDA) y d = 0. La
constante en la serie diferenciada es el crecimiento medio semana a semana.
p, q ∈ {0, 1, 2} y P, Q ∈ {0, 1}: 36 combinaciones, que se ajustan en el tramo
de entrenamiento de CADA origen; se queda la de menor AIC. Las combinaciones se
ajustan en paralelo (no cambia el resultado, solo el tiempo).
"""
from __future__ import annotations

import itertools
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from statsmodels.tsa.statespace.sarimax import SARIMAX

from vhp.models.comun import salida

PERIODO = 6
GRILLA = [((p, 0, q), (P, 1, Q, PERIODO)) for p, q, P, Q in itertools.product([0, 1, 2], [0, 1, 2], [0, 1], [0, 1])]


def _ajustar_uno(ly: np.ndarray, orden, estacional):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avisos de convergencia / no invertibilidad
        try:
            return SARIMAX(ly, order=orden, seasonal_order=estacional, trend="c").fit(disp=False)
        except (np.linalg.LinAlgError, ValueError):
            return None


def ajustar(hist: pd.DataFrame, n_jobs: int = -1):
    """Ajusta la grilla en log(y_modelo) y devuelve el resultado de menor AIC."""
    ly = np.log(hist["y_modelo"].to_numpy(float))
    res = Parallel(n_jobs=n_jobs)(delayed(_ajustar_uno)(ly, o, e) for o, e in GRILLA)
    validos = [r for r in res if r is not None and np.isfinite(r.aic)]
    return min(validos, key=lambda r: r.aic)


def especificacion(r) -> str:
    (p, d, q), (P, D, Q, s) = r.model.order, r.model.seasonal_order
    return f"({p},{d},{q})({P},{D},{Q})[{s}]"


def modelo():
    def f(hist: pd.DataFrame, fut: pd.DataFrame) -> pd.DataFrame:
        return salida(fut.index, np.exp(ajustar(hist).forecast(len(fut))))

    return f


def ajuste_final(hist: pd.DataFrame) -> tuple[pd.Series, str]:
    """Residuos dentro de la muestra (escala log) y la especificación elegida."""
    r = ajustar(hist)
    resid = pd.Series(r.resid, index=hist.index)
    resid.iloc[: 2 * PERIODO] = np.nan  # arranque del filtro (diferencia estacional): residuos sin sentido
    return resid, especificacion(r)
