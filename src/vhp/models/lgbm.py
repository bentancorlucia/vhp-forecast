"""LightGBM directo con lags, medias móviles y calendario (sin clima).

Los árboles no extrapolan la tendencia, así que todo se normaliza por el NIVEL
del origen: la media de los últimos 6 días (una semana) de y_modelo hasta el
origen inclusive. Objetivo y lags quedan como cocientes respecto de ese nivel.

Estrategia directa: un solo modelo para los 6 horizontes; cada fila de
entrenamiento es (origen, h) con los lags del origen, h y las variables de
calendario del día objetivo. Se usan todos los días de hist como orígenes
posibles; las filas cuyo día objetivo está cerrado no se usan.
Pérdida: error absoluto (objective="l1"), coherente con MAE/MASE.
Las mismas variables las usa el MLP (`rasgos`).
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from vhp.models.comun import SEMILLA, salida

H = 6
LAGS = 18  # tres semanas hábiles
PARAMS = dict(objective="l1", n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=20,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=SEMILLA,
              deterministic=True, force_row_wise=True, verbose=-1)


def _rasgos_lags(y: np.ndarray, o: int) -> tuple[dict, float]:
    """Lags y medias móviles en el origen o, normalizados por el nivel (media de y[o-5..o])."""
    nivel = y[o - H + 1: o + 1].mean()
    v = y[o - LAGS + 1: o + 1][::-1] / nivel  # v[0] = y[o]
    r = {f"lag{k}": v[k] for k in range(LAGS)}
    r["mm_sem_ant"] = y[o - 2 * H + 1: o - H + 1].mean() / nivel  # semana anterior (tendencia corta)
    r["mm_3sem"] = y[o - 3 * H + 1: o + 1].mean() / nivel
    return r, nivel


def _rasgos_objetivo(fila: pd.Series, exog: list[str], h: int) -> dict:
    return {"dow": fila["dia_semana"], **{c: fila[c] for c in exog}, "h": h}


def rasgos(hist: pd.DataFrame, fut: pd.DataFrame, exog: list[str]):
    """Tabla de entrenamiento y de pronóstico de la estrategia directa.

    Devuelve (X, y_rel, origen_fila, Xf, nivel_final): X e y_rel = y / nivel para
    cada (origen, h) con día objetivo abierto dentro de hist; `origen_fila` = posición
    del día objetivo (sirve para separar validación); Xf = las 6 filas de fut con
    los lags del último día de hist."""
    y, ab = hist["y_modelo"].to_numpy(float), hist["abierto"].to_numpy()
    filas, obj, pos = [], [], []
    for o in range(LAGS - 1, len(hist) - 1):
        base, nivel = _rasgos_lags(y, o)
        for h in range(1, H + 1):
            if o + h >= len(hist) or ab[o + h] == 0:
                continue
            filas.append({**base, **_rasgos_objetivo(hist.iloc[o + h], exog, h)})
            obj.append(y[o + h] / nivel)
            pos.append(o + h)
    X = pd.DataFrame(filas)
    base, nivel = _rasgos_lags(y, len(hist) - 1)
    Xf = pd.DataFrame([{**base, **_rasgos_objetivo(fut.iloc[i], exog, i + 1)} for i in range(len(fut))])[X.columns]
    return X, np.asarray(obj), np.asarray(pos), Xf, nivel


def directo(exog: list[str]):
    def f(hist: pd.DataFrame, fut: pd.DataFrame) -> pd.DataFrame:
        X, obj, _, Xf, nivel = rasgos(hist, fut, exog)
        m = lgb.LGBMRegressor(**PARAMS).fit(X, obj)
        return salida(fut.index, m.predict(Xf) * nivel)

    return f
