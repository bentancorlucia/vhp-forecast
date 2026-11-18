"""Fase 6: clima → mix de categorías.

Unidades por categoría = pronóstico del segmento (lgbm_directo, el modelo
elegido para el total) × participación pronosticada. Se comparan tres modelos
de participaciones (`models/mix.py`): media_4sem, multinomial y multinomial con
clima. El elegido es media_4sem (decisión de Lucía): el clima no mejora el
pronóstico a una semana, aunque sí mueve el mix (efecto descriptivo, calor vs.
frío, con IC por bootstrap de semanas). Las categorías suman el segmento por
construcción (las participaciones suman 1).

Mismo walk-forward que la fase 5: 12 orígenes (sábados), 6 días por origen,
ventana expansiva, métricas solo en días abiertos de cada serie. Intervalo
80 % de las unidades por categoría, igual que en el total (`ev.intervalos`):
ŷ × [p10, p90] de y / ŷ de la misma serie y el mismo método en los 12 orígenes
previos (se corren además los 12 sábados anteriores al test).
Datos públicos (unidades × K): MASE, WAPE, participaciones y log loss por
vianda no dependen de K.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from vhp import eda, series  # noqa: E402
from vhp import evaluate as ev  # noqa: E402
from vhp.config import cargar_config, ruta  # noqa: E402
from vhp.models import lgbm  # noqa: E402
from vhp.models import mix as mx  # noqa: E402

NIVELES = {0: "total", 1: "segmento", 2: "categoria"}


def nivel(uid: str) -> str:
    return NIVELES[uid.count("/")]


# --------------------------------------------------------------------- datos
def cargar(cfg: dict | None = None) -> dict:
    """Grillas de modelado de las 17 series (mismo índice lunes a sábado) y la matriz S."""
    cfg = cfg or cargar_config()
    d = eda.cargar_datos()
    cierres = cfg["serie"].get("cierres_segmento") or {}
    _, S, tags = series.jerarquia(d["diarias"], pd.DatetimeIndex(d["cal"].index), cierres,
                                  cfg["serie"].get("fin_segmento"))
    G = {}
    for uid in S.index:
        seg = uid.split("/")[1] if "/" in uid else None
        G[uid] = ev.armar_grilla(d["ancho"][uid], d["clima"].reset_index(), cfg["serie"]["meses_verano"],
                                 cierres.get(seg) if seg else None)
    # Todas empiezan el mismo día; empresas y el Total terminan antes (31/08/2026) que
    # particulares: cada grilla es un tramo inicial de la más larga.
    largo = max(G.values(), key=len).index
    assert all(largo[: len(g)].equals(g.index) for g in G.values()), "Las grillas no comparten índice"
    return {"G": G, "S": S, "segmentos": [s.split("/")[1] for s in tags["total/segmento"]]}


def unidades_segmento(G: dict, S: pd.DataFrame, seg: str) -> pd.DataFrame:
    """Unidades por categoría del segmento (NaN en días cerrados del segmento)."""
    hojas = [h for h in S.columns if h.split("/")[1] == seg]
    return pd.DataFrame({h.split("/")[2]: G[h]["y"] for h in hojas})


# --------------------------------------------------------------- backtest
def _filas(q: pd.DataFrame, modelo: str, uid: str, origen, G: dict, escala: float) -> pd.DataFrame:
    g = G[uid].loc[q.index]
    df = q[["q0.1", "q0.5", "q0.9"]].copy()
    df["modelo"], df["unique_id"], df["origen"] = modelo, uid, pd.Timestamp(origen)
    df["h"], df["y"], df["escala_mase"] = np.arange(1, len(q) + 1), g["y"], escala
    return df[g["abierto"].to_numpy() == 1]


def backtest(datos: dict, origs: list, modelos_mix: dict | None = None, semanas_intervalo: int = 12,
             verbose: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (pred, part), solo para los orígenes de test `origs`:
    - pred: modelo de participaciones × serie × origen × fecha, con q0.1/q0.5/q0.9
      (intervalo 80 % por errores relativos previos) e y real. Nivel segmento =
      lgbm_directo (modelo "lgbm_directo"); nivel categoría = segmento × participación.
    - part: participaciones pronosticadas vs. unidades reales por categoría."""
    G, S, segs = datos["G"], datos["S"], datos["segmentos"]
    modelos_mix = modelos_mix or mx.catalogo()
    f_seg = lgbm.directo(ev.EXOG_CAL)
    previos = ev.origenes_previos(G["Total"], origs[0], semanas_intervalo)
    test = {pd.Timestamp(o) for o in origs}
    filas, filas_part = [], []
    for o in [*previos, *origs]:
        for s in segs:
            seg_id = f"Total/{s}"
            hist, fut = ev.partir(G[seg_id], o)
            sq = f_seg(hist, fut)
            filas.append(_filas(sq, "lgbm_directo", seg_id, o, G, ev.escala_mase(hist)))
            U = unidades_segmento(G, S, s)
            for nombre, f in modelos_mix.items():
                P = f(U.loc[hist.index], hist, fut)
                uc = mx.unidades_categoria(sq, P)
                assert np.allclose(sum(uc.values())["q0.5"], sq["q0.5"]), "Las categorías no suman el segmento"
                for c, q in uc.items():
                    u = f"{seg_id}/{c}"
                    filas.append(_filas(q, nombre, u, o, G, ev.escala_mase(G[u].loc[hist.index])))
                if pd.Timestamp(o) in test:
                    real = U.loc[fut.index]
                    for c in P:
                        filas_part.append(pd.DataFrame({"metodo": nombre, "segmento": s, "origen": pd.Timestamp(o),
                                                        "fecha": fut.index, "categoria": c, "p": P[c].to_numpy(),
                                                        "unidades": real[c].to_numpy()}))
        if verbose:
            print(f"  origen {pd.Timestamp(o):%d/%m/%Y} listo", flush=True)
    res = pd.concat(filas).rename_axis("fecha").reset_index()
    # intervalo 80 %: percentiles de y / ŷ por serie y modelo en los orígenes previos
    pred = pd.concat([ev.intervalos(d, origs, semanas_intervalo) for _, d in res.groupby("unique_id")],
                     ignore_index=True)
    pred["nivel"] = pred["unique_id"].map(nivel)
    part = pd.concat(filas_part, ignore_index=True).dropna(subset=["unidades"])
    return pred, part


