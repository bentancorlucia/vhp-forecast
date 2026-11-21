"""Fase 5: backtest walk-forward de los modelos del total de viandas.

Corre los 8 modelos en los 12 orígenes semanales (y en los 12 sábados anteriores,
solo para armar el intervalo 80 %), calcula MAE, MASE, WAPE y cobertura,
Diebold-Mariano entre los mejores y de SARIMAX (el modelo del proyecto) contra
cada uno, y Ljung-Box de los residuos de ETS, SARIMA y SARIMAX. Lo mismo en la
ventana anterior (12 orígenes hasta `fin_test_ventana_anterior`), que no se usó
para elegir SARIMAX, y los coeficientes del SARIMAX al último origen.
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
from vhp.nombres import nombre  # noqa: E402


def modelos(cfg: dict) -> dict:
    """Catálogo de modelos del backtest (nombre → función), en orden de complejidad."""
    M = cfg["mlp"]
    return {
        "naive": baselines.modelo("naive"),
        "naive_estacional": baselines.modelo("naive_estacional"),
        "media_movil_4sem": baselines.modelo("media_movil_4sem"),
        "ets": ets.modelo(),
        "sarima": sarimax.modelo(),
        "sarimax": sarimax.modelo_calendario(ev.EXOG_CAL),
        "lgbm_directo": lgbm.directo(ev.EXOG_CAL),
        "mlp": mlp.modelo(ev.EXOG_CAL, epocas_max=M["epocas_max"], paciencia=M["paciencia"],
                          semanas_validacion=M["semanas_validacion"]),
    }


def grilla_total(cfg: dict | None = None, uid: str = "Total") -> pd.DataFrame:
    """Grilla de modelado del Total (o de otra serie de la jerarquía, ej. Total/particulares)."""
    cfg = cfg or cargar_config()
    d = eda.cargar_datos()
    seg = uid.split("/")[-1]
    cierres = (cfg["serie"].get("cierres_segmento") or {}).get(seg) if uid != "Total" else None
    return ev.armar_grilla(d["ancho"][uid], d["clima"], cfg["serie"]["meses_verano"], cierres_extra=cierres)


def fig_backtest(res: pd.DataFrame, nombres: list[str], destino, serie: str = "Total") -> None:
    fig, axs = plt.subplots(len(nombres), 1, figsize=(12, 2.6 * len(nombres)), sharex=True)
    for ax, m in zip(axs, nombres):
        d = res[res["modelo"] == m].sort_values("fecha")
        ax.fill_between(d["fecha"], d["q0.1"], d["q0.9"], alpha=0.25, step="mid", label="Intervalo 80 %")
        ax.plot(d["fecha"], d["y"], "k.-", lw=0.8, label="Real")
        ax.plot(d["fecha"], d["q0.5"], "o-", ms=3, lw=1, label="Pronóstico")
        ax.set_title(nombre(m), fontsize=10)
    axs[0].legend(ncol=3, fontsize=8)
    fig.suptitle(f"Backtest walk-forward, {nombre(serie)}, {eda.periodo(res['fecha'])} (unidades × K)")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)


# Backtest del Total y de cada segmento: mismos orígenes, modelos e intervalo.
# La figura es solo del Total (figura = None en los segmentos).
SERIES = {
    "Total": ("fin_test", "backtest_total", "07_backtest_total.png"),
    "Total/particulares": ("fin_test", "backtest_particulares", None),
    "Total/empresas": ("fin_test", "backtest_empresas", None),
}


# Modelos de la figura del backtest, en orden fijo (decisión de Lucía, 21/11/2026):
# el modelo del proyecto primero, después SARIMA, ETS y la referencia naive estacional.
FIG_MODELOS = ["lgbm_directo", "sarima", "ets", "naive_estacional"]


def correr() -> dict:
    cfg = cargar_config()
    out = {uid: correr_serie(uid, *v) for uid, v in SERIES.items()}
    # Validación de la elección de SARIMAX en datos que no se usaron para elegirla
    for uid, (_, prefijo, _) in SERIES.items():
        out[f"{uid} (ventana anterior)"] = correr_serie(uid, "fin_test_ventana_anterior",
                                                        f"{prefijo}_ventana_anterior", None, completo=False)
    out["coeficientes"] = tabla_coeficientes(cfg)
    out["robustez"] = robustez(cfg)
    return out


# ---------------------------------------------------------------- robustez
VENTANAS = {"anterior": "_ventana_anterior", "nueva": ""}
DIA_EXPORT_INCOMPLETO = "2026-08-17"


def _metricas_ventanas(cfg: dict) -> pd.DataFrame:
    """MASE de cada modelo en cada serie × ventana, con el período de la ventana
    (leído de las predicciones guardadas por `correr_serie`)."""
    tablas = ruta("tablas", cfg)
    filas = []
    for uid, (_, prefijo, _) in SERIES.items():
        for ventana, suf in VENTANAS.items():
            met = pd.read_csv(tablas / f"{prefijo}{suf}_metricas.csv")
            pred = pd.read_csv(tablas / f"{prefijo}{suf}_predicciones.csv", parse_dates=["fecha"])
            filas.append(met[["modelo", "MASE"]].assign(serie=uid, ventana=ventana,
                                                        periodo=eda.periodo(pred["fecha"])))
    return pd.concat(filas, ignore_index=True)


def tabla_puestos(m: pd.DataFrame) -> pd.DataFrame:
    """Puesto (1 = menor MASE) de cada modelo en cada serie × ventana."""
    m = m.copy()
    m["puesto"] = m.groupby(["serie", "ventana"])["MASE"].rank(method="min").astype(int)
    return m[["serie", "ventana", "periodo", "modelo", "puesto", "MASE"]].sort_values(
        ["serie", "ventana", "puesto"]).reset_index(drop=True)


def tabla_peor_caso(m: pd.DataFrame) -> pd.DataFrame:
    """Para cada modelo, el MASE relativo al mejor de cada serie × ventana, en %
    ((MASE / MASE del mejor − 1) × 100), y el máximo de esos valores con la serie
    y la ventana donde ocurre. Ordenada de menor a mayor."""
    m = m.copy()
    m["pct_sobre_mejor"] = (m["MASE"] / m.groupby(["serie", "ventana"])["MASE"].transform("min") - 1) * 100
    peor = m.loc[m.groupby("modelo")["pct_sobre_mejor"].idxmax()]
    out = peor.rename(columns={"pct_sobre_mejor": "peor_pct_sobre_mejor", "serie": "serie_peor",
                               "ventana": "ventana_peor", "periodo": "periodo_peor", "MASE": "MASE_peor"})
    ancho = m.assign(col=m["serie"] + " | " + m["ventana"]).pivot(index="modelo", columns="col",
                                                                  values="pct_sobre_mejor")
    out = out.merge(ancho.add_prefix("pct ").reset_index(), on="modelo")
    return out.sort_values("peor_pct_sobre_mejor").reset_index(drop=True)


def tabla_sin_dia(cfg: dict, dia: str = DIA_EXPORT_INCOMPLETO) -> pd.DataFrame:
    """MASE y puesto de los 8 modelos en la ventana anterior, con y sin `dia`
    en la evaluación (mismo recorte para todos). Solo para informar."""
    tablas = ruta("tablas", cfg)
    filas = []
    for uid, (_, prefijo, _) in SERIES.items():
        res = pd.read_csv(tablas / f"{prefijo}_ventana_anterior_predicciones.csv", parse_dates=["fecha"])
        con = ev.metricas(res)[["modelo", "MASE"]]
        sin = ev.metricas(res[res["fecha"] != pd.Timestamp(dia)])[["modelo", "MASE", "n"]]
        t = con.merge(sin, on="modelo", suffixes=("_con", "_sin"))
        t["puesto_con"] = t["MASE_con"].rank(method="min").astype(int)
        t["puesto_sin"] = t["MASE_sin"].rank(method="min").astype(int)
        filas.append(t.assign(serie=uid, periodo=eda.periodo(res["fecha"]), dia_excluido=f"{pd.Timestamp(dia):%d/%m/%Y}"))
    out = pd.concat(filas, ignore_index=True)
    return out[["serie", "periodo", "dia_excluido", "modelo", "n", "MASE_con", "puesto_con", "MASE_sin",
                "puesto_sin"]].sort_values(["serie", "puesto_sin"]).reset_index(drop=True)


def robustez(cfg: dict | None = None) -> dict:
    """Tablas de robustez: puestos, peor caso y chequeo sin el 17/08/2026."""
    cfg = cfg or cargar_config()
    tablas = ruta("tablas", cfg)
    m = _metricas_ventanas(cfg)
    puestos, peor, sin = tabla_puestos(m), tabla_peor_caso(m), tabla_sin_dia(cfg)
    puestos.round(4).to_csv(tablas / "robustez_puestos.csv", index=False)
    peor.round(2).to_csv(tablas / "robustez_peor_caso.csv", index=False)
    sin.round(4).to_csv(tablas / "robustez_sin_17_08.csv", index=False)
    print("Robustez, peor caso (% de MASE por encima del mejor de cada serie × ventana):")
    print(peor[["modelo", "peor_pct_sobre_mejor", "serie_peor", "ventana_peor", "periodo_peor"]].round(1).to_string(index=False))
    return {"puestos": puestos, "peor_caso": peor, "sin_17_08": sin}


def dm_contra(res: pd.DataFrame, base: str = "sarimax") -> pd.DataFrame:
    """Diebold-Mariano de `base` contra cada uno de los otros modelos, con los días
    que gana cada uno y el error absoluto total de cada uno (mismos días)."""
    ancho = res.pivot_table(index="fecha", columns="modelo", values="q0.5")
    y = res.drop_duplicates("fecha").set_index("fecha")["y"].reindex(ancho.index)
    filas = []
    for m in [c for c in ancho.columns if c != base]:
        e_b, e_m = (y - ancho[base]).abs(), (y - ancho[m]).abs()
        dm, p = ev.diebold_mariano(y - ancho[base], y - ancho[m])
        filas.append({"modelo_1": base, "modelo_2": m, "DM": dm, "p_valor": p, "mejor": None if pd.isna(dm) else (base if dm < 0 else m),
                      "dias_gana_1": int((e_b < e_m).sum()), "dias_gana_2": int((e_m < e_b).sum()),
                      "error_abs_1": e_b.sum(), "error_abs_2": e_m.sum()})
    return pd.DataFrame(filas)


def tabla_coeficientes(cfg: dict | None = None) -> pd.DataFrame:
    """SARIMAX ajustado al último origen del backtest (Total y cada segmento):
    β, IC 95 %, efecto % con su IC, p-valor, orden por AIC y período de ajuste."""
    cfg = cfg or cargar_config()
    p = cfg["pronostico"]
    filas = []
    for uid in SERIES:
        g = grilla_total(cfg, uid)
        o = ev.origenes(g, p["semanas_test"], p["fin_test"])[-1]
        hist, _ = ev.partir(g, o)
        filas.append(sarimax.coeficientes(hist, ev.EXOG_CAL)
                     .assign(serie=uid, origen=f"{o:%d/%m/%Y}", periodo_ajuste=eda.periodo(hist.index)))
    out = pd.concat(filas, ignore_index=True)
    out = out[["serie", "variable", "beta", "beta_ic_inf", "beta_ic_sup", "efecto_pct", "efecto_ic_inf",
               "efecto_ic_sup", "p_valor", "orden", "aic", "origen", "periodo_ajuste"]]
    out.round(4).to_csv(ruta("tablas", cfg) / "sarimax_coeficientes.csv", index=False)
    print("Coeficientes del SARIMAX al último origen (efecto % = (e^β − 1) × 100):")
    print(out.drop(columns=["aic"]).round(3).to_string(index=False))
    return out


def correr_serie(uid: str = "Total", clave_fin: str = "fin_test", prefijo: str = "backtest_total",
                 figura: str | None = "07_backtest_total.png", completo: bool = True) -> dict:
    """Backtest de los 8 modelos en una serie. `completo=False` (ventana anterior):
    solo métricas y DM de SARIMAX contra cada modelo."""
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
    dm_sarimax = dm_contra(res, "sarimax")
    tablas, figs = ruta("tablas", cfg), ruta("figuras", cfg)
    periodo = eda.periodo(res["fecha"])
    print(f"Métricas, backtest {uid} {periodo} ({res['fecha'].nunique()} días abiertos):")
    print(met.round(3).to_string(index=False))
    print("Diebold-Mariano de SARIMAX contra cada modelo:\n" + dm_sarimax.round(3).to_string(index=False))
    if not completo:
        res.to_csv(tablas / f"{prefijo}_predicciones.csv", index=False)
        met.round(4).assign(periodo=periodo).to_csv(tablas / f"{prefijo}_metricas.csv", index=False)
        dm_sarimax.round(4).assign(periodo=periodo).to_csv(tablas / f"{prefijo}_dm_sarimax.csv", index=False)
        return {"res": res, "metricas": met, "dm_sarimax": dm_sarimax}
    dm_lgbm = dm_contra(res, "lgbm_directo")

    hist_final, _ = ev.partir(g, origs[-1])
    resid_sarima, espec = sarimax.ajuste_final(hist_final)
    resid_sarimax, espec_x = sarimax.ajuste_final(hist_final, ev.EXOG_CAL)
    lb = []
    for nombre, resid in [("ets", ets.residuos(hist_final)), ("sarima (log)", resid_sarima),
                          ("sarimax (log)", resid_sarimax)]:
        lb.append(ev.ljung_box(resid[hist_final["abierto"] == 1]).assign(modelo=nombre))
    lb = pd.concat(lb)[["modelo", "rezago", "lb_stat", "lb_pvalue"]]

    res.to_csv(tablas / f"{prefijo}_predicciones.csv", index=False)
    met.round(4).to_csv(tablas / f"{prefijo}_metricas.csv", index=False)
    por_h.round(4).to_csv(tablas / f"{prefijo}_mase_por_h.csv")
    dm.round(4).to_csv(tablas / f"{prefijo}_dm.csv", index=False)
    lb.round(4).to_csv(tablas / f"{prefijo}_ljung_box.csv", index=False)
    dm_lgbm.round(4).to_csv(tablas / f"{prefijo}_dm_lgbm.csv", index=False)
    dm_sarimax.round(4).to_csv(tablas / f"{prefijo}_dm_sarimax.csv", index=False)
    if figura:
        fig_backtest(res, FIG_MODELOS, figs / figura, uid)

    print("MASE por horizonte (1 = lunes … 6 = sábado):\n" + por_h.loc[met["modelo"]].round(2).to_string())
    print("Diebold-Mariano (pérdida absoluta, HLN):\n" + dm.round(3).to_string(index=False))
    print(f"Orden elegido por AIC al último origen: SARIMA {espec}, SARIMAX {espec_x}")
    print("Ljung-Box, residuos dentro de la muestra al último origen:\n" + lb.round(4).to_string(index=False))
    return {"res": res, "metricas": met, "dm": dm, "dm_lgbm": dm_lgbm, "dm_sarimax": dm_sarimax, "ljung_box": lb,
            "por_h": por_h, "spec_sarima": espec, "spec_sarimax": espec_x}
