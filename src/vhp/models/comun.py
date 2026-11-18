"""Piezas comunes a todos los modelos.

Interfaz de un modelo: f(hist, fut) -> DataFrame con índice = fut.index y
columnas q0.1, q0.5, q0.9. Los modelos solo dan el pronóstico puntual (q0.5);
q0.1 y q0.9 salen en NaN y el intervalo 80 % lo arma `evaluate.backtest` con
los errores del propio modelo en las 12 semanas previas al origen (igual para
todos los modelos).
- hist: grilla hasta el origen (incluye y, y_modelo, abierto, calendario, clima).
- fut: las 6 filas siguientes, sin y ni y_modelo (calendario y clima sí).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COLS_Q = ["q0.1", "q0.5", "q0.9"]
SEMILLA = 42


def salida(index, punto) -> pd.DataFrame:
    """Arma la salida con el pronóstico puntual (sin negativos) y el intervalo vacío."""
    p = np.clip(np.asarray(punto, dtype=float), 0, None)
    return pd.DataFrame({"q0.1": np.nan, "q0.5": p, "q0.9": np.nan}, index=index)


def columnas_variables(hist: pd.DataFrame, columnas: list[str]) -> list[str]:
    """Columnas exógenas que varían en hist (las constantes rompen la regresión)."""
    return [c for c in columnas if hist[c].nunique() > 1]