# ---------------------------------------------------------------- métricas
def metricas_unidades(pred: pd.DataFrame) -> pd.DataFrame:
    """Por nivel y modelo: MASE (media de |e|/escala), WAPE (agrupado) y cobertura del intervalo 80 %."""
    d = pred.assign(ae=(pred["y"] - pred["q0.5"]).abs())
    d["se"] = d["ae"] / d["escala_mase"]
    d["c"] = (d["y"] >= d["q0.1"]) & (d["y"] <= d["q0.9"])
    g = d.groupby(["nivel", "modelo"])
    out = pd.DataFrame({"MASE": g["se"].mean(), "WAPE": g["ae"].sum() / g["y"].sum(), "n": g.size(),
                        "cobertura_80": g["c"].mean()})
    return out.reset_index().sort_values(["nivel", "MASE"])


def metricas_participacion(part: pd.DataFrame) -> pd.DataFrame:
    """Por modelo de participaciones y segmento: log loss por vianda
    (−Σ u·log p / Σ u) y error absoluto medio de la participación en puntos."""
    d = part.copy()
    tot = d.groupby(["metodo", "segmento", "fecha"])["unidades"].transform("sum")
    d = d[tot > 0]
    d["real"] = d["unidades"] / tot[tot > 0]
    d["ll"] = -d["unidades"] * np.log(d["p"].clip(lower=1e-9))
    g = d.groupby(["segmento", "metodo"])
    out = pd.DataFrame({"logloss_por_vianda": g["ll"].sum() / g["unidades"].sum(),
                        "error_abs_medio_pp": 100 * g.apply(lambda x: (x["p"] - x["real"]).abs().mean(),
                                                            include_groups=False)})
    return out.reset_index().sort_values(["segmento", "logloss_por_vianda"])


