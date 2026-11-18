"""Modelos del mix: participación de cada categoría en las viandas de un segmento.

Interfaz de un modelo de participaciones: f(U, X, fut) -> DataFrame
(índice = fut.index, columnas = categorías, filas que suman 1).
- U: unidades por categoría en los días de hist (filas = grilla lunes a sábado
  hasta el origen; NaN en días cerrados).
- X: calendario y clima de esas mismas filas (la grilla del segmento).
- fut: calendario y clima de los 6 días a pronosticar (sin ventas).

Modelos:
- media_4sem: participación de las últimas 4 semanas, mismo día de la semana
  (cociente de sumas: Σ unidades de la categoría / Σ unidades; más estable que
  promediar participaciones diarias y no se rompe con días de 0 ventas).
- multinomial: regresión logística multinomial (softmax) ponderada por
  unidades, con día de la semana, verano y el mix reciente (log de la
  participación de los 24 días hábiles anteriores) y, en la variante con
  clima, temperatura máxima y precipitación.
El mix reciente entra como variable porque el menú cambia con el tiempo; así el
modelo aprende cuánto se aparta el día del mix reciente según el clima.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from vhp.models.comun import SEMILLA

H = 6
VENTANA = 4 * H  # 4 semanas de lunes a sábado
CLIMA = ["temperature_2m_max", "precipitation_sum"]


def participaciones(U: pd.DataFrame) -> pd.DataFrame:
    """Participación de cada categoría por fila (NaN si la fila suma 0)."""
    tot = U.sum(axis=1)
    return U.div(tot.where(tot > 0), axis=0)


def _cociente(U: pd.DataFrame) -> np.ndarray:
    s = U.sum(axis=0).to_numpy(float)
    return s / s.sum() if s.sum() > 0 else np.full(len(s), 1 / len(s))


# ---------------------------------------------------------------- baseline
def media_4sem(U: pd.DataFrame, X: pd.DataFrame, fut: pd.DataFrame) -> pd.DataFrame:
    """Participación de las últimas 4 semanas, mismo día de la semana."""
    ult = U.iloc[-VENTANA:]
    dow = X["dia_semana"].iloc[-VENTANA:]
    filas = []
    for d in fut["dia_semana"]:
        mismo = ult[(dow == d).to_numpy()].dropna()
        filas.append(_cociente(mismo) if mismo.to_numpy().sum() > 0 else _cociente(ult.dropna()))
    return pd.DataFrame(filas, index=fut.index, columns=U.columns)


# ----------------------------------------------------------- variables
def mix_reciente(U: pd.DataFrame) -> pd.DataFrame:
    """log de la participación en las VENTANA filas anteriores (sin incluir la fila).

    Usa solo el pasado: fila t ← filas t−24 … t−1. Suavizado +0,5 por categoría
    para que el log no explote con ceros."""
    s = U.fillna(0).rolling(VENTANA, min_periods=VENTANA).sum().shift(1)
    s = s + 0.5
    return np.log(s.div(s.sum(axis=1), axis=0)).add_prefix("logmix_")


def _rasgos(X: pd.DataFrame, reciente: pd.DataFrame, clima: bool) -> pd.DataFrame:
    r = pd.get_dummies(X["dia_semana"].astype(int), prefix="dow").reindex(
        columns=[f"dow_{i}" for i in range(H)], fill_value=0).astype(float)
    r["verano"] = X["verano"].to_numpy(float)
    if clima:
        for c in CLIMA:
            r[c] = X[c].to_numpy(float)
    return pd.concat([r, reciente.set_axis(r.index)], axis=1)


def _largo(F: pd.DataFrame, U: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Formato largo para un clasificador: una fila por día × categoría, peso = unidades."""
    cats = list(U.columns)
    Xl = np.repeat(F.to_numpy(float), len(cats), axis=0)
    yl = np.tile(np.arange(len(cats)), len(F))
    wl = U.to_numpy(float).ravel()
    ok = wl > 0
    return Xl[ok], yl[ok], wl[ok]


def _entrenamiento(U: pd.DataFrame, X: pd.DataFrame, clima: bool):
    rec = mix_reciente(U)
    F = _rasgos(X, rec, clima)
    ok = U.notna().all(axis=1) & (U.sum(axis=1) > 0) & rec.notna().all(axis=1)
    return F[ok.to_numpy()], U[ok]


