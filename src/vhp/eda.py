"""Análisis exploratorio (fase 4) sobre los datos PÚBLICOS de data/processed/.

Las unidades están multiplicadas por K: los niveles absolutos no son reales,
pero sí los cocientes, participaciones, correlaciones y tests (no cambian con K).

Todo es descriptivo (usa la muestra completa): nada de esto sirve como
feature de pronóstico.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402
from scipy import stats  # noqa: E402
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf  # noqa: E402
from statsmodels.tsa.seasonal import STL  # noqa: E402
from statsmodels.tsa.stattools import adfuller  # noqa: E402

from vhp import series  # noqa: E402
from vhp.config import cargar_config, ruta  # noqa: E402

SERIES_PRINCIPALES = {"Total": "Total", "Total/particulares": "Particulares", "Total/empresas": "Empresas"}
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
VARIABLES_CAL = ["feriado_laborable", "vispera_cierre", "post_cierre", "verano"]


# --------------------------------------------------------------------------- datos
def cargar_datos() -> dict:
    """Calendario, series jerárquicas en ancho (fecha × serie), ventas y clima."""
    cfg = cargar_config()
    cal = pd.read_csv(ruta("processed", cfg) / "calendario.csv", parse_dates=["fecha"]).set_index("fecha")
    diarias = pd.read_csv(ruta("processed", cfg) / "ventas_diarias.csv", parse_dates=["fecha"])
    Y, _, tags = series.jerarquia(diarias, pd.DatetimeIndex(cal.index), cfg["serie"].get("cierres_segmento"),
                                  cfg["serie"].get("fin_segmento"))
    ancho = Y.pivot(index="ds", columns="unique_id", values="y")
    clima = pd.read_csv(ruta("external", cfg) / "clima_montevideo.csv", parse_dates=["fecha"]).set_index("fecha")
    return {"cal": cal, "ancho": ancho, "diarias": diarias, "clima": clima, "tags": tags}


def periodo(idx) -> str:
    """Texto 'dd/mm/aaaa–dd/mm/aaaa' para rotular tablas y figuras."""
    return f"{idx.min():%d/%m/%Y}–{idx.max():%d/%m/%Y}"


# ------------------------------------------------------------ descomposición y tests
def stl(y: pd.Series, periodo_est: int = 6) -> tuple[pd.DataFrame, dict]:
    """STL robusta (período 6 = una semana hábil) y fuerzas de tendencia y estacionalidad
    (Hyndman & Athanasopoulos, FPP3 §4.3)."""
    f = STL(y.to_numpy(), period=periodo_est, robust=True).fit()
    comp = pd.DataFrame({"y": y.to_numpy(), "tendencia": f.trend, "estacional": f.seasonal, "resto": f.resid},
                        index=y.index)
    r = comp["resto"].var()
    fuerzas = {"fuerza_tendencia": max(0.0, 1 - r / (comp["tendencia"] + comp["resto"]).var()),
               "fuerza_estacional": max(0.0, 1 - r / (comp["estacional"] + comp["resto"]).var())}
    return comp, fuerzas


def estacionariedad(y: pd.Series, estacion: int = 6) -> pd.DataFrame:
    """ADF (H0: raíz unitaria) en nivel y diferenciada. p < 0,05 → se rechaza la raíz unitaria."""
    transformaciones = {"nivel": y,
                        f"dif. estacional ({estacion})": y.diff(estacion),
                        f"dif. estacional + dif. 1": y.diff(estacion).diff()}
    filas = [{"transformacion": nombre, "n": len(x.dropna()), "adf_p": adfuller(x.dropna(), autolag="AIC")[1]}
             for nombre, x in transformaciones.items()]
    out = pd.DataFrame(filas)
    out["conclusion"] = np.where(out.adf_p < 0.05, "estacionaria", "no estacionaria")
    return out


# ---------------------------------------------------------------- perfiles y efectos
def perfil_dia_semana(ancho: pd.DataFrame) -> pd.DataFrame:
    """Índice por día de la semana (media del día / media de la serie) por segmento."""
    cols = list(SERIES_PRINCIPALES)
    m = ancho[cols].groupby(ancho.index.dayofweek).mean()
    out = (m / ancho[cols].mean()).rename(columns=SERIES_PRINCIPALES)
    out.index = DIAS
    return out


def efectos_calendario(ancho: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    """Efecto de feriados laborables, días junto a un cierre y verano (enero), en %.

    Regresión lineal de log(y) contra una tendencia lineal (en semanas), el día de la
    semana y las dummies de calendario, con errores HAC (Newey-West, 6 rezagos).
    El efecto en % es 100·(exp(β) − 1); para la tendencia, es el crecimiento por semana.
    """
    filas = []
    for col, nombre in SERIES_PRINCIPALES.items():
        y = ancho[col].dropna()
        df = cal.loc[y.index].copy()
        df["semanas"] = np.arange(len(df)) / 6
        df["ly"] = np.log(y.where(y > 0))  # días con 0 (sábados de empresas en 2025) quedan afuera
        df = df.dropna(subset=["ly"])
        m = smf.ols("ly ~ semanas + C(dia_semana) + " + " + ".join(VARIABLES_CAL), data=df).fit(
            cov_type="HAC", cov_kwds={"maxlags": 6})
        ic = m.conf_int()
        for v in ["semanas"] + VARIABLES_CAL:
            filas.append({"serie": nombre, "variable": "tendencia (por semana)" if v == "semanas" else v,
                          "dias": len(df) if v == "semanas" else int(df[v].sum()),
                          "efecto_pct": 100 * (np.exp(m.params[v]) - 1),
                          "ic95_inf_pct": 100 * (np.exp(ic.loc[v, 0]) - 1),
                          "ic95_sup_pct": 100 * (np.exp(ic.loc[v, 1]) - 1),
                          "p_valor": m.pvalues[v]})
    return pd.DataFrame(filas)


# ------------------------------------------------------------- agregación semanal
def _semana(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Lunes de la semana (lunes a domingo) de cada fecha."""
    return pd.DatetimeIndex(idx.to_period("W-SUN").start_time)


