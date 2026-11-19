"""Fase 8: gasto en Meta Ads y clientes nuevos de particulares (nivel semanal, gancho 2).

Semanas de lunes a domingo, 05/01/2026–08/11/2026 (44 semanas, las del export de Meta;
hasta el 17/11/2026 eran 34, hasta el 30/08/2026).
- Objetivo: log(clientes nuevos de particulares).
- Gasto: gasto_meta_total (34 semanas, contiene el escalón enero → febrero, cuando entra
  la agencia) y gasto_campania_viandas (desde el 02/02/2026, 30 semanas; casi no varía).

Piezas:
1. Coeficiente de variación del gasto y de los clics (¿hay variación con la que medir algo?).
2. Regresiones lineales log(clientes nuevos) ~ log(x) + verano, con x = gasto total (44
   semanas), gasto de la campaña (desde el 02/02/2026, incluye la baja de noviembre) y
   clics de la campaña (desde el 02/02/2026: los clics sí varían, por los cambios de anuncios).
3. Tests de Granger con 1 rezago (fijado antes de mirar): gasto de campaña → clientes
   nuevos y clics → clientes nuevos.
Desde el 02/02/2026 no hay ninguna semana de enero: `verano` es constante y sale de la
regresión (queda solo la constante). Se declara en la tabla (columna `control`).
Los clics no se asignan al azar (dependen de qué anuncios elige la agencia): también es
correlación. No hay origen del pedido (UTM) en el export: la atribución por anuncio queda fuera.

Todo es correlación, no causa: con un solo escalón (que coincide con el fin del
verano) y un gasto casi constante después, el efecto no queda identificado.
Gasto en índice base 100 y conteos × K: las elasticidades (log-log) no dependen de K
ni de la base del índice.
"""
from __future__ import annotations

import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402
from statsmodels.tsa.stattools import grangercausalitytests  # noqa: E402

from vhp import eda  # noqa: E402
from vhp.config import cargar_config, ruta  # noqa: E402

INICIO_CAMPANIA = "2026-02-02"  # primera semana con la campaña de viandas (entra la agencia)
# Fijado ANTES de mirar el resultado: 1 rezago = una semana, el horizonte natural de una
# campaña semanal; con 30 semanas, más rezagos comen grados de libertad. No se prueban otros.
REZAGO_GRANGER = 1
# Rezagos de Newey-West para los errores estándar de la regresión (autocorrelación semanal).
REZAGOS_HAC = 2


# --------------------------------------------------------------------- datos
def cargar(cfg: dict | None = None) -> pd.DataFrame:
    """Una fila por semana de Meta (lunes) con clientes nuevos de particulares, gasto en log y verano."""
    cfg = cfg or cargar_config()
    p = ruta("processed", cfg)
    meta = pd.read_csv(p / "meta_ads_semanal_indice.csv", parse_dates=["semana_ini"])
    part = pd.read_csv(p / "particulares_semanal.csv", parse_dates=["semana_ini"])
    cal = pd.read_csv(p / "calendario.csv", parse_dates=["fecha"])
    cal["semana_ini"] = cal["fecha"].dt.to_period("W-SUN").dt.start_time
    # verano = fracción de días hábiles de la semana en enero (misma definición que calendar.py)
    c = cal.groupby("semana_ini").agg(verano=("verano", "mean"))
    d = meta.merge(part, on="semana_ini", how="left").merge(c, on="semana_ini", how="left").set_index("semana_ini")
    if d["clientes_nuevos_particulares"].isna().any():
        raise ValueError("Faltan semanas de particulares en el período de Meta")
    d["log_clientes_nuevos"] = np.log(d["clientes_nuevos_particulares"])
    d["log_gasto_total"] = np.log(d["gasto_meta_total"])
    d["log_gasto_campania"] = np.log(d["gasto_campania_viandas"])
    d["log_clics"] = np.log(d["clics"])
    return d


