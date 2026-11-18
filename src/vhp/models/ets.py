"""ETS / Holt-Winters (statsmodels ExponentialSmoothing, período 6) sobre y_modelo.

En cada origen se ajustan cuatro variantes con los datos de entrenamiento y se
queda la de menor AIC:
- estacionalidad aditiva o multiplicativa (período 6 = una semana hábil);
- sin tendencia o con tendencia aditiva amortiguada (la amortiguación evita que
  la tendencia se extrapole sin freno en el horizonte de 6 días).
El pronóstico puntual es la media del modelo elegido.
"""
from __future__ import annotations

import itertools
import warnings

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from vhp.models.comun import salida

PERIODO = 6
VARIANTES = list(itertools.product([None, "add"], ["add", "mul"]))  # (tendencia, estacionalidad)


def ajustar(hist: pd.DataFrame):
    """Ajusta las cuatro variantes y devuelve el resultado de menor AIC."""
    y = hist["y_modelo"].to_numpy(float)
    mejor = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avisos de convergencia del optimizador
        for tendencia, estacion in VARIANTES:
            if estacion == "mul" and (y <= 0).any():
                continue  # la estacionalidad multiplicativa necesita valores positivos
            r = ExponentialSmoothing(y, trend=tendencia, damped_trend=tendencia is not None, seasonal=estacion,
                                     seasonal_periods=PERIODO).fit()
            if mejor is None or r.aic < mejor.aic:
                mejor = r
    return mejor


def modelo():
    def f(hist: pd.DataFrame, fut: pd.DataFrame) -> pd.DataFrame:
        return salida(fut.index, ajustar(hist).forecast(len(fut)))

    return f


def residuos(hist: pd.DataFrame) -> pd.Series:
    """Residuos a un paso dentro de la muestra (para Ljung-Box)."""
    return pd.Series(ajustar(hist).resid, index=hist.index)
