"""Grilla de modelado, walk-forward, métricas, Diebold-Mariano y Ljung-Box.

Grilla de modelado: TODOS los lunes a sábado (posición t = 0, 1, 2…), para que
el período estacional 6 quede alineado con el día de la semana aunque haya
feriados no laborables en el medio. Los días cerrados se marcan `abierto = 0` y,
SOLO para la mecánica de los modelos, se rellenan con el valor del mismo día de
la semana anterior (`y_modelo`, usa solo el pasado). Las métricas se calculan
únicamente sobre días abiertos: los cerrados no existen para la evaluación.

Walk-forward: un origen por semana (cada sábado), ventana expansiva; con datos
hasta el sábado se pronostican los días hábiles de lunes a sábado siguientes.
Cada modelo recibe `hist` (filas ≤ origen) y `fut` (las 6 filas siguientes SIN
`y` ni `y_modelo`), así que no puede ver el futuro.

Intervalo 80 % (igual para todos los modelos): el backtest corre además los 12
sábados ANTERIORES al primer origen de test. Para cada origen o, se toman los
errores relativos r = y / ŷ del mismo modelo en los 12 orígenes previos a o
(o − 12 … o − 1 semanas; la semana pronosticada desde o − 1 termina justo en o,
así que todos esos errores ya se conocen en o). Intervalo = ŷ × [p10(r), p90(r)].
Se usa el cociente y no la diferencia porque la serie crece y el error escala
con el nivel. En el primer origen de test los 12 previos son todos anteriores
al test; después la ventana se desliza e incluye semanas de test ya cerradas,
como pasaría en producción.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox

from vhp.calendar import tabla_feriados, variables_calendario
from vhp.models.comun import COLS_Q

EXOG_CAL = ["feriado_laborable", "vispera_cierre", "post_cierre", "turismo", "verano"]
EXOG_CLIMA = ["temperature_2m_max", "precipitation_sum"]
H = 6  # lunes a sábado

Modelo = Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame]


# ---------------------------------------------------------------------- grilla
def armar_grilla(y: pd.Series, clima: pd.DataFrame, meses_verano=(1,), cierres_extra=None) -> pd.DataFrame:
    """Grilla lunes-a-sábado con y, y_modelo, abierto, calendario y clima.

    `y`: serie en días hábiles (índice fecha). `cierres_extra`: fechas cerradas
    solo para esta serie (ej.: empresas el 24/05/2025).
    """
    y = y.dropna()
    dias = pd.date_range(y.index.min(), y.index.max(), freq="D")
    dias = dias[dias.dayofweek <= 5]
    fer = tabla_feriados(dias.min(), dias.max())
    g = variables_calendario(dias, fer, tuple(meses_verano)).set_index("fecha")
    cerrados = set(fer.loc[fer["tipo"] == "no_laborable", "fecha"]) | set(pd.to_datetime(cierres_extra or []))
    g["abierto"] = (~g.index.isin(cerrados)).astype(int)
    g["y"] = y.reindex(g.index)
    faltan = g.index[(g["abierto"] == 1) & g["y"].isna()]
    if len(faltan):
        raise ValueError(f"Días abiertos sin dato: {list(faltan[:5])}")
    if g.loc[g["abierto"] == 0, "y"].notna().any():
        raise ValueError("Hay ventas en días marcados como cerrados")
    ym = g["y"].to_numpy(dtype=float).copy()
    for i in np.flatnonzero(np.isnan(ym)):  # mismo día de la semana anterior (solo pasado)
        ym[i] = ym[i - H] if i >= H else np.nan
    g["y_modelo"] = pd.Series(ym, index=g.index).bfill()
    g["t"] = np.arange(len(g))
    cl = clima.set_index("fecha")[EXOG_CLIMA] if "fecha" in clima else clima[EXOG_CLIMA]
    g = g.join(cl, how="left")
    if g[EXOG_CLIMA].isna().any().any():
        raise ValueError("Falta clima para algún día de la grilla")
    return g


# ------------------------------------------------------------------ walk-forward
def origenes(grilla: pd.DataFrame, n_semanas: int, fin_test) -> list[pd.Timestamp]:
    """Los últimos `n_semanas` sábados cuya semana siguiente termina a más tardar en `fin_test`."""
    fin_test = pd.Timestamp(fin_test)
    sab = [d for d in grilla.index if d.dayofweek == 5 and d + pd.Timedelta(H + 1, unit="D") <= fin_test
           and d + pd.Timedelta(H + 1, unit="D") <= grilla.index.max()]
    return sab[-n_semanas:]


def partir(grilla: pd.DataFrame, origen) -> tuple[pd.DataFrame, pd.DataFrame]:
    """hist = filas ≤ origen; fut = las 6 filas siguientes, sin y ni y_modelo."""
    origen = pd.Timestamp(origen)
    hist = grilla.loc[grilla.index <= origen].copy()
    fut = grilla.loc[grilla.index > origen].iloc[:H].drop(columns=["y", "y_modelo"]).copy()
    return hist, fut


def escala_mase(hist: pd.DataFrame) -> float:
    """MAE del naive estacional (mismo día de la semana anterior) dentro de hist,
    solo en pares de días abiertos."""
    y = hist["y"].to_numpy(dtype=float)
    e = np.abs(y[H:] - y[:-H])
    return float(np.nanmean(e))


def origenes_previos(grilla: pd.DataFrame, primer_origen, n_semanas: int) -> list[pd.Timestamp]:
    """Los `n_semanas` sábados anteriores a `primer_origen` (para armar el intervalo)."""
    o = pd.Timestamp(primer_origen)
    return [o - pd.Timedelta(7 * k, unit="D") for k in range(n_semanas, 0, -1)
            if o - pd.Timedelta(7 * k, unit="D") in grilla.index]


def _correr(grilla, modelos, origs, verbose):
    filas = []
    for o in origs:
        hist, fut = partir(grilla, o)
        escala = escala_mase(hist)
        real = grilla.loc[fut.index, "y"]
        for nombre, f in modelos.items():
            p = f(hist, fut)
            assert list(p.index) == list(fut.index) and set(COLS_Q) <= set(p.columns), nombre
            df = p[COLS_Q].copy()
            df["modelo"], df["origen"], df["h"] = nombre, pd.Timestamp(o), np.arange(1, len(fut) + 1)
            df["y"], df["abierto"], df["escala_mase"] = real, fut["abierto"], escala
            filas.append(df[fut["abierto"] == 1])
        if verbose:
            print(f"  origen {pd.Timestamp(o):%d/%m/%Y} listo", flush=True)
    out = pd.concat(filas).rename_axis("fecha").reset_index()
    return out[["modelo", "origen", "fecha", "h", "y", *COLS_Q, "escala_mase"]]


def intervalos(res: pd.DataFrame, origs: list, semanas: int = 12) -> pd.DataFrame:
    """Pone q0.1/q0.9 en las filas de `origs` con los percentiles 10 y 90 de
    y / ŷ del mismo modelo en los `semanas` orígenes previos (ver docstring del módulo)."""
    out = []
    for o in origs:
        o = pd.Timestamp(o)
        previos = res[(res["origen"] <= o - pd.Timedelta(7, unit="D"))
                      & (res["origen"] >= o - pd.Timedelta(7 * semanas, unit="D"))]
        actual = res[res["origen"] == o].copy()
        for m, d in previos.groupby("modelo"):
            d = d[d["q0.5"] > 0]
            lo, hi = np.percentile(d["y"] / d["q0.5"], [10, 90])
            fil = actual["modelo"] == m
            actual.loc[fil, "q0.1"] = actual.loc[fil, "q0.5"] * lo
            actual.loc[fil, "q0.9"] = actual.loc[fil, "q0.5"] * hi
        out.append(actual)
    return pd.concat(out, ignore_index=True)


def backtest(grilla: pd.DataFrame, modelos: dict[str, Modelo], origs: list, semanas_intervalo: int = 12,
             verbose: bool = True) -> pd.DataFrame:
    """Corre cada modelo en los orígenes de test y en los `semanas_intervalo` sábados
    anteriores (solo para el intervalo). Devuelve una fila por modelo × día abierto
    pronosticado de los orígenes de test, con el intervalo 80 % armado con los errores previos."""
    previos = origenes_previos(grilla, origs[0], semanas_intervalo)
    res = _correr(grilla, modelos, [*previos, *origs], verbose)
    return intervalos(res, origs, semanas_intervalo)


# ---------------------------------------------------------------------- métricas
def metricas(res: pd.DataFrame) -> pd.DataFrame:
    """MAE, MASE, WAPE y cobertura del intervalo 80 %.

    MASE: promedio de |e| / escala del origen (MAE del naive estacional en el
    train de ese origen). WAPE = Σ|e| / Σy. No se usa MAPE.
    """
    filas = []
    for m, d in res.groupby("modelo", sort=False):
        e = d["y"] - d["q0.5"]
        filas.append({"modelo": m, "n": len(d), "MAE": e.abs().mean(),
                      "MASE": (e.abs() / d["escala_mase"]).mean(), "WAPE": e.abs().sum() / d["y"].sum(),
                      "cobertura_80": ((d["y"] >= d["q0.1"]) & (d["y"] <= d["q0.9"])).mean()})
    return pd.DataFrame(filas).sort_values("MASE").reset_index(drop=True)


def diebold_mariano(e1: np.ndarray, e2: np.ndarray, h: int = H, perdida: str = "abs") -> tuple[float, float]:
    """Test de Diebold-Mariano con la corrección de Harvey, Leybourne y Newbold (1997).

    d_t = L(e1) − L(e2); varianza de largo plazo con autocovarianzas hasta h − 1.
    Estadístico negativo = el modelo 1 tiene menor pérdida. p-valor bilateral (t con n − 1 gl).
    """
    L = np.abs if perdida == "abs" else np.square
    d = L(np.asarray(e1)) - L(np.asarray(e2))
    n = len(d)
    dc = d - d.mean()
    gam = [np.sum(dc[k:] * dc[:n - k]) / n for k in range(h)]
    var = (gam[0] + 2 * sum(gam[1:])) / n
    if var <= 0:
        return np.nan, np.nan
    dm = d.mean() / np.sqrt(var)
    dm *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return float(dm), float(2 * stats.t.sf(abs(dm), df=n - 1))


def tabla_dm(res: pd.DataFrame, modelos: list[str]) -> pd.DataFrame:
    """DM (pérdida absoluta) entre cada par de `modelos`, sobre los mismos días."""
    ancho = res.pivot_table(index="fecha", columns="modelo", values="q0.5")
    y = res.drop_duplicates("fecha").set_index("fecha")["y"].reindex(ancho.index)
    filas = []
    for i, a in enumerate(modelos):
        for b in modelos[i + 1:]:
            dm, p = diebold_mariano(y - ancho[a], y - ancho[b])
            filas.append({"modelo_1": a, "modelo_2": b, "DM": dm, "p_valor": p,
                          "mejor": a if dm < 0 else b})
    return pd.DataFrame(filas)


def ljung_box(resid: pd.Series, lags=(6, 12)) -> pd.DataFrame:
    """Ljung-Box sobre residuos (H0: sin autocorrelación hasta el rezago)."""
    r = pd.Series(resid).dropna()
    return acorr_ljungbox(r, lags=list(lags)).reset_index(names="rezago")