def variacion_gasto(d: pd.DataFrame) -> pd.DataFrame:
    """Coeficiente de variación del gasto (sin unidades: no depende de la base del índice)."""
    filas = []
    for col, desde in [("gasto_meta_total", None), ("gasto_meta_total", INICIO_CAMPANIA),
                       ("gasto_campania_viandas", None), ("clics", None)]:
        x = d[col].dropna()
        if desde:
            x = x[x.index >= desde]
        filas.append({"serie": col, "desde": x.index.min(), "hasta": x.index.max(), "semanas": len(x),
                      "cv_pct": 100 * x.std() / x.mean(), "max_sobre_min": x.max() / x.min()})
    return pd.DataFrame(filas)


# ------------------------------------------------------------ regresión
def regresion(d: pd.DataFrame, y: str = "log_clientes_nuevos", x: str = "log_gasto_total",
              control: str = "verano", desde=None) -> pd.DataFrame:
    """MCO y = a + β·x + γ·verano con errores de Newey-West.

    Decisiones:
    - En log-log: β es una elasticidad y no depende de K ni de la base 100 del índice de
      gasto (en niveles el coeficiente cambiaría con la anonimización y no se podría leer).
    - Gasto TOTAL y no el de campaña: la campaña está vacía en enero, así que el único
      salto de gasto del período (enero → febrero) solo aparece en el total. Desde febrero
      el gasto casi no varía, así que sin el escalón no habría nada con qué estimar.
    - El verano (enero) cae exactamente en las mismas semanas que el gasto bajo: la
      columna `corr_x_control` muestra esa colinealidad, que es la razón de fondo por la
      que el efecto no queda identificado.
    """
    df = d[[y, x, control]].dropna()
    if desde is not None:
        df = df[df.index >= pd.Timestamp(desde)]
    usa_control = df[control].nunique() > 1  # desde febrero no hay enero: verano constante
    regs = [x, control] if usa_control else [x]
    X = sm.add_constant(df[regs])
    r = sm.OLS(df[y], X).fit(cov_type="HAC", cov_kwds={"maxlags": REZAGOS_HAC})
    ic = r.conf_int()
    filas = [{"y": y, "x": x, "termino": c, "coef": r.params[c], "ic95_inf": ic.loc[c, 0], "ic95_sup": ic.loc[c, 1],
              "p_valor": r.pvalues[c]} for c in regs]
    out = pd.DataFrame(filas)
    out["control"] = control if usa_control else f"{control} constante: fuera"
    out["semanas"], out["r2"] = len(df), r.rsquared
    out["corr_x_control"] = df[x].corr(df[control]) if usa_control else np.nan
    out["desde"], out["hasta"] = df.index.min(), df.index.max()
    return out


# ------------------------------------------------------------ Granger
def granger(d: pd.DataFrame, y: str = "log_clientes_nuevos", x: str = "log_gasto_campania",
            rezago: int = REZAGO_GRANGER) -> pd.DataFrame:
    """Test F de Granger x → y con un único rezago (H0: x no ayuda a predecir y).

    Clientes nuevos en log niveles, como antes (no tienen tendencia; solo los pedidos se
    diferenciaban)."""
    df = d[[y, x]].dropna()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = grangercausalitytests(df[[y, x]], maxlag=[rezago])
    f, p, _, _ = res[rezago][0]["ssr_ftest"]
    return pd.DataFrame([{"causa": x, "efecto": y, "rezagos": rezago, "F": f, "p_valor": p, "semanas": len(df),
                          "desde": df.index.min(), "hasta": df.index.max()}])


