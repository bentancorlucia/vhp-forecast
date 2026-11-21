"""SARIMA y SARIMAX (statsmodels, período 6) sobre log(y_modelo).

- `modelo()`: SARIMA puro, sin exógenas (la comparación que muestra cuánto agrega el calendario).
- `modelo_calendario(cols)`: SARIMAX = regresión sobre las variables de calendario
  (se conocen de antemano) con errores SARIMA. Es el modelo del proyecto desde el
  21/11/2026: cada β se lee como un efecto, (e^β − 1) × 100 %.

Se modela el logaritmo porque la varianza crece con el nivel (los días con 0, que solo
hay en empresas, entran como 1 para poder tomar log); el pronóstico
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

from vhp.models.comun import columnas_variables, salida

PERIODO = 6
GRILLA = [((p, 0, q), (P, 1, Q, PERIODO)) for p, q, P, Q in itertools.product([0, 1, 2], [0, 1, 2], [0, 1], [0, 1])]


def _ajustar_uno(ly: np.ndarray, orden, estacional, exog=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avisos de convergencia / no invertibilidad
        try:
            return SARIMAX(ly, exog=exog, order=orden, seasonal_order=estacional, trend="c").fit(disp=False)
        except (np.linalg.LinAlgError, ValueError):
            return None


def ajustar(hist: pd.DataFrame, n_jobs: int = -1, exog: list[str] | None = None):
    """Ajusta la grilla en log(y_modelo) y devuelve el resultado de menor AIC.
    Con `exog` (columnas de hist) queda una regresión con errores SARIMA."""
    # piso de 1 solo para los días con 0 (3 sábados de empresas en 2025); Total y particulares no tienen ceros
    ly = np.log(np.maximum(hist["y_modelo"].to_numpy(float), 1.0))
    X = hist[exog].to_numpy(float) if exog else None
    res = Parallel(n_jobs=n_jobs)(delayed(_ajustar_uno)(ly, o, e, X) for o, e in GRILLA)
    validos = [r for r in res if r is not None and np.isfinite(r.aic)]
    return min(validos, key=lambda r: r.aic)


def especificacion(r) -> str:
    (p, d, q), (P, D, Q, s) = r.model.order, r.model.seasonal_order
    return f"({p},{d},{q})({P},{D},{Q})[{s}]"


def modelo():
    def f(hist: pd.DataFrame, fut: pd.DataFrame) -> pd.DataFrame:
        return salida(fut.index, np.exp(ajustar(hist).forecast(len(fut))))

    return f


def modelo_calendario(columnas: list[str]):
    """SARIMAX: el mismo SARIMA sobre log(y), misma grilla y AIC, más como exógenas
    las variables de calendario que varían en hist. `fut` ya trae el calendario
    (se conoce el sábado), así que no mira el futuro."""
    def f(hist: pd.DataFrame, fut: pd.DataFrame) -> pd.DataFrame:
        cols = columnas_variables(hist, columnas)
        r = ajustar(hist, exog=cols or None)
        X = fut[cols].to_numpy(float) if cols else None
        return salida(fut.index, np.exp(r.forecast(len(fut), exog=X)))

    return f


def ajuste_final(hist: pd.DataFrame, exog: list[str] | None = None) -> tuple[pd.Series, str]:
    """Residuos dentro de la muestra (escala log) y la especificación elegida.
    Con `exog`, el SARIMAX (solo las columnas que varían en hist)."""
    cols = columnas_variables(hist, exog) if exog else None
    r = ajustar(hist, exog=cols or None)
    resid = pd.Series(r.resid, index=hist.index)
    resid.iloc[: 2 * PERIODO] = np.nan  # arranque del filtro (diferencia estacional): residuos sin sentido
    return resid, especificacion(r)


def coeficientes(hist: pd.DataFrame, exog: list[str]) -> pd.DataFrame:
    """Coeficientes del SARIMAX ajustado en hist: una fila por variable de calendario
    que varía en hist, con β, IC 95 %, efecto % = (e^β − 1) × 100 con su IC
    (transformando los extremos del IC de β), p-valor y orden elegido por AIC."""
    cols = columnas_variables(hist, exog)
    r = ajustar(hist, exog=cols)
    nombres = list(r.model.exog_names)  # statsmodels: x1, x2… si exog es un array
    params, ic, pv = (pd.Series(np.asarray(r.params), index=r.model.param_names),
                      pd.DataFrame(np.asarray(r.conf_int(alpha=0.05)), index=r.model.param_names),
                      pd.Series(np.asarray(r.pvalues), index=r.model.param_names))
    filas = []
    for c, k in zip(cols, nombres):
        b, lo, hi = params[k], ic.loc[k, 0], ic.loc[k, 1]
        filas.append({"variable": c, "beta": b, "beta_ic_inf": lo, "beta_ic_sup": hi,
                      "efecto_pct": 100 * np.expm1(b), "efecto_ic_inf": 100 * np.expm1(lo),
                      "efecto_ic_sup": 100 * np.expm1(hi), "p_valor": pv[k]})
    return pd.DataFrame(filas).assign(orden=especificacion(r), aic=r.aic)