def _rasgos_fut(U: pd.DataFrame, fut: pd.DataFrame, clima: bool) -> pd.DataFrame:
    s = U.iloc[-VENTANA:].fillna(0).sum() + 0.5
    rec = np.log(s / s.sum()).add_prefix("logmix_")
    rec = pd.DataFrame([rec.to_numpy()] * len(fut), columns=rec.index)
    return _rasgos(fut, rec, clima)


def _probas(modelo, F: pd.DataFrame, n_cats: int) -> np.ndarray:
    p = np.zeros((len(F), n_cats))
    p[:, modelo.classes_] = modelo.predict_proba(F.to_numpy(float))
    return p / p.sum(axis=1, keepdims=True)


# ------------------------------------------------------------- modelos
def multinomial(clima: bool, C: float = 1.0):
    def f(U: pd.DataFrame, X: pd.DataFrame, fut: pd.DataFrame) -> pd.DataFrame:
        F, Uo = _entrenamiento(U, X, clima)
        Xl, yl, wl = _largo(F, Uo)
        m = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=5000))
        m.fit(Xl, yl, logisticregression__sample_weight=wl)
        return pd.DataFrame(_probas(m, _rasgos_fut(U, fut, clima), U.shape[1]), index=fut.index, columns=U.columns)

    return f


def catalogo() -> dict:
    return {"media_4sem": media_4sem, "multinomial": multinomial(clima=False),
            "multinomial_clima": multinomial(clima=True)}


# ------------------------------------------------ unidades por categoría
def unidades_categoria(sq: pd.DataFrame, P: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Unidades por categoría = pronóstico del segmento × participación.

    `sq`: pronóstico del segmento (q0.5) y límites del intervalo 80 % (q0.1/q0.9), índice = días.
    `P`: participaciones (mismo índice, filas que suman 1). Devuelve
    {categoría: DataFrame con las mismas columnas que `sq`}; por construcción
    las categorías suman el segmento en cada columna."""
    assert sq.index.equals(P.index), "Índices distintos entre segmento y participaciones"
    assert np.allclose(P.sum(axis=1), 1), "Las participaciones no suman 1"
    return {c: sq.mul(P[c], axis=0) for c in P.columns}


# ------------------------------------------------------ efecto de la temperatura
def efecto_temperatura(U: pd.DataFrame, X: pd.DataFrame, t_frio: float, t_calor: float,
                       n_boot: int = 200, semilla: int = SEMILLA) -> pd.DataFrame:
    """Efecto de la temperatura en el mix (descriptivo, con todos los datos).

    Multinomial con día de la semana, verano, temperatura máxima y precipitación
    (sin el mix reciente, que absorbería parte del efecto estacional). Efecto
    marginal promedio: se predice el mix de TODOS los días observados poniendo
    la temperatura en `t_frio` y luego en `t_calor`, y se promedia. Intervalo
    95 % por bootstrap de bloques semanales (las semanas se remuestrean enteras
    para respetar la autocorrelación)."""
    ok = U.notna().all(axis=1) & (U.sum(axis=1) > 0)
    U, X = U[ok], X[ok]
    F = _rasgos(X, pd.DataFrame(index=X.index), clima=True)
    semana = X.index.to_period("W-SUN")

    def ajustar_y_contrastar(idx):
        Xl, yl, wl = _largo(F.iloc[idx], U.iloc[idx])
        m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=5000))
        m.fit(Xl, yl, logisticregression__sample_weight=wl)
        res = []
        for t in (t_frio, t_calor):
            Ft = F.assign(temperature_2m_max=t)
            res.append(_probas(m, Ft, U.shape[1]).mean(axis=0))
        return np.asarray(res)

    punto = ajustar_y_contrastar(np.arange(len(U)))
    rng = np.random.default_rng(semilla)
    semanas = semana.unique()
    pos = {s: np.flatnonzero(semana == s) for s in semanas}
    boots = []
    for _ in range(n_boot):
        elegidas = rng.choice(semanas, size=len(semanas), replace=True)
        boots.append(ajustar_y_contrastar(np.concatenate([pos[s] for s in elegidas])))
    dif = np.asarray([b[1] - b[0] for b in boots])
    return pd.DataFrame({"categoria": U.columns, "pct_frio": 100 * punto[0], "pct_calor": 100 * punto[1],
                         "calor_menos_frio_pp": 100 * (punto[1] - punto[0]),
                         "ic95_inf_pp": 100 * np.quantile(dif, 0.025, axis=0),
                         "ic95_sup_pp": 100 * np.quantile(dif, 0.975, axis=0)})
