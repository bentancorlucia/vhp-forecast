"""Fase 5: backtest walk-forward de los modelos del total de viandas.

Corre los modelos en los 12 orígenes semanales (y en los 12 sábados anteriores,
solo para armar el intervalo 80 %), calcula MAE, MASE, WAPE y cobertura,
Diebold-Mariano entre los mejores y Ljung-Box de los residuos de ETS y SARIMA.
Usa datos públicos (unidades × K): MASE, WAPE y cobertura no dependen de K;
MAE queda multiplicado por K.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from vhp import eda  # noqa: E402
from vhp import evaluate as ev  # noqa: E402
from vhp.config import cargar_config, ruta  # noqa: E402
from vhp.models import baselines, ets, lgbm, mlp, sarimax  # noqa: E402


def modelos(cfg: dict) -> dict:
    """Catálogo de modelos del backtest (nombre → función), en orden de complejidad."""
    M = cfg["mlp"]
    return {
        "naive": baselines.modelo("naive"),
        "naive_estacional": baselines.modelo("naive_estacional"),
        "media_movil_4sem": baselines.modelo("media_movil_4sem"),
        "ets": ets.modelo(),
        "sarima": sarimax.modelo(),
        "lgbm_directo": lgbm.directo(ev.EXOG_CAL),
        "mlp": mlp.modelo(ev.EXOG_CAL, epocas_max=M["epocas_max"], paciencia=M["paciencia"],
                          semanas_validacion=M["semanas_validacion"]),
    }


def grilla_total(cfg: dict | None = None, uid: str = "Total") -> pd.DataFrame:
    """Grilla de modelado del Total (o de otra serie de la jerarquía, ej. Total/particulares)."""
    cfg = cfg or cargar_config()
    d = eda.cargar_datos()
    return ev.armar_grilla(d["ancho"][uid], d["clima"], cfg["serie"]["meses_verano"])


def fig_backtest(res: pd.DataFrame, nombres: list[str], destino, serie: str = "Total") -> None:
    fig, axs = plt.subplots(len(nombres), 1, figsize=(12, 2.6 * len(nombres)), sharex=True)
    for ax, m in zip(axs, nombres):
        d = res[res["modelo"] == m].sort_values("fecha")
        ax.fill_between(d["fecha"], d["q0.1"], d["q0.9"], alpha=0.25, step="mid", label="intervalo 80 %")
        ax.plot(d["fecha"], d["y"], "k.-", lw=0.8, label="real")
        ax.plot(d["fecha"], d["q0.5"], "o-", ms=3, lw=1, label="pronóstico")
        ax.set_title(m, fontsize=10)
    axs[0].legend(ncol=3, fontsize=8)
    fig.suptitle(f"Backtest walk-forward de {serie}, {eda.periodo(res['fecha'])} (unidades × K)")
    fig.tight_layout()
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)


# Un solo backtest: el Total (particulares + empresas), con datos hasta la última semana completa.
SERIES = {"Total": ("fin_test", "backtest_total", "07_backtest_total.png")}


def correr() -> dict:
    return {uid: correr_serie(uid, *v) for uid, v in SERIES.items()}


def correr_serie(uid: str = "Total", clave_fin: str = "fin_test", prefijo: str = "backtest_total",
                 figura: str = "07_backtest_total.png") -> dict:
    cfg = cargar_config()
    p = cfg["pronostico"]
    g = grilla_total(cfg, uid)
    origs = ev.origenes(g, p["semanas_test"], p[clave_fin])
    print(f"Backtest {uid}: {len(origs)} orígenes ({origs[0]:%d/%m/%Y} a {origs[-1]:%d/%m/%Y})")
    res = ev.backtest(g, modelos(cfg), origs, p["semanas_intervalo"])
    met = ev.metricas(res)
    por_h = (res.assign(ae=(res["y"] - res["q0.5"]).abs() / res["escala_mase"])
             .pivot_table(index="modelo", columns="h", values="ae", aggfunc="mean"))
    mejores = list(met["modelo"].head(4))
    if "naive_estacional" not in mejores:
        mejores.append("naive_estacional")
    dm = ev.tabla_dm(res, mejores)

    hist_final, _ = ev.partir(g, origs[-1])
    resid_sarima, espec = sarimax.ajuste_final(hist_final)
    lb = []
    for nombre, resid in [("ets", ets.residuos(hist_final)), ("sarima (log)", resid_sarima)]:
        lb.append(ev.ljung_box(resid[hist_final["abierto"] == 1]).assign(modelo=nombre))
    lb = pd.concat(lb)[["modelo", "rezago", "lb_stat", "lb_pvalue"]]

    tablas, figs = ruta("tablas", cfg), ruta("figuras", cfg)
    periodo = eda.periodo(res["fecha"])
    res.to_csv(tablas / f"{prefijo}_predicciones.csv", index=False)
    met.round(4).to_csv(tablas / f"{prefijo}_metricas.csv", index=False)
    por_h.round(4).to_csv(tablas / f"{prefijo}_mase_por_h.csv")
    dm.round(4).to_csv(tablas / f"{prefijo}_dm.csv", index=False)
    lb.round(4).to_csv(tablas / f"{prefijo}_ljung_box.csv", index=False)
    fig_backtest(res, list(met["modelo"].head(3)) + ["naive_estacional"], figs / figura, uid.split("/")[-1])

    print(f"Métricas, backtest {periodo} ({res['fecha'].nunique()} días abiertos):")
    print(met.round(3).to_string(index=False))
    print("MASE por horizonte (1 = lunes … 6 = sábado):\n" + por_h.loc[met["modelo"]].round(2).to_string())
    print("Diebold-Mariano (pérdida absoluta, HLN):\n" + dm.round(3).to_string(index=False))
    print(f"SARIMA elegido por AIC al último origen: {espec}")
    print("Ljung-Box, residuos dentro de la muestra al último origen:\n" + lb.round(4).to_string(index=False))
    return {"res": res, "metricas": met, "dm": dm, "ljung_box": lb, "por_h": por_h, "spec_sarima": espec}
