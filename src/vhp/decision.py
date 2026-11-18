"""Fase 9: plan de compras (gancho 4).

Pronóstico (decisión de Lucía, fase 6): lgbm_directo por segmento × participación
media de las últimas 4 semanas (`media_4sem`) → pronóstico por segmento × categoría.
Referencia: naive estacional por categoría (mismo día de la semana anterior).

Una sola granularidad: se compra una vez por semana (los 6 días, lunes a sábado)
para cada segmento × categoría. El pronóstico semanal es la suma de los días
abiertos.

Plan = pronóstico + colchón. El colchón sale de los errores del propio pronóstico
en las 12 semanas anteriores al origen (sin mirar la semana que se planifica):
    r = y / ŷ  (demanda real de la semana / pronóstico de esa semana)
    plan_p = ŷ · percentil_p(r)
Se prueban p = 40, 45, …, 95 y se elige el de menor costo simulado en el backtest
(sobrante $200 y faltante $150 por vianda, `config.yaml`). Se reportan también
p = 80, 90 y 95 como referencia ("alcanza 8, 9 o 9,5 de cada 10 semanas").
Ojo: p se elige mirando el costo del backtest (24/08–14/11/2026), así que ese
costo es algo optimista para el futuro; el colchón de cada semana sí usa solo
semanas previas.

Desde el 18/11/2026 (datos nuevos):
- Cada segmento puede tener su propia ventana de backtest (`fin_test_<segmento>`); desde el
  18/11/2026 los dos terminan en la última semana completa (09/11–14/11/2026).
- Sobrante y faltante ponderados por la proporción de XL del segmento en las 12 semanas
  previas a cada origen (x): sobrante = 200·(1 − x) + 260·x; faltante = 150·(1 − x) + 155·x
  (margen $350 − $200 y $415 − $260). Con `ponderar_xl: false` vuelve a los costos fijos.
- Plan real de la semana 16–21/11/2026: los dos segmentos desde el origen 14/11/2026.

Por qué cociente y no diferencia: es lo mismo que el intervalo 80 % del paso 2
(percentiles de y / ŷ), el error crece con el nivel de la serie y, sobre todo,
permite juntar categorías de tamaños muy distintos (carne vacuna ≈ 10 veces
cerdo): un error de +10 % significa lo mismo en las dos, uno de +50 viandas no.
Por qué juntar las 7 categorías del segmento: hay un error por serie y semana;
con 12 semanas el percentil 90 y el 95 de una sola categoría serían casi el
máximo. Juntando las 7 hay 84 errores por segmento. El intervalo diario de las
categorías del mix (mismo método) cubre 79,9 % (fase 6), así que el cociente
está bien calibrado.

Datos públicos (unidades × K): cocientes, % de sobrante/faltante, coberturas y
costo por vianda demandada no dependen de K. El plan en porciones públicas está
× K; la versión en porciones reales (÷ K) y el costo total en UYU van a
data/interim/ (no se suben).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from vhp import eda, jerarquico  # noqa: E402
from vhp import evaluate as ev  # noqa: E402
from vhp.calendar import tabla_feriados, variables_calendario  # noqa: E402
from vhp.config import cargar_config, ruta  # noqa: E402
from vhp.models import lgbm  # noqa: E402
from vhp.models import mix as mx  # noqa: E402

CLAVE = ["segmento", "categoria"]
METODOS = ["lgbm", "naive_estacional"]


# ---------------------------------------------------------------- pronóstico
def fut_semana(G_seg: pd.DataFrame, origen, meses_verano, cierres_extra=None) -> pd.DataFrame:
    """Los 6 lunes a sábado después de `origen` con sus variables de calendario,
    aunque estén fuera de la grilla (para el plan real de la semana siguiente)."""
    origen = pd.Timestamp(origen)
    dias = pd.date_range(origen + pd.Timedelta(days=1), periods=7, freq="D")
    dias = dias[dias.dayofweek <= 5]
    fer = tabla_feriados(dias.min(), dias.max())
    fut = variables_calendario(dias, fer, tuple(meses_verano)).set_index("fecha")
    cerrados = set(fer.loc[fer["tipo"] == "no_laborable", "fecha"]) | set(pd.to_datetime(cierres_extra or []))
    fut["abierto"] = (~fut.index.isin(cerrados)).astype(int)
    fut["t"] = G_seg["t"].iloc[-1] + 1 + np.arange(len(fut)) if len(G_seg) else np.arange(len(fut))
    return fut


def pronosticar_origen(datos: dict, origen, cfg: dict, fut_externo: bool = False,
                       segmentos: list[str] | None = None, origen_hist: dict | None = None) -> pd.DataFrame:
    """Pronóstico diario por segmento × categoría para la semana siguiente a `origen`.

    Columnas: lgbm (segmento × participación media 4 semanas), naive_estacional
    e y (NaN si no hay dato). Solo días abiertos.
    `origen_hist` ({segmento: fecha}): para un segmento sin datos recientes (empresas),
    la historia se corta en esa fecha y el pronóstico se pone en la semana de `origen`."""
    G, S = datos["G"], datos["S"]
    cierres = cfg["serie"].get("cierres_segmento") or {}
    f_seg = lgbm.directo(ev.EXOG_CAL)
    filas = []
    for s in segmentos or datos["segmentos"]:
        uid = f"Total/{s}"
        o_h = pd.Timestamp((origen_hist or {}).get(s, origen))
        hist = G[uid].loc[G[uid].index <= o_h]
        if fut_externo:
            fut = fut_semana(hist, origen, cfg["serie"]["meses_verano"], cierres.get(s))
        else:
            _, fut = ev.partir(G[uid], origen)
        sq = f_seg(hist, fut)
        U = jerarquico.unidades_segmento(G, S, s)
        P = mx.media_4sem(U.loc[hist.index], hist, fut)
        uc = mx.unidades_categoria(sq[["q0.5"]], P)
        for c, q in uc.items():
            gc = G[f"{uid}/{c}"]
            ym = gc.loc[hist.index, "y_modelo"].to_numpy(float)
            filas.append(pd.DataFrame({
                "origen": pd.Timestamp(origen), "fecha": fut.index, "segmento": s, "categoria": c,
                "abierto": fut["abierto"].to_numpy(), "lgbm": q["q0.5"].to_numpy(),
                "naive_estacional": ym[-ev.H:][: len(fut)],
                "y": gc["y"].reindex(fut.index).to_numpy()}))
    out = pd.concat(filas, ignore_index=True)
    return out[out["abierto"] == 1].drop(columns="abierto")


def backtest(datos: dict, origs, cfg: dict, verbose: bool = True) -> pd.DataFrame:
    """`origs`: lista de orígenes (todos los segmentos) o {segmento: orígenes}."""
    por_seg = origs if isinstance(origs, dict) else {s: list(origs) for s in datos["segmentos"]}
    filas = []
    for o in sorted({pd.Timestamp(x) for v in por_seg.values() for x in v}):
        segs = [s for s, v in por_seg.items() if o in {pd.Timestamp(x) for x in v}]
        filas.append(pronosticar_origen(datos, o, cfg, segmentos=segs))
        if verbose:
            print(f"  origen {pd.Timestamp(o):%d/%m/%Y} listo", flush=True)
    return pd.concat(filas, ignore_index=True)


def semanal(pred: pd.DataFrame, metodos: list[str] = METODOS) -> pd.DataFrame:
    """Suma de los días abiertos de cada semana pronosticada (real y pronóstico)."""
    cols = [m for m in metodos if m in pred] + ["y"]
    return pred.groupby(["origen", *CLAVE], as_index=False)[cols].sum(min_count=1)


# ------------------------------------------------------------------- colchón
def semanas_previas(sem: pd.DataFrame, origen, semanas: int = 12) -> pd.DataFrame:
    """Filas de las `semanas` semanas anteriores al origen: orígenes o' con
    o' + 7 días ≤ origen (su semana ya terminó) y o' > origen − 7·(semanas + 1)."""
    o = pd.Timestamp(origen)
    return sem[(sem["origen"] <= o - pd.Timedelta(days=7))
               & (sem["origen"] > o - pd.Timedelta(days=7 * (semanas + 1)))]


def factores(previas: pd.DataFrame, metodo: str, ps, por: list[str] = ["segmento"]) -> pd.DataFrame:
    """Percentil p del cociente y / ŷ por grupo (`por`), para cada p de `ps`.
    Por defecto se juntan las 7 categorías del segmento."""
    d = previas[(previas[metodo] > 0) & previas["y"].notna()]
    d = d.assign(r=d["y"] / d[metodo])
    filas = []
    for k, x in d.groupby(por):
        k = k if isinstance(k, tuple) else (k,)
        filas.append({**dict(zip(por, k)), "n_errores": len(x),
                      **{p: float(np.percentile(x["r"], p)) for p in ps}})
    return pd.DataFrame(filas)


def planes(sem: pd.DataFrame, origs_test: list, metodos: list[str], ps, semanas: int = 12) -> pd.DataFrame:
    """Plan semanal para cada origen de test: ŷ × percentil p de los errores previos.

    Devuelve una fila por origen × segmento × categoría × método × p con plan e y."""
    filas = []
    for o in origs_test:
        prev = semanas_previas(sem, o, semanas)
        actual = sem[sem["origen"] == pd.Timestamp(o)]
        for m in metodos:
            x = actual.merge(factores(prev, m, ps), on="segmento", how="left")
            for p in ps:
                filas.append(pd.DataFrame({**{k: x[k] for k in ["origen", *CLAVE, "y"]}, "metodo": m, "p": p,
                                           "n_errores": x["n_errores"], "pronostico": x[m],
                                           "plan": x[m] * x[p]}))
    return pd.concat(filas, ignore_index=True)


# ---------------------------------------------------------------- simulación
def prop_xl_previa(xl: pd.DataFrame, segmento: str, origen, semanas: int = 12) -> float:
    """Proporción media de XL del segmento en las `semanas` semanas (lunes a domingo) que
    empiezan antes del origen (la semana del origen ya terminó el sábado)."""
    o = pd.Timestamp(origen)
    d = xl[(xl["segmento"] == segmento) & (xl["semana_ini"] < o)
           & (xl["semana_ini"] >= o - pd.Timedelta(days=7 * semanas))]
    return float(d["prop_xl"].mean())


def agregar_xl(pl: pd.DataFrame, xl: pd.DataFrame, semanas: int = 12) -> pd.DataFrame:
    """Columna prop_xl (12 semanas previas a cada origen, por segmento) para ponderar costos."""
    claves = pl[["origen", "segmento"]].drop_duplicates()
    claves["prop_xl"] = [prop_xl_previa(xl, s, o, semanas) for o, s in zip(claves["origen"], claves["segmento"])]
    return pl.merge(claves, on=["origen", "segmento"], how="left")


def simular(pl: pd.DataFrame, cf: float, cs: float, por: list[str] | None = None,
            cs_xl: float | None = None, cf_xl: float | None = None) -> pd.DataFrame:
    """Sobrantes y faltantes simulados: plan contra la demanda real de cada semana.

    Si se pasan cs_xl / cf_xl y `pl` tiene prop_xl (x), el costo por vianda de cada fila es
    el promedio ponderado: cs·(1 − x) + cs_xl·x y cf·(1 − x) + cf_xl·x."""
    d = pl.dropna(subset=["y", "plan"])
    x = d["prop_xl"] if (cs_xl is not None and "prop_xl" in d) else 0.0
    c_s = cs * (1 - x) + (cs_xl if cs_xl is not None else cs) * x
    c_f = cf * (1 - x) + (cf_xl if cf_xl is not None else cf) * x
    d = d.assign(sobra=(d["plan"] - d["y"]).clip(lower=0), falta=(d["y"] - d["plan"]).clip(lower=0),
                 alcanza=d["y"] <= d["plan"])
    d = d.assign(c_sobra=c_s * d["sobra"], c_falta=c_f * d["falta"])
    g = d.groupby([*(por or []), "metodo", "p"])
    dem = g["y"].sum()
    out = pd.DataFrame({"n": g.size(), "cobertura": g["alcanza"].mean(),
                        "sobrante_pct": 100 * g["sobra"].sum() / dem,
                        "faltante_pct": 100 * g["falta"].sum() / dem,
                        "plan_sobre_demanda": g["plan"].sum() / dem,
                        "costo_por_vianda": (g["c_sobra"].sum() + g["c_falta"].sum()) / dem,
                        "costo_total": g["c_sobra"].sum() + g["c_falta"].sum(),
                        "demanda": dem})
    return out.reset_index()


def elegir_p(curva: pd.DataFrame, metodo: str = "lgbm") -> int:
    """p de menor costo por vianda (si empatan, el más chico)."""
    c = curva[curva["metodo"] == metodo].sort_values(["costo_por_vianda", "p"])
    return int(c["p"].iloc[0])


# --------------------------------------------------------------------- figura
def fig_plan(curva: pd.DataFrame, p_elegido: int, refs, periodo: str, destino) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    estilos = {"lgbm": ("C0", "-", "LightGBM × participación"), "naive_estacional": ("0.5", "--", "Naive estacional")}
    for m, (col, ls, nombre) in estilos.items():
        d = curva[curva["metodo"] == m].sort_values("p")
        ax.plot(d["p"], d["costo_por_vianda"], ls, color=col, marker="o", ms=3, label=nombre)
    d = curva[curva["metodo"] == "lgbm"].set_index("p")
    ax.plot(p_elegido, d.loc[p_elegido, "costo_por_vianda"], "*", color="C3", ms=14,
            label=f"p elegido = {p_elegido}")
    for r in refs:
        ax.annotate(f"p{r}", (r, d.loc[r, "costo_por_vianda"]), textcoords="offset points", xytext=(-8, 6), fontsize=8)
    ax.set_xlabel("percentil p de los errores de las 12 semanas previas (colchón)")
    ax.set_ylabel("costo simulado por vianda demandada (UYU)")
    ax.set_title(f"Plan de compras semanal por segmento × categoría, backtest {periodo}", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------- correr
def correr() -> dict:
    cfg = cargar_config()
    p_cfg, pc, co = cfg["pronostico"], cfg["plan_compras"], cfg["costos"]
    cf, cs = pc["costo_faltante_vianda"], pc["costo_sobrante_vianda"]
    ps, refs, n_prev = list(pc["percentiles"]), list(pc["percentiles_referencia"]), pc["semanas_colchon"]
    # costos de la XL: sobrante = costo XL; faltante = margen XL (415 − 260 = 155); cf_xl = cf + 5
    pond = pc.get("ponderar_xl", False)
    cs_xl = co["vianda_xl"] if pond else None
    delta_xl = (co["precio_vianda_xl"] - co["vianda_xl"]) - (co["precio_vianda"] - co["vianda"])
    cf_xl = (lambda c: c + delta_xl) if pond else (lambda c: None)
    datos = jerarquico.cargar(cfg)
    fin_seg = {s: pd.Timestamp(p_cfg.get(f"fin_test_{s}", p_cfg["fin_test"])) for s in datos["segmentos"]}
    todos = {s: ev.origenes(datos["G"][f"Total/{s}"], p_cfg["semanas_test"] + n_prev, fin_seg[s])
             for s in datos["segmentos"]}
    test = {s: o[-p_cfg["semanas_test"]:] for s, o in todos.items()}
    for s in datos["segmentos"]:
        print(f"Fase 9, {s}: {len(todos[s])} orígenes ({todos[s][0]:%d/%m/%Y} a {todos[s][-1]:%d/%m/%Y}), "
              f"test desde {test[s][0]:%d/%m/%Y}")
    pred = backtest(datos, todos, cfg)
    sem = semanal(pred)
    primer = sem["segmento"].map({s: o[0] for s, o in test.items()})
    sem["fase"] = np.where(sem["origen"] >= primer, "test", "previa")

    pl = pd.concat([planes(sem[sem["segmento"] == s], test[s], METODOS, ps, n_prev) for s in datos["segmentos"]],
                   ignore_index=True)
    xl = pd.read_csv(ruta("processed", cfg) / "xl_semanal.csv", parse_dates=["semana_ini"])
    pl = agregar_xl(pl, xl, n_prev)
    curva = simular(pl, cf, cs, cs_xl=cs_xl, cf_xl=cf_xl(cf))
    p_star = elegir_p(curva)
    # referencia: mismo backtest con los costos fijos de antes (200 / 150), para ver si cambia p
    curva_fija = simular(pl, cf, cs)
    p_fijo = elegir_p(curva_fija)
    res = curva[curva["p"].isin([p_star, *refs])].assign(elegido=lambda d: (d["p"] == p_star) & (d["metodo"] == "lgbm"))
    # sensibilidad al costo de faltante: con cada c_f se vuelve a elegir p
    sens = []
    for cf_i in pc["sensibilidad_costo_faltante"]:
        c_i = simular(pl, cf_i, cs, cs_xl=cs_xl, cf_xl=cf_xl(cf_i))
        p_i = elegir_p(c_i)
        sens.append(c_i[(c_i["metodo"] == "lgbm") & (c_i["p"] == p_i)].assign(costo_faltante=cf_i, costo_sobrante=cs))
    sens = pd.concat(sens, ignore_index=True)
    por_seg = simular(pl[pl["p"] == p_star], cf, cs, por=["segmento"], cs_xl=cs_xl, cf_xl=cf_xl(cf))

    # plan real: semana siguiente a la última semana completa; un segmento con datos más viejos
    # usaría su último origen (o_hist)
    o_fin = max(fin_seg.values())
    o_hist = {s: f for s, f in fin_seg.items() if f < o_fin}
    fut = semanal(pronosticar_origen(datos, o_fin, cfg, fut_externo=True, origen_hist=o_hist).assign(y=np.nan),
                  ["lgbm"])
    cols = {p_star: f"plan_p{p_star}", **{r: f"plan_p{r}" for r in refs}}
    fac = pd.concat([factores(semanas_previas(sem[sem["segmento"] == s], fin_seg[s], n_prev), "lgbm", list(cols))
                     for s in datos["segmentos"]], ignore_index=True)
    fut = fut.merge(fac, on="segmento")
    plan = fut[CLAVE].assign(pronostico=fut["lgbm"].round(1))
    for p, nombre in cols.items():
        plan[nombre] = np.ceil(fut["lgbm"] * fut[p]).astype(int)
    plan["origen_datos"] = plan["segmento"].map(lambda s: f"{min(fin_seg[s], o_fin):%d/%m/%Y}")
    dias = pd.Timestamp(o_fin) + pd.Timedelta(days=2), pd.Timestamp(o_fin) + pd.Timedelta(days=7)

    tablas, figs = ruta("tablas", cfg), ruta("figuras", cfg)
    periodos = {s: eda.periodo(pred.loc[(pred["segmento"] == s) & (pred["origen"] >= test[s][0]), "fecha"])
                for s in datos["segmentos"]}
    periodo = "; ".join(f"{s} {p}" for s, p in periodos.items())
    publicas = ["metodo", "p", "n", "cobertura", "sobrante_pct", "faltante_pct", "plan_sobre_demanda",
                "costo_por_vianda"]  # costo_total y demanda dependen de K: no se publican
    sem.to_csv(tablas / "plan_backtest_predicciones.csv", index=False)
    curva[publicas].round(4).to_csv(tablas / "plan_curva_costo.csv", index=False)
    curva_fija[publicas].round(4).to_csv(tablas / "plan_curva_costo_fijo.csv", index=False)
    res[[*publicas, "elegido"]].round(4).to_csv(tablas / "plan_simulacion.csv", index=False)
    por_seg[["segmento", *publicas]].round(4).to_csv(tablas / "plan_simulacion_segmento.csv", index=False)
    sens[["costo_faltante", "costo_sobrante", *publicas]].round(4).to_csv(tablas / "plan_sensibilidad_costo.csv",
                                                                         index=False)
    xl_prev = pl[["origen", "segmento", "prop_xl"]].drop_duplicates().sort_values(["segmento", "origen"])
    xl_prev.round(4).to_csv(tablas / "plan_prop_xl.csv", index=False)
    pd.DataFrame([{"p_elegido": p_star, "p_costos_fijos": p_fijo, "p_antes_18_11": 45, "ponderar_xl": pond,
                   "periodo_test": periodo}]).to_csv(tablas / "plan_p_elegido.csv", index=False)
    plan.to_csv(tablas / "plan_semana_siguiente.csv", index=False)
    fig_plan(curva, p_star, refs, periodo, figs / "12_plan_compras.png")
    try:  # porciones reales y costo total en UYU (privado)
        from vhp.anonymize import secretos
        k = secretos()[1]
        real = plan.copy()
        real["pronostico"] = (plan["pronostico"] / k).round(1)
        for c in cols.values():
            real[c] = np.ceil(plan[c] / k).astype(int)
        real.to_csv(ruta("interim", cfg) / "plan_semana_siguiente_real.csv", index=False)
        costo_real = res.assign(costo_total_uyu=res["costo_total"] / k, demanda_real=res["demanda"] / k)
        costo_real.round(2).to_csv(ruta("interim", cfg) / "plan_costo_real.csv", index=False)
        print("Costo total en UYU reales (privado):\n" + costo_real[["metodo", "p", "demanda_real", "costo_total_uyu"]]
              .round(0).to_string(index=False))
    except RuntimeError:
        print("Sin .env: no se genera el plan en porciones reales")

    print(f"Curva de costo, backtest {periodo} (costos ponderados por XL: {pond}):")
    print(curva[publicas].round(3).to_string(index=False))
    print(f"p elegido (lgbm) = {p_star} | con costos fijos 200/150 = {p_fijo} | antes (18/11) = 45")
    print("Proporción de XL usada (12 semanas previas):\n" + xl_prev.groupby("segmento")["prop_xl"]
          .agg(["min", "mean", "max"]).round(4).to_string())
    print("Por segmento (p elegido):\n" + por_seg[["segmento", *publicas]].round(3).to_string(index=False))
    print("Sensibilidad al costo de faltante:\n" + sens[["costo_faltante", "p", "cobertura", "sobrante_pct",
                                                        "faltante_pct", "costo_por_vianda"]].round(3).to_string(index=False))
    print(f"Plan semanal para {dias[0]:%d/%m/%Y}–{dias[1]:%d/%m/%Y} (porciones × K):")
    print(plan.to_string(index=False))
    return {"pred": pred, "sem": sem, "curva": curva, "res": res, "sens": sens, "plan": plan, "p_elegido": p_star,
            "p_fijo": p_fijo, "por_segmento": por_seg}
