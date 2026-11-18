"""Baselines: naive, naive estacional y media móvil estacional de 4 semanas.

- naive: repite el último día (sábado) para los 6 días.
- naive estacional: repite la semana anterior (mismo día de la semana).
- media móvil 4 semanas: promedio del mismo día de la semana en las últimas 4 semanas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from vhp.models.comun import salida

H = 6


def _naive(y: np.ndarray) -> np.ndarray:
    return np.repeat(y[-1], H)


def _naive_estacional(y: np.ndarray) -> np.ndarray:
    return y[-H:].copy()


def _media_movil_estacional(y: np.ndarray, semanas: int = 4) -> np.ndarray:
    w = y[-H * semanas:].reshape(semanas, H)
    return w.mean(axis=0)


REGLAS = {"naive": _naive, "naive_estacional": _naive_estacional, "media_movil_4sem": _media_movil_estacional}


def modelo(nombre: str):
    regla = REGLAS[nombre]

    def f(hist: pd.DataFrame, fut: pd.DataFrame) -> pd.DataFrame:
        return salida(fut.index, regla(hist["y_modelo"].to_numpy(float))[: len(fut)])

    return f