def semanal(y: pd.Series, min_dias: int = 3) -> pd.Series:
    """Media por día hábil de cada semana (lunes a domingo), rotulada con el lunes.

    La media, y no la suma, para que las semanas con feriado no laborable sean
    comparables. Se descartan las semanas con menos de `min_dias` días hábiles
    observados (ej.: la del 31/08/2026, que solo tiene el lunes y saldría inflada).
    """
    y = y.dropna()
    g = y.groupby(_semana(y.index))
    n = g.size()
    return g.mean()[n >= min_dias]


# ------------------------------------------------------------------- mix y clima
def participaciones_semanales(diarias: pd.DataFrame, segmento: str | None = None) -> pd.DataFrame:
    """Participación de cada categoría en las viandas de cada semana (lunes a domingo)."""
    v = diarias[diarias["tipo_producto"] == "Vianda"]
    if segmento:
        v = v[v["segmento"] == segmento]
    u = v.pivot_table(index="fecha", columns="categoria", values="unidades", aggfunc="sum").fillna(0)
    dias = u.groupby(_semana(u.index)).size()
    u = u.groupby(_semana(u.index)).sum()
    u = u[(dias >= 3) & (u.sum(axis=1) > 0)]
    return u.div(u.sum(axis=1), axis=0)


def oferta_vs_temperatura(lineas: pd.DataFrame, temp: pd.Series) -> pd.DataFrame:
    """Control: ¿el mix se mueve porque cambia el MENÚ o porque cambia la ELECCIÓN?

    Usa las líneas internas (con nombre de plato; no se publica): % de platos
    distintos ofrecidos de cada categoría por semana, contra la temperatura.
    Si la oferta no se mueve con la temperatura, el efecto en el mix es demanda.
    """
    mapa, _ = series.cargar_categorias()
    v = series.asignar_categoria(lineas, mapa)
    v = v[v["tipo_producto"] == "Vianda"]
    sem = _semana(pd.DatetimeIndex(v["fecha_entrega"]))
    of = v.assign(plato=series.plato_base(v["producto"]), sem=sem).groupby(["sem", "categoria"])["plato"].nunique()
    of = of.unstack(fill_value=0)
    sh = of.div(of.sum(axis=1), axis=0).loc[lambda x: x.index.isin(temp.index)]
    t = temp.reindex(sh.index)
    filas = [{"categoria": c, "platos_ofrecidos_medios": of[c].mean(), "rho_oferta_temp": stats.spearmanr(sh[c], t)[0],
              "p_valor": stats.spearmanr(sh[c], t)[1]} for c in sh]
    out = pd.DataFrame(filas)
    out.attrs["platos_por_semana"] = of.sum(axis=1).describe()
    return out