def dm_participacion(part: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """Diebold-Mariano sobre la log loss diaria por vianda de dos modelos de participaciones."""
    filas = []
    for s, d in part.groupby("segmento"):
        ll = d.assign(ll=-d["unidades"] * np.log(d["p"].clip(lower=1e-9)))
        dia = ll.groupby(["metodo", "fecha"]).agg(ll=("ll", "sum"), u=("unidades", "sum"))
        dia = (dia["ll"] / dia["u"]).unstack("metodo").dropna()
        dm, p = ev.diebold_mariano(dia[a].to_numpy(), dia[b].to_numpy(), perdida="abs")
        filas.append({"segmento": s, "modelo_1": a, "modelo_2": b, "dias": len(dia), "DM": dm, "p_valor": p,
                      "mejor": a if dm < 0 else b})
    return pd.DataFrame(filas)


# ------------------------------------------------- efecto de la temperatura
def efecto_temperatura(datos: dict, n_boot: int = 200) -> tuple[pd.DataFrame, dict]:
    """Mix con frío (percentil 10 de la temperatura máxima en días abiertos) vs.
    calor (percentil 90), por segmento, con todo el período."""
    G, S = datos["G"], datos["S"]
    gt = G["Total"]
    temp = gt.loc[gt["abierto"] == 1, "temperature_2m_max"]
    t_frio, t_calor = float(temp.quantile(0.1)), float(temp.quantile(0.9))
    out = []
    for s in datos["segmentos"]:
        U = unidades_segmento(G, S, s)
        out.append(mx.efecto_temperatura(U, G[f"Total/{s}"], t_frio, t_calor, n_boot=n_boot).assign(segmento=s))
    info = {"t_frio": t_frio, "t_calor": t_calor, "periodo": eda.periodo(temp.index)}
    return pd.concat(out, ignore_index=True), info


# ----------------------------------------------------------------- figuras
def fig_efecto(ef: pd.DataFrame, info: dict, destino) -> None:
    segs = ef["segmento"].unique()
    fig, axs = plt.subplots(1, len(segs), figsize=(11, 4), sharex=True)
    for ax, s in zip(np.atleast_1d(axs), segs):
        d = ef[ef["segmento"] == s].sort_values("calor_menos_frio_pp")
        err = [d["calor_menos_frio_pp"] - d["ic95_inf_pp"], d["ic95_sup_pp"] - d["calor_menos_frio_pp"]]
        colores = np.where(d["calor_menos_frio_pp"] > 0, "#c8553d", "#2f6690")
        ax.barh(d["categoria"], d["calor_menos_frio_pp"], xerr=err, color=colores, capsize=3)
        ax.axvline(0, color="k", lw=0.8)
        ax.set_title(s.capitalize())
        ax.set_xlabel("puntos porcentuales del mix")
    fig.suptitle(f"Cambio en el mix con calor ({info['t_calor']:.1f} °C) vs. frío ({info['t_frio']:.1f} °C), "
                 f"{info['periodo']} — IC 95 % bootstrap por semanas", fontsize=10)
    fig.tight_layout()
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_participaciones(part: pd.DataFrame, segmento: str, modelos: list[str], destino) -> None:
    """Participación semanal real vs. pronosticada en el backtest (cociente de sumas por semana)."""
    d = part[part["segmento"] == segmento]
    cats = sorted(d["categoria"].unique())
    semanal = {}
    for m in modelos:  # participación semanal: Σ p·(total real del día) / Σ total real
        x = d[d["metodo"] == m]
        x = x.assign(pu=x["p"] * x.groupby("fecha")["unidades"].transform("sum"))
        g = x.groupby(["origen", "categoria"])[["pu", "unidades"]].sum()
        tot = g.groupby("origen")["unidades"].sum()
        semanal[m] = (g["pu"].unstack().div(tot, axis=0) * 100, g["unidades"].unstack().div(tot, axis=0) * 100)
    fig, axs = plt.subplots(2, 4, figsize=(14, 5.5), sharex=True)
    for ax, c in zip(axs.ravel(), cats):
        for m in modelos:
            ax.plot(semanal[m][0].index, semanal[m][0][c], "o-", ms=3, lw=1, label=m)
        real = semanal[modelos[0]][1]
        ax.plot(real.index, real[c], "k.-", lw=1.2, label="real")
        ax.set_title(c, fontsize=9)
        ax.tick_params(axis="x", labelrotation=45, labelsize=7)
    axs.ravel()[-1].axis("off")
    axs[0, 0].legend(fontsize=7)
    fig.suptitle(f"Mix semanal de {segmento} (% de viandas), backtest {eda.periodo(d['fecha'])}; "
                 "eje x = sábado de origen", fontsize=10)
    fig.tight_layout()
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------- correr
def correr() -> dict:
    cfg = cargar_config()
    p = cfg["pronostico"]
    datos = cargar(cfg)
    origs = ev.origenes(datos["G"]["Total"], p["semanas_test"], p["fin_test"])
    print(f"Fase 6: {len(origs)} orígenes ({origs[0]:%d/%m/%Y} a {origs[-1]:%d/%m/%Y})")
    pred, part = backtest(datos, origs)
    met = metricas_unidades(pred)
    mpart = metricas_participacion(part)
    dm = pd.concat([dm_participacion(part, "multinomial_clima", "multinomial"),
                    dm_participacion(part, "multinomial_clima", "media_4sem")], ignore_index=True)
    ef, info = efecto_temperatura(datos)

    tablas, figs = ruta("tablas", cfg), ruta("figuras", cfg)
    periodo = eda.periodo(pred["fecha"])
    pred.to_csv(tablas / "mix_backtest_predicciones.csv", index=False)
    part.to_csv(tablas / "mix_backtest_participaciones.csv", index=False)
    met.round(4).to_csv(tablas / "mix_metricas_unidades.csv", index=False)
    mpart.round(4).to_csv(tablas / "mix_metricas_participacion.csv", index=False)
    dm.round(4).to_csv(tablas / "mix_dm_participacion.csv", index=False)
    ef.round(3).to_csv(tablas / "mix_efecto_temperatura.csv", index=False)
    fig_efecto(ef, info, figs / "08_mix_efecto_temperatura.png")
    fig_participaciones(part, "particulares", ["media_4sem", "multinomial_clima"], figs / "09_mix_backtest_particulares.png")

    print(f"Métricas de unidades, backtest {periodo}:")
    print(met.round(3).to_string(index=False))
    print(f"Participaciones, backtest {periodo}:")
    print(mpart.round(4).to_string(index=False))
    print("Diebold-Mariano, log loss diaria por vianda:\n" + dm.round(3).to_string(index=False))
    print(f"Efecto de la temperatura ({info['periodo']}; frío = {info['t_frio']:.1f} °C, "
          f"calor = {info['t_calor']:.1f} °C):")
    print(ef.round(2).to_string(index=False))
    return {"pred": pred, "part": part, "metricas": met, "metricas_part": mpart, "dm": dm, "efecto": ef, "info": info}