# ------------------------------------------------------------------ figura
def fig_ads(d: pd.DataFrame, destino) -> None:
    """Gasto vs. clientes nuevos: serie en índice y dispersión (log-log) marcando enero."""
    fig, axs = plt.subplots(1, 3, figsize=(16, 4))
    ax = axs[0]
    for c, et, est in [("clientes_nuevos_particulares", "clientes nuevos", "o-"),
                       ("gasto_meta_total", "gasto Meta total", "s--"),
                       ("gasto_campania_viandas", "gasto campaña viandas", "s--")]:
        s = d[c]
        ax.plot(s.index, 100 * s / s[s.index >= INICIO_CAMPANIA].mean(), est, ms=3, lw=1, label=et)
    ax.axvline(pd.Timestamp(INICIO_CAMPANIA), color="C3", lw=0.8, ls=":")
    ax.set_title("Índice (media desde 02/02/2026 = 100)", fontsize=9)
    ax.legend(fontsize=7)
    ax.tick_params(axis="x", labelrotation=45, labelsize=7)
    ax = axs[1]
    ver = d["verano"] > 0
    ax.scatter(d.loc[~ver, "log_gasto_total"], d.loc[~ver, "log_clientes_nuevos"], s=14, label="feb–ago")
    ax.scatter(d.loc[ver, "log_gasto_total"], d.loc[ver, "log_clientes_nuevos"], s=14, color="C3",
               label="enero (verano)")
    ax.set_xlabel("log gasto Meta total (índice)")
    ax.set_ylabel("log clientes nuevos (× K)")
    ax.set_title("El escalón de gasto coincide con el fin del verano", fontsize=9)
    ax.legend(fontsize=7)
    ax = axs[2]
    c = d[d.index >= INICIO_CAMPANIA]
    nov = c.index >= "2026-11-02"
    ax.scatter(c.loc[~nov, "log_clics"], c.loc[~nov, "log_clientes_nuevos"], s=14, label="feb–oct")
    ax.scatter(c.loc[nov, "log_clics"], c.loc[nov, "log_clientes_nuevos"], s=24, color="C3", marker="D",
               label="noviembre (baja de pauta)")
    b = np.polyfit(c["log_clics"], c["log_clientes_nuevos"], 1)
    xs = np.linspace(c["log_clics"].min(), c["log_clics"].max(), 10)
    ax.plot(xs, np.polyval(b, xs), "k--", lw=0.8)
    ax.set_xlabel("log clics de la campaña (índice)")
    ax.set_ylabel("log clientes nuevos (× K)")
    ax.set_title("Clics vs. clientes nuevos (desde el 02/02/2026)", fontsize=9)
    ax.legend(fontsize=7)
    fig.suptitle(f"Meta Ads y clientes nuevos de particulares, semanas {eda.periodo(d.index)}", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ correr
def correr() -> dict:
    cfg = cargar_config()
    d = cargar(cfg)
    var = variacion_gasto(d)
    reg = pd.concat([regresion(d),
                     regresion(d, x="log_gasto_campania", desde=INICIO_CAMPANIA),
                     regresion(d, x="log_clics", desde=INICIO_CAMPANIA)], ignore_index=True)
    gc = pd.concat([granger(d), granger(d, x="log_clics")], ignore_index=True)

    tablas, figs = ruta("tablas", cfg), ruta("figuras", cfg)
    var.round(4).to_csv(tablas / "ads_variacion_gasto.csv", index=False)
    reg.round(4).to_csv(tablas / "ads_regresion.csv", index=False)
    gc.round(4).to_csv(tablas / "ads_granger.csv", index=False)
    fig_ads(d, figs / "11_meta_ads.png")

    print(f"Fase 8: {len(d)} semanas ({eda.periodo(d.index)})")
    print("Variación del gasto:\n" + var.round(3).to_string(index=False))
    print("Regresiones log(clientes nuevos) ~ log(x) + verano (HAC):\n" + reg.round(3).to_string(index=False))
    print("Granger (1 rezago, fijado de antemano):\n" + gc.round(3).to_string(index=False))
    return {"datos": d, "variacion": var, "regresion": reg, "granger": gc}