def temperatura_semanal(clima: pd.DataFrame, dias: pd.DatetimeIndex, var: str = "temperature_2m_max") -> pd.Series:
    """Media semanal de la variable de clima, solo en días hábiles."""
    return semanal(clima[var].reindex(dias))


def mix_vs_temperatura(part: pd.DataFrame, temp: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Spearman entre participación semanal y temperatura máxima media, y
    participación media por tercil de temperatura (frío / templado / calor)."""
    temp = temp.reindex(part.index)
    filas = []
    for c in part:
        rho, p = stats.spearmanr(part[c], temp)
        filas.append({"categoria": c, "participacion_media_pct": 100 * part[c].mean(), "rho_spearman": rho, "p_valor": p})
    corr = pd.DataFrame(filas).sort_values("rho_spearman")
    tercil = pd.qcut(temp, 3, labels=["frío", "templado", "calor"])
    por_tercil = 100 * part.groupby(tercil, observed=True).mean().T
    por_tercil["calor − frío (pp)"] = por_tercil["calor"] - por_tercil["frío"]
    rangos = temp.groupby(tercil, observed=True).agg(["min", "max", "size"])
    por_tercil.attrs["rangos"] = rangos
    return corr, por_tercil.sort_values("calor − frío (pp)")


# -------------------------------------------------------------------------- figuras
def _guardar(fig, nombre: str) -> None:
    destino = ruta("figuras")
    destino.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_series(ancho: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 4))
    for col, nombre in SERIES_PRINCIPALES.items():
        ax.plot(ancho.index, ancho[col], lw=0.5, alpha=0.35)
        s = semanal(ancho[col])
        ax.plot(s.index, s, lw=2, label=f"{nombre} (media semanal)", color=ax.lines[-1].get_color())
    ax.set(title=f"Viandas por día hábil — {periodo(ancho.index)} (unidades × K)", ylabel="unidades × K")
    ax.legend()
    _guardar(fig, "01_series_diarias.png")


def fig_stl(comp: pd.DataFrame, titulo: str) -> None:
    fig, axs = plt.subplots(4, 1, figsize=(11, 8), sharex=True)
    for ax, c in zip(axs, comp.columns):
        ax.plot(comp.index, comp[c], lw=0.8)
        ax.set_ylabel(c)
    axs[0].set_title(titulo)
    _guardar(fig, "02_stl_total.png")


def fig_acf(y: pd.Series) -> None:
    fig, axs = plt.subplots(2, 2, figsize=(11, 6))
    d = y.diff(6).dropna()
    plot_acf(y, lags=36, ax=axs[0, 0], title="ACF — Total en nivel")
    plot_pacf(y, lags=36, ax=axs[0, 1], method="ywm", title="PACF — Total en nivel")
    plot_acf(d, lags=36, ax=axs[1, 0], title="ACF — dif. estacional (6)")
    plot_pacf(d, lags=36, ax=axs[1, 1], method="ywm", title="PACF — dif. estacional (6)")
    fig.suptitle(f"Autocorrelación, {periodo(y.index)}")
    fig.tight_layout()
    _guardar(fig, "03_acf_pacf.png")


def fig_dia_semana(dow: pd.DataFrame, idx) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    dow.plot.bar(ax=ax, rot=0)
    ax.axhline(1, color="k", lw=0.7)
    ax.set(title=f"Índice por día de la semana (1 = media) — {periodo(idx)}")
    _guardar(fig, "04_dia_semana.png")


def fig_mix(part: pd.DataFrame, temp: pd.Series, corr: pd.DataFrame) -> None:
    cats = list(corr["categoria"])
    fig, axs = plt.subplots(2, 4, figsize=(14, 6.5), sharex=True)
    for ax, c in zip(axs.flat, cats):
        ax.scatter(temp.reindex(part.index), 100 * part[c], s=12)
        rho = corr.set_index("categoria").loc[c, "rho_spearman"]
        ax.set_title(f"{c} (ρ = {rho:+.2f})", fontsize=10)
        ax.set_ylabel("% de viandas")
    axs.flat[-1].axis("off")
    for ax in axs[1]:
        ax.set_xlabel("temp. máx. media semanal (°C)")
    fig.suptitle(f"Mix de categorías vs. temperatura, semanas {periodo(part.index)}")
    fig.tight_layout()
    _guardar(fig, "06_mix_temperatura.png")


# ---------------------------------------------------------------------- principal
def correr() -> dict:
    """Fase 4: calcula todo, guarda figuras y tablas, e imprime un resumen."""
    d = cargar_datos()
    ancho, cal = d["ancho"], d["cal"]
    tot = ancho["Total"].dropna()

    comp, fuerzas = stl(tot)
    est = estacionariedad(tot)
    dow = perfil_dia_semana(ancho)
    efectos = efectos_calendario(ancho, cal)
    tot_sem = semanal(tot)
    # Mix de los dos segmentos juntos: solo hasta el último día con ambos (si no, desde
    # septiembre 2026 el mix sería solo de particulares y cambiaría por composición)
    fin_comun = tot.dropna().index.max()
    part = participaciones_semanales(d["diarias"][d["diarias"]["fecha"] <= fin_comun])
    temp = temperatura_semanal(d["clima"], ancho.index)
    corr, tercil = mix_vs_temperatura(part, temp)

    fig_series(ancho)
    fig_stl(comp, f"STL (período 6, robusta) del Total — {periodo(tot.index)}")
    fig_acf(tot)
    fig_dia_semana(dow, tot.index)
    fig_mix(part, temp, corr)

    tablas = ruta("tablas")
    tablas.mkdir(parents=True, exist_ok=True)
    est.to_csv(tablas / "eda_estacionariedad.csv", index=False)
    dow.round(3).to_csv(tablas / "eda_dia_semana.csv")
    efectos.round(4).to_csv(tablas / "eda_efectos_calendario.csv", index=False)
    corr.round(4).to_csv(tablas / "eda_mix_temperatura.csv", index=False)
    tercil.round(2).to_csv(tablas / "eda_mix_tercil_temperatura.csv")
    oferta = None
    lineas_int = ruta("interim") / "lineas.parquet"
    if lineas_int.exists():  # control interno: solo con los datos privados
        oferta = oferta_vs_temperatura(pd.read_parquet(lineas_int), temp)
        oferta.round(4).to_csv(tablas / "eda_oferta_temperatura.csv", index=False)

    p = periodo(tot.index)
    print(f"Período: {p} ({len(tot)} días hábiles, {len(tot_sem)} semanas)")
    print(f"STL: fuerza tendencia {fuerzas['fuerza_tendencia']:.2f} | fuerza estacional {fuerzas['fuerza_estacional']:.2f}")
    print(est.round(4).to_string(index=False))
    print("Índice día de semana:\n" + dow.round(2).to_string())
    print("Efectos de calendario (regresión de log y, HAC):\n" + efectos.round(3).to_string(index=False))
    print("Mix vs temperatura (Spearman, semanal):\n" + corr.round(3).to_string(index=False))
    print("Participación por tercil de temperatura (%):\n" + tercil.round(1).to_string())
    print("Rangos de los terciles (°C):\n" + tercil.attrs["rangos"].round(1).to_string())
    if oferta is not None:
        print("Control de oferta (% de platos ofrecidos vs temperatura):\n" + oferta.round(3).to_string(index=False))
    return {"oferta": oferta, "fuerzas": fuerzas, "estacionariedad": est, "dia_semana": dow, "efectos": efectos,
            "mix_corr": corr, "mix_tercil": tercil}
