"""Exporta los resultados públicos de vhp-forecast a public/data/presentacion.json.

Uso (desde vhp-presentacion/):
    npm run datos
    # equivale a: ../vhp-forecast/.venv/bin/python scripts/exportar_datos.py [--repo RUTA]

Lee SOLO archivos públicos (versionados) del repo:
  - reports/tables/*.csv  (salvo calidad_datos.csv: tiene conteos reales y no se sube)
  - reports/decisiones.yaml, reports/resultados.md, reports/figures/*.png
  - data/processed/*.csv  (agregados × K o índices base 100)
  - config/config.yaml    (parámetros públicos: semanas de test, costos estimados)
Nunca toca data/raw_private, data/interim, data/control ni .env.

Al final compara los números clave del JSON contra reports/resultados.md y termina con
error (código 1) si alguno no coincide. Así ningún número de la presentación queda
desfasado del informe.
"""
from __future__ import annotations

import argparse
import warnings
import json
import math
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

AQUI = Path(__file__).resolve().parent.parent
REPO_DEF = AQUI.parent / "vhp-forecast"
PROHIBIDOS = ("raw_private", "interim", "control", ".env", "calidad_datos")

NOMBRES_MODELO = {
    "naive": "Naive",
    "naive_estacional": "Naive estacional",
    "media_movil_4sem": "Media móvil 4 sem.",
    "ets": "ETS",
    "sarima": "SARIMA",
    "lgbm_directo": "LightGBM directo",
    "mlp": "MLP",
}
NOMBRES_EVENTO = {
    "agencia_meta": "Agencia de Marketing",
    "influencer": "Influencer",
    "postres_web": "Postres en la web",
    "panes_web": "Panes en la web",
    "suba_precio": "Suba de precio",
    "suba_precio_13sem": "Suba de precio (13 sem.)",
    "meta_reparto": "Meta: reparto (05/09)",
    "baja_pauta": "Baja de pauta (nov.)",
}
NOMBRES_SERIE_EVENTO = {
    "viandas_particulares": "viandas de particulares",
    "tasa_postre_particulares": "postres por vianda",
    "tasa_pan_particulares": "panes por vianda",
    "tasa_extras_particulares": "extras por vianda",
    "clientes_nuevos_particulares": "clientes nuevos",
    "pedidos_recurrentes_particulares": "pedidos de recurrentes",
}
METODOS_MIX = {"media_4sem": "Media 4 semanas", "multinomial": "Multinomial", "multinomial_clima": "Multinomial + clima", "lgbm_directo": "LightGBM (segmento)"}

# Limitaciones: no hay tabla. Texto tomado de CLAUDE.md, resultados.md y decisiones.yaml del repo.
LIMITACIONES = [
    {"titulo": "Sin hora de creación del pedido", "texto": "Solo sabemos el día de entrega, no cuándo se pidió.", "implica": "El pronóstico no usa los pedidos ya confirmados.", "fuente": "decisiones.yaml (fecha_entrega)"},
    {"titulo": "Faltan pedidos fuera del sistema", "texto": "WhatsApp, teléfono y carga manual no figuran.", "implica": "La demanda real es algo mayor.", "fuente": "decisiones.yaml (periodo)"},
    {"titulo": "Meta: sin variación ni origen del pedido", "texto": "El gasto casi no varía (CV 2,8 %) y no hay UTM.", "implica": "No sabemos cuánto rinde Meta ni qué anuncio funciona.", "fuente": "decisiones.yaml (meta_no_identificado, eventos_meta_nuevos)"},
    {"titulo": "Suba de precio, preliminar", "texto": "Solo 8 semanas después y 4 placebos.", "implica": "El p-placebo no baja de 0,2: aún no se distingue de cero.", "fuente": "decisiones.yaml (suba_precio_preliminar)"},
    {"titulo": "Recetario incompleto", "texto": "26 platos (13,7 %) sin receta; XL estimadas como normal × 1,30.", "implica": "La lista de compras queda corta en esos platos.", "fuente": "decisiones.yaml (platos_a_ingredientes, xl_sin_receta)"},
    {"titulo": "Clima observado y p optimista", "texto": "Se usa el clima real, y p se elige en las mismas semanas que se evalúa.", "implica": "Sin leakage, pero el costo es algo optimista.", "fuente": "decisiones.yaml (clima_total, plan_colchon)"},
]
FUTURO = [
    "Pedir al sistema la fecha y hora de creación del pedido → nowcasting con lo ya confirmado.",
    "Variar el gasto en Meta a propósito (semanas alternas) y registrar el origen del pedido (UTM).",
    "Volver a medir la baja de pauta y la suba de precio con más semanas; completar las recetas que faltan.",
]
# Las 6 decisiones de la diapositiva de cierre (ids de decisiones.yaml).
# Ordenadas: primero las de negocio, después las técnicas.
DECISIONES_CLAVE = ["dias_habiles", "segmentos", "costo_faltante", "walk_forward", "modelo_total", "platos_a_ingredientes"]


# ------------------------------------------------------------------ utilidades
def r(x, nd=4):
    """Redondea y convierte NaN a None (JSON válido)."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return x
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, nd)


def es(x: float, d: int) -> str:
    """Número con coma decimal, como en resultados.md."""
    return f"{x:.{d}f}".replace(".", ",").replace("-", "−")


def corta(s: str) -> str:
    return pd.Timestamp(s).strftime("%d/%m")


def larga(s) -> str:
    return pd.Timestamp(s).strftime("%d/%m/%Y")


class Fuentes:
    """Lector que se niega a abrir rutas privadas."""

    def __init__(self, repo: Path):
        self.repo = repo
        self.leidos: list[str] = []

    def ruta(self, rel: str) -> Path:
        if any(p in rel for p in PROHIBIDOS):
            raise SystemExit(f"Ruta privada, no se lee: {rel}")
        p = self.repo / rel
        if not p.exists():
            raise SystemExit(f"Falta {rel} en el repo: no se inventa el número. Avisale a Lucía.")
        self.leidos.append(rel)
        return p

    def csv(self, rel: str, **kw) -> pd.DataFrame:
        return pd.read_csv(self.ruta(rel), **kw)

    def texto(self, rel: str) -> str:
        return self.ruta(rel).read_text(encoding="utf-8")


def buscar(patron: str, texto: str, que: str) -> re.Match:
    m = re.search(patron, texto)
    if not m:
        raise SystemExit(f"No encontré «{que}» en el texto fuente; no se inventa.")
    return m


# Fragmentos de código para las diapositivas "En código": (id, archivo, constantes, funciones).
# Se extraen tal cual del repo con ast (sin docstrings), así nunca se desfasan de src/.
FRAGMENTOS = [
    ("baselines", "src/vhp/models/baselines.py", [], ["_naive", "_naive_estacional", "_media_movil_estacional"]),
    ("sarima", "src/vhp/models/sarimax.py", ["GRILLA"], ["ajustar"]),
    ("lgbm", "src/vhp/models/lgbm.py", [], ["_rasgos_lags", "directo"]),
    ("walk_forward", "src/vhp/evaluate.py", [], ["partir", "escala_mase"]),
    ("intervalo", "src/vhp/evaluate.py", [], ["intervalos"]),
    ("plan", "src/vhp/decision.py", [], ["factores", "elegir_p"]),
    ("modelo_final", "src/vhp/decision.py", [], ["pronosticar_origen"]),
]
# Abreviaturas explícitas (marcadas con «...» en la diapositiva): (id, línea que empieza, cuántas, reemplazo)
ABREVIAR = {
    "modelo_final": [('"origen": pd.Timestamp(origen)', 4,
                      '...}))  # columnas: origen, fecha, segmento, categoría, lgbm, naive_estacional, y')],
}


def extraer_codigo(F: "Fuentes") -> dict:
    """Devuelve {id: {archivo, codigo}} con las funciones pedidas, sin docstrings."""
    import ast
    out = {}
    for fid, rel, consts, funcs in FRAGMENTOS:
        src = F.texto(rel)
        lineas = src.splitlines()
        arbol = ast.parse(src)
        bloques = []
        for nodo in arbol.body:
            if isinstance(nodo, ast.Assign) and any(getattr(t, "id", None) in consts for t in nodo.targets):
                bloques.append(lineas[nodo.lineno - 1: nodo.end_lineno])
            if isinstance(nodo, ast.FunctionDef) and nodo.name in funcs:
                cuerpo = lineas[nodo.lineno - 1: nodo.end_lineno]
                primero = nodo.body[0]
                if isinstance(primero, ast.Expr) and isinstance(getattr(primero, "value", None), ast.Constant) and isinstance(primero.value.value, str):
                    a, b = primero.lineno - nodo.lineno, primero.end_lineno - nodo.lineno
                    cuerpo = cuerpo[:a] + cuerpo[b + 1:]
                bloques.append(cuerpo)
        faltan = set(funcs) - {n.name for n in arbol.body if isinstance(n, ast.FunctionDef)}
        if faltan:
            raise SystemExit(f"No están en {rel}: {faltan}")
        codigo = "\n\n".join("\n".join(b) for b in bloques)
        for inicio, n, reemplazo in ABREVIAR.get(fid, []):
            ls = codigo.split("\n")
            k = next((i for i, l in enumerate(ls) if inicio in l), None)
            if k is None:
                raise SystemExit(f"No encontré «{inicio}» en {rel} para abreviar")
            sangria = ls[k][: len(ls[k]) - len(ls[k].lstrip())]
            ls[k: k + n] = [sangria + reemplazo]
            codigo = "\n".join(ls)
        out[fid] = {"archivo": rel, "codigo": codigo}
    return out


# ------------------------------------------------------------------ exportación
def construir(F: Fuentes) -> dict:
    T, P = "reports/tables/", "data/processed/"
    cfg = yaml.safe_load(F.texto("config/config.yaml"))
    dec = yaml.safe_load(F.texto("reports/decisiones.yaml"))["decisiones"]
    dec_id = {d["id"]: d for d in dec}

    # ---- serie diaria de viandas por segmento (× K)
    vd = F.csv(P + "ventas_diarias.csv", parse_dates=["fecha"])
    vv = vd[vd["tipo_producto"] == "Vianda"]
    serie = vv.pivot_table(index="fecha", columns="segmento", values="unidades", aggfunc="sum").fillna(0)
    cal = F.csv(P + "calendario.csv", parse_dates=["fecha"]).set_index("fecha")
    serie = cal[["feriado_laborable", "verano", "dia_semana"]].join(serie, how="left").fillna(0)
    # Si empresas no tuviera datos un día: e = null (no es cero). Hoy llega al final de la serie.
    fin_emp = pd.Timestamp(vv.loc[vv.segmento == "empresas", "fecha"].max())
    serie_out = [
        {"f": d.strftime("%Y-%m-%d"), "p": int(x["particulares"]), "e": int(x["empresas"]) if d <= fin_emp else None,
         "fer": int(x["feriado_laborable"]), "ver": int(x["verano"])}
        for d, x in serie.iterrows()
    ]
    comun = serie[serie.index <= fin_emp]  # período con los dos segmentos (Total)
    tot_p, tot_e = comun["particulares"].sum(), comun["empresas"].sum()
    categorias = sorted(vv["categoria"].dropna().unique().tolist())
    periodo_s = int(cal["dia_semana"].nunique())  # días hábiles por semana = período estacional

    # ---- el dataset: de dónde sale cada cosa (solo archivos públicos + código de src/)
    load_src = F.texto("src/vhp/load.py")
    columnas_export = re.findall(r'^\s+"([^"]+)": "\w+",$', load_src.split("COLUMNAS_USADAS", 1)[1].split("}", 1)[0], flags=re.M)
    if not columnas_export:
        raise SystemExit("No encontré COLUMNAS_USADAS en load.py")
    cats_yaml = yaml.safe_load(F.texto("config/categorias.yaml"))["categorias"]
    clima = F.csv("data/external/clima_montevideo.csv", parse_dates=["fecha"])
    fer = F.csv("data/external/feriados_uy.csv", parse_dates=["fecha"])
    fer = fer[(fer.fecha >= serie.index.min()) & (fer.fecha <= serie.index.max())]
    meta_sem = F.csv(P + "meta_ads_semanal_indice.csv")
    tests = F.ruta("tests")
    n_tests = sum(len(re.findall(r"^def test_", p.read_text(encoding="utf-8"), flags=re.M)) for p in tests.glob("test_*.py"))
    muestra = vv.sort_values(["fecha", "segmento", "categoria"]).head(4)
    # ejemplo de la serie ya cruzada: tartas de empresas en la semana de carnaval 2026
    dias_cruce = pd.to_datetime(["2026-02-12", "2026-02-13", "2026-02-16", "2026-02-18"])
    tar = vv[(vv.segmento == "empresas") & (vv.categoria == "tartas y huevo")].groupby("fecha")["unidades"].sum()
    cl = clima.set_index("fecha")
    ms = meta_sem.assign(ini=pd.to_datetime(meta_sem.semana_ini), fin=pd.to_datetime(meta_sem.semana_fin))
    def gasto(f):
        w = ms[(ms.ini <= f) & (ms.fin >= f)]
        return round(float(w.gasto_meta_total.iloc[0]), 1) if len(w) else None
    def evento(f):
        r = cal.loc[f]
        return "carnaval" if r.carnaval else "turismo" if r.turismo else "feriado" if r.feriado_laborable else "víspera" if r.vispera_cierre else "—"
    cruce = [{"f": f.strftime("%Y-%m-%d"), "u": int(tar.get(f, 0)), "ev": evento(f),
              "tmax": round(float(cl.loc[f, "temperature_2m_max"]), 1), "lluvia": round(float(cl.loc[f, "precipitation_sum"]), 1),
              "meta": gasto(f)} for f in dias_cruce]
    dataset = {
        "columnas": columnas_export,
        "nArchivos": int(vd.assign(mes=vd.fecha.dt.to_period("M")).groupby("segmento")["mes"].nunique().sum()),
        "tipos": sorted(vd["tipo_producto"].unique().tolist()),
        "nPlatos": int(sum(len(v) for v in cats_yaml.values())),
        "filasProcesadas": int(len(vd)),
        "cruce": cruce,
        "muestra": [{"f": x.fecha.strftime("%Y-%m-%d"), "seg": x.segmento, "cat": x.categoria, "u": int(x.unidades)} for x in muestra.itertuples()],
        "climaVars": [c for c in clima.columns if c != "fecha"], "climaDias": int(len(clima)),
        "feriadosNoLab": int((fer.tipo == "no_laborable").sum()), "feriadosLab": int((fer.tipo == "laborable").sum()),
        "calVars": [c for c in cal.columns if c != "dia_semana"],
        "semanasMeta": int(len(meta_sem)),
        "nTests": n_tests,
    }

    # ---- STL y ACF/PACF del Total de viandas: mismo método que src/vhp/eda.py
    #      (STL período 6 robusta; ACF y PACF "ywm" con 36 rezagos), recalculado para
    #      dibujarlo con la paleta de la marca (las figuras PNG del repo son azules).
    from statsmodels.tsa.seasonal import STL
    from statsmodels.tsa.stattools import acf, pacf
    tot = comun["particulares"] + comun["empresas"]
    stl = STL(tot.to_numpy(), period=periodo_s, robust=True).fit()
    stl_out = [{"f": d.strftime("%Y-%m-%d"), "y": r(v, 0), "t": r(a, 1), "s": r(b, 1), "r": r(c, 1)}
               for d, v, a, b, c in zip(tot.index, tot, stl.trend, stl.seasonal, stl.resid)]
    dif = (tot - tot.shift(periodo_s)).dropna()
    autocorr = {
        "nivel": {"acf": [r(v, 3) for v in acf(tot, nlags=36)], "pacf": [r(v, 3) for v in pacf(tot, nlags=36, method="ywm")], "n": int(len(tot))},
        "dif": {"acf": [r(v, 3) for v in acf(dif, nlags=36)], "pacf": [r(v, 3) for v in pacf(dif, nlags=36, method="ywm")], "n": int(len(dif))},
    }

    # ---- EDA
    ds = F.csv(T + "eda_dia_semana.csv", index_col=0)
    dia_semana = [{"dia": d, "total": r(x.Total, 3), "particulares": r(x.Particulares, 3), "empresas": r(x.Empresas, 3)} for d, x in ds.iterrows()]
    ec = F.csv(T + "eda_efectos_calendario.csv")
    efectos = {f"{x.serie}|{x.variable}": {"ef": r(x.efecto_pct, 2), "lo": r(x.ic95_inf_pct, 2), "hi": r(x.ic95_sup_pct, 2), "p": r(x.p_valor, 4), "dias": int(x.dias)} for x in ec.itertuples()}
    est = F.csv(T + "eda_estacionariedad.csv")
    estacionariedad = [{"t": x.transformacion, "n": int(x.n), "p": float(f"{x.adf_p:.3g}"), "c": x.conclusion} for x in est.itertuples()]
    mt_rho = F.csv(T + "eda_mix_temperatura.csv")
    rho = [{"cat": x.categoria, "rho": r(x.rho_spearman, 2), "p": r(x.p_valor, 3), "part": r(x.participacion_media_pct, 1)} for x in mt_rho.itertuples()]

    # ---- total
    met = F.csv(T + "backtest_total_metricas.csv").sort_values("MASE")
    metricas = [{"id": x.modelo, "nombre": NOMBRES_MODELO[x.modelo], "n": int(x.n), "mae": r(x.MAE, 1), "mase": r(x.MASE), "wape": r(x.WAPE), "cob": r(x.cobertura_80)} for x in met.itertuples()]
    dm = F.csv(T + "backtest_total_dm.csv")
    dm_out = [{"m1": x.modelo_1, "m2": x.modelo_2, "n1": NOMBRES_MODELO[x.modelo_1], "n2": NOMBRES_MODELO[x.modelo_2], "dm": r(x.DM, 2), "p": r(x.p_valor, 3), "mejor": x.mejor} for x in dm.itertuples()]
    lb = F.csv(T + "backtest_total_ljung_box.csv")
    lb_out = [{"modelo": x.modelo, "rezago": int(x.rezago), "stat": r(x.lb_stat, 2), "p": r(x.lb_pvalue, 3)} for x in lb.itertuples()]
    bp = F.csv(T + "backtest_total_predicciones.csv")
    pred = {}
    for mod in ["lgbm_directo", "media_movil_4sem", "naive_estacional", "ets"]:
        g = bp[bp.modelo == mod].sort_values("fecha")
        pred[mod] = [{"f": x.fecha, "o": x.origen, "h": int(x.h), "y": r(x.y, 1), "lo": r(x._6, 1), "m": r(x._7, 1), "hi": r(x._8, 1)} for x in g.itertuples()]
    fechas_bt = sorted(bp.fecha.unique())
    origenes = sorted(bp.origen.unique())
    horizonte = int(bp.h.max())
    bt_periodo = f"{corta(fechas_bt[0])}–{larga(fechas_bt[-1])}"

    # Ejemplo real para las fórmulas: el primer día del backtest.
    dia0 = fechas_bt[0]
    ej = {}
    for mod in ["naive", "naive_estacional", "media_movil_4sem", "lgbm_directo"]:
        x = bp[(bp.modelo == mod) & (bp.fecha == dia0)].iloc[0]
        ej[mod] = {"y": r(x.y, 0), "yhat": r(x["q0.5"], 1), "lo": r(x["q0.1"], 1), "hi": r(x["q0.9"], 1), "escala": r(x.escala_mase, 1)}
    # Semana del primer origen (6 días) de LightGBM: MAE y WAPE de una semana, a mano.
    s0 = bp[(bp.modelo == "lgbm_directo") & (bp.origen == origenes[0])].sort_values("fecha")
    err = (s0.y - s0["q0.5"]).abs()
    ej_semana = {
        "dias": [{"f": x.fecha, "y": r(x.y, 0), "yhat": r(x["q0.5"], 0), "lo": r(x["q0.1"], 0), "hi": r(x["q0.9"], 0)} for _, x in s0.iterrows()],
        "mae": r(err.mean(), 1), "wape": r(err.sum() / s0.y.sum(), 4), "escala": r(s0.escala_mase.iloc[0], 1),
        "mase": r(err.mean() / s0.escala_mase.iloc[0], 3),
        "cubiertos": int(((s0.y >= s0["q0.1"]) & (s0.y <= s0["q0.9"])).sum()),
    }

    # SARIMA del último origen: viene escrito en decisiones.yaml (no hay tabla).
    m = buscar(r"Al último origen quedó (\(\d,\d,\d\)\(\d,\d,\d\)\[\d+\])", dec_id["sarima_ordenes"]["decision"], "orden SARIMA del último origen")
    sarima_ultimo = m.group(1)

    # ---- mix y clima
    mt = F.csv(T + "mix_efecto_temperatura.csv")
    mix_temp = [{"seg": x.segmento, "cat": x.categoria, "frio": r(x.pct_frio, 2), "calor": r(x.pct_calor, 2), "d": r(x.calor_menos_frio_pp, 2), "lo": r(x.ic95_inf_pp, 2), "hi": r(x.ic95_sup_pp, 2)} for x in mt.itertuples()]
    mtemp = buscar(r"calor \(([\d,]+) °C\) contra frío \(([\d,]+) °C\)", dec_id["clima_mix"]["porque"], "temperaturas de calor y frío")
    temps = {"calor": float(mtemp.group(1).replace(",", ".")), "frio": float(mtemp.group(2).replace(",", "."))}
    mp = F.csv(T + "mix_metricas_participacion.csv")
    mix_part = [{"seg": x.segmento, "id": x.metodo, "metodo": METODOS_MIX[x.metodo], "logloss": r(x.logloss_por_vianda, 4), "mae_pp": r(x.error_abs_medio_pp, 2)} for x in mp.itertuples()]
    mu = F.csv(T + "mix_metricas_unidades.csv")
    mix_unid = [{"nivel": x.nivel, "id": x.modelo, "metodo": METODOS_MIX[x.modelo], "mase": r(x.MASE, 3), "wape": r(x.WAPE, 3), "cob": r(x.cobertura_80, 3)} for x in mu.itertuples()]

    # ---- eventos
    ee = F.csv(T + "eventos_efectos.csv")
    eventos = []
    for x in ee.itertuples():
        pct = x.metrica_placebo == "efecto_pct"
        eventos.append({
            "evento": x.evento, "nombre": NOMBRES_EVENTO[x.evento], "serie": x.serie, "serieNombre": NOMBRES_SERIE_EVENTO[x.serie],
            "unidad": "pct" if pct else "tasa", "desde": x.desde, "hasta": x.hasta, "dias": int(x.dias),
            "ef": r(x.efecto_pct if pct else x.efecto, 4), "lo": r(x.pct_inf if pct else x.efecto_inf, 4), "hi": r(x.pct_sup if pct else x.efecto_sup, 4),
            "orden": x.orden, "nPlac": int(x.n_placebos), "sigPlac": int(x.placebos_significativos),
            "pPlac": r(x.p_placebo, 3), "emd": r(x.efecto_minimo_detectable, 4),
        })

    # ---- Meta Ads (índices, nunca montos)
    ma = F.csv(P + "meta_ads_semanal_indice.csv", parse_dates=["semana_ini"])
    ps = F.csv(P + "particulares_semanal.csv", parse_dates=["semana_ini"])
    reg = F.csv(T + "ads_regresion.csv")
    r_desde, r_hasta = pd.Timestamp(reg.desde.iloc[0]), pd.Timestamp(reg.hasta.iloc[0])
    w = ma.merge(ps, on="semana_ini", how="left")
    w = w[(w.semana_ini >= r_desde) & (w.semana_ini <= r_hasta)].copy()
    base = w[w.semana_ini.dt.month != 1]
    w["g"] = 100 * w.gasto_meta_total / base.gasto_meta_total.mean()
    w["c"] = 100 * w.clientes_nuevos_particulares / base.clientes_nuevos_particulares.mean()
    w["k"] = 100 * w.clics / base.clics.mean()
    var = F.csv(T + "ads_variacion_gasto.csv")
    grs = F.csv(T + "ads_granger.csv")
    gr = grs[grs.causa == "log_gasto_campania"].iloc[0]
    grk = grs[grs.causa == "log_clics"].iloc[0]
    rk = reg[reg.termino == "log_clics"].iloc[0]
    rc = reg[reg.termino == "log_gasto_campania"].iloc[0]
    cv_clics = var[var.serie == "clics"].iloc[0]
    el = reg[reg.termino == "log_gasto_total"].iloc[0]
    cv_camp = var[var.serie == "gasto_campania_viandas"].iloc[0]
    escalon = var[(var.serie == "gasto_meta_total") & (var.desde == var.desde.min())].iloc[0]
    ads = {
        "semanal": [{"s": x.semana_ini.strftime("%Y-%m-%d"), "g": r(x.g, 1), "c": r(x.c, 1), "k": r(x.k, 1), "ver": int(x.semana_ini.month == 1)} for x in w.itertuples()],
        "clics": {"coef": r(rk.coef, 2), "lo": r(rk.ic95_inf, 2), "hi": r(rk.ic95_sup, 2), "p": r(rk.p_valor, 3), "r2": r(rk.r2, 2), "semanas": int(rk.semanas), "desde": rk.desde, "hasta": rk.hasta,
                  "cv": r(cv_clics.cv_pct, 1), "grangerF": r(grk.F, 2), "grangerP": r(grk.p_valor, 3)},
        "campania": {"coef": r(rc.coef, 2), "lo": r(rc.ic95_inf, 2), "hi": r(rc.ic95_sup, 2), "p": r(rc.p_valor, 3), "semanas": int(rc.semanas)},
        "cv": r(cv_camp.cv_pct, 2), "cvDesde": cv_camp.desde, "cvHasta": cv_camp.hasta,
        "escalon": r(escalon.max_sobre_min, 1),
        "regresion": {"coef": r(el.coef, 2), "lo": r(el.ic95_inf, 2), "hi": r(el.ic95_sup, 2), "p": r(el.p_valor, 3), "semanas": int(el.semanas), "corr": r(el.corr_x_control, 3), "desde": el.desde, "hasta": el.hasta},
        "granger": {"F": r(gr.F, 2), "p": r(gr.p_valor, 3), "rezagos": int(gr.rezagos), "semanas": int(gr.semanas), "desde": gr.desde, "hasta": gr.hasta},
    }
    # Las semanas van de lunes a domingo: la última termina el domingo siguiente a su lunes.
    ads["semanaFin"] = (pd.Timestamp(ads["regresion"]["hasta"]) + pd.Timedelta(days=6)).strftime("%Y-%m-%d")

    # ---- plan
    cc = F.csv(T + "plan_curva_costo.csv")
    curva = [{"metodo": x.metodo, "p": int(x.p), "cob": r(x.cobertura, 4), "sob": r(x.sobrante_pct, 4), "fal": r(x.faltante_pct, 4), "costo": r(x.costo_por_vianda, 4)} for x in cc.itertuples()]
    sim = F.csv(T + "plan_simulacion.csv")
    simul = [{"metodo": x.metodo, "p": int(x.p), "cob": r(x.cobertura, 4), "sob": r(x.sobrante_pct, 4), "fal": r(x.faltante_pct, 4), "costo": r(x.costo_por_vianda, 4), "elegido": bool(x.elegido)} for x in sim.itertuples()]
    sens = F.csv(T + "plan_sensibilidad_costo.csv")
    sens_out = [{"faltante": int(x.costo_faltante), "p": int(x.p), "costo": r(x.costo_por_vianda, 4)} for x in sens.itertuples()]
    ss = F.csv(T + "plan_semana_siguiente.csv")
    elegido = next(s for s in simul if s["elegido"])
    semana = [{"seg": x.segmento, "cat": x.categoria, "pron": r(x.pronostico, 0), "plan": int(getattr(x, f"plan_p{elegido['p']}")), "p80": int(x.plan_p80), "p90": int(x.plan_p90)} for x in ss.itertuples()]
    # La semana planificada sigue a la última semana completa del backtest.
    lunes_plan = pd.Timestamp(fechas_bt[-1]) + pd.Timedelta(days=2)  # el sábado + 2 = lunes siguiente
    pinfo = F.csv(T + "plan_p_elegido.csv").iloc[0]
    xl = F.csv(T + "plan_prop_xl.csv").groupby("segmento")["prop_xl"].mean()
    hasta_seg = {x.segmento: x.origen_datos for x in ss.itertuples()}
    cr = F.csv(T + "compras_resumen.csv").iloc[0]
    cfam = F.csv(T + "compras_familia_indice.csv")
    compras = {
        "semana": cr.semana, "ingredientes": int(cr.ingredientes), "proveedores": int(cr.proveedores),
        "sinReceta12": r(cr.pct_viandas_sin_receta_12sem, 1), "sinRecetaSemana": r(cr.pct_viandas_sin_receta_semana, 1),
        "platosSinReceta": int(cr.platos_sin_receta_12sem),
        "ratioPlan": r(cr[f"kg_plan_p{elegido['p']}_sobre_pronostico"], 3), "ratioP90": r(cr["kg_plan_p90_sobre_pronostico"], 3),
        "familias": [{"familia": x.familia, "pct": r(x.pct_kg, 1), "unid": int(x.ingredientes_en_unidades)} for x in cfam.itertuples()],
        "gramosGuarnicion": int(cfg["recetario"]["gramos_guarnicion"]), "factorXL": r(cfg["recetario"]["factor_xl"], 2),
    }

    # ---- figuras: se copian (solo PNG del repo)
    figs = sorted(p.name for p in F.ruta("reports/figures").glob("*.png"))
    dest = AQUI / "public" / "figuras"
    dest.mkdir(parents=True, exist_ok=True)
    for f in figs:
        shutil.copy2(F.repo / "reports" / "figures" / f, dest / f)

    return {
        "meta": {
            "titulo": "Del pedido al plato",
            "subtitulo": "Pronóstico de la demanda de Viandas Hotel del Prado. Efecto de eventos y de la pauta en Meta Ads. Plan de compras.",
            "desde": serie.index.min().strftime("%Y-%m-%d"), "hasta": serie.index.max().strftime("%Y-%m-%d"),
            "datosPeriodo": f"{larga(comun.index.min())}–{larga(comun.index.max())}",
            "diasHabiles": int(len(comun)), "periodo": periodo_s, "horizonte": horizonte,
            "btDesde": fechas_bt[0], "btHasta": fechas_bt[-1], "btPeriodo": bt_periodo, "origenes": origenes,
            "nOrigenes": len(origenes), "diasBacktest": int(met.n.iloc[0]),
            "semanasIntervalo": int(cfg["pronostico"]["semanas_intervalo"]),
            "costos": {"sobrante": int(cfg["plan_compras"]["costo_sobrante_vianda"]), "faltante": int(cfg["plan_compras"]["costo_faltante_vianda"]),
                       "sobranteXL": int(cfg["costos"]["vianda_xl"]),
                       "faltanteXL": int(cfg["costos"]["precio_vianda_xl"] - cfg["costos"]["vianda_xl"])},
            "finEmpresas": fin_emp.strftime("%Y-%m-%d"),
            "hastaParticulares": serie.index.max().strftime("%Y-%m-%d"),
            "datosPeriodoPart": f"{larga(serie.index.min())}–{larga(serie.index.max())}",
            "diasHabilesPart": int(len(serie)),
            "percentiles": cfg["plan_compras"]["percentiles"],
            "categorias": categorias, "nCategorias": len(categorias),
            "partParticulares": r(tot_p / (tot_p + tot_e), 4),
            "logo": (AQUI / "public" / "marca" / "logo-tinta.png").exists(),
            "diaIncompleto": pd.to_datetime(buscar(r"(\d\d/\d\d/\d{4})", dec_id["lunes_17_08"]["titulo"], "día incompleto").group(1), dayfirst=True).strftime("%Y-%m-%d"),
            "variablesModelo": buscar(r"usan las mismas variables: ([^.]+)", dec_id["modelos_total"]["decision"], "variables de LightGBM").group(1),
            "semanaPlan": f"{lunes_plan:%d/%m}–{(lunes_plan + pd.Timedelta(days=5)):%d/%m/%Y}",
        },
        "dataset": dataset,
        "serie": serie_out,
        "eda": {"stl": stl_out, "autocorr": autocorr, "diaSemana": dia_semana, "efectos": efectos, "estacionariedad": estacionariedad, "rho": rho},
        "total": {"metricas": metricas, "dm": dm_out, "ljungBox": lb_out, "pred": pred, "sarimaUltimo": sarima_ultimo,
                  "ejemplo": {"fecha": dia0, "modelos": ej, "semana": ej_semana}},
        "mix": {"temperatura": mix_temp, "temps": temps, "participacion": mix_part, "unidades": mix_unid},
        "eventos": eventos,
        "ads": ads,
        "plan": {"curva": curva, "simulacion": simul, "sensibilidad": sens_out, "semana": semana, "pElegido": elegido["p"], "elegido": elegido,
                 "pCostosFijos": int(pinfo.p_costos_fijos), "pAntes": int(pinfo.p_antes_18_11), "periodo": pinfo.periodo_test,
                 "xl": {k: r(v, 4) for k, v in xl.items()}, "hasta": hasta_seg},
        "compras": compras,
        "decisiones": [dec_id[i] for i in DECISIONES_CLAVE],
        "limitaciones": LIMITACIONES,
        "futuro": FUTURO,
        "figuras": figs,
        "codigo": extraer_codigo(F),
        "fuentes": sorted(set(F.leidos)),
    }


# ------------------------------------------------------------------ chequeo contra resultados.md
def chequear(out: dict, md: str) -> list[str]:
    """Devuelve la lista de diferencias entre el JSON y resultados.md (vacía = todo coincide)."""
    fallas: list[str] = []

    def esta(fragmento: str, que: str):
        if fragmento not in md:
            fallas.append(f"{que}: «{fragmento}» no aparece en resultados.md")

    me = out["meta"]
    esta(f"({me['diasHabiles']} días hábiles", "días hábiles")
    esta(me["datosPeriodo"].replace("–", "–"), "período de datos")
    esta(f"{larga(me['btDesde'])}–{larga(me['btHasta'])}", "período del backtest")
    esta(f"({me['nOrigenes']} orígenes", "orígenes")

    for m in out["total"]["metricas"]:
        fila = f"| {m['nombre'].replace('4 sem.', '4 semanas')} | {es(m['mase'], 3)} | {es(m['wape'] * 100, 1)} % | {round(m['cob'] * 100)} % |"
        esta(fila, f"métricas de {m['id']}")
    for d in out["total"]["dm"]:
        n1, n2 = (n.replace("4 sem.", "4 semanas") for n in (d["n1"], d["n2"]))
        esta(f"| {n1} | {n2} | {es(d['dm'], 2)} | {es(d['p'], 3)} |", f"DM {d['m1']}–{d['m2']}")

    adf = out["eda"]["estacionariedad"][0]
    esta(f"ADF p = {es(adf['p'], 2)}", "ADF en nivel")

    for x in out["mix"]["participacion"]:
        esta(f"| {x['seg']} | {x['id']} | {es(x['logloss'], 4)} |", f"log loss {x['seg']} {x['id']}")
    for x in out["mix"]["unidades"]:
        esta(f"| {x['nivel']} | {x['id']} | {es(x['mase'], 3)} |", f"MASE mix {x['id']}")
    carne = next(x for x in out["mix"]["temperatura"] if x["seg"] == "empresas" and x["cat"] == "carne vacuna")
    esta(f"{es(-carne['d'], 1)} pp en empresas [{es(carne['lo'], 1)}; {es(carne['hi'], 1)}]", "calor vs frío carne")

    for e in out["eventos"]:
        if e["unidad"] == "pct":
            txt = f"{'+' if e['ef'] >= 0 else '−'}{abs(round(e['ef']))} % [{'+' if e['lo'] >= 0 else '−'}{abs(round(e['lo']))}; {'+' if e['hi'] >= 0 else '−'}{abs(round(e['hi']))}]"
        else:
            sg = lambda v: ("+" if v >= 0 else "−") + es(abs(v), 3)
            txt = f"{sg(e['ef'])} [{sg(e['lo'])}; {sg(e['hi'])}] por vianda"
        esta(f"{txt} | {e['orden']} | {e['sigPlac']} de {e['nPlac']} |", f"evento {e['evento']} / {e['serie']}")

    a = out["ads"]
    esta(f"CV {es(a['cv'], 1)} %", "CV del gasto")
    esta(f"×{es(a['escalon'], 1)}", "escalón del gasto")
    sg2 = lambda v: ("+" if v >= 0 else "−") + es(abs(v), 2)
    rg = a["regresion"]
    esta(f"elasticidad {sg2(rg['coef'])} [{sg2(rg['lo'])}; {sg2(rg['hi'])}], p = {es(rg['p'], 3)}", "elasticidad gasto total")
    k = a["clics"]
    esta(f"elasticidad {sg2(k['coef'])} [{sg2(k['lo'])}; {sg2(k['hi'])}], p = {es(k['p'], 3)}", "elasticidad clics")
    esta(f"clics → clientes nuevos F = {es(k['grangerF'], 2)}, p = {es(k['grangerP'], 3)}", "Granger clics")
    esta(f"F = {es(a['granger']['F'], 2)}, p = {es(a['granger']['p'], 3)}", "Granger")

    p = out["plan"]
    esta(f"p elegido = {p['pElegido']} (antes: {p['pAntes']}", "p elegido")
    for s in p["simulacion"]:
        nom = "LightGBM × participación" if s["metodo"] == "lgbm" else "Naive estacional"
        esta(f"| {nom} | {s['p']}{' (elegido)' if s['elegido'] else ''} | {es(s['cob'] * 100, 1)} % | {es(s['sob'], 1)} % | {es(s['fal'], 1)} % | {es(s['costo'], 1)} |", f"simulación {s['metodo']} p{s['p']}")
    for s in p["sensibilidad"]:
        esta(f"| ${s['faltante']} | {s['p']} |", f"sensibilidad {s['faltante']}")
    for s in p["semana"]:
        esta(f"| {s['seg']} | {s['cat']} | {round(s['pron'])} | {s['plan']} | {s['p80']} | {s['p90']} |", f"plan {s['seg']} {s['cat']}")
    esta(f"semana {me['semanaPlan']}", "semana del plan")
    c = out["compras"]
    esta(f"{c['ingredientes']} ingredientes de {c['proveedores']} proveedores", "ingredientes")
    esta(f"{c['platosSinReceta']} platos, {es(c['sinReceta12'], 1)} %", "platos sin receta")
    for f in c["familias"]:
        esta(f"| {f['familia']} | {es(f['pct'], 1)} |", f"familia {f['familia']}")
    return fallas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=REPO_DEF)
    ap.add_argument("--salida", type=Path, default=AQUI / "public" / "data" / "presentacion.json")
    a = ap.parse_args()
    F = Fuentes(a.repo.resolve())
    out = construir(F)

    fallas = chequear(out, F.texto("reports/resultados.md"))
    if fallas:
        print("ERROR: el JSON no coincide con reports/resultados.md:", file=sys.stderr)
        for f in fallas:
            print("  -", f, file=sys.stderr)
        sys.exit(1)

    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"OK → {a.salida.relative_to(AQUI)} ({a.salida.stat().st_size / 1024:.0f} KB); "
          f"{len(out['figuras'])} figuras copiadas; chequeo contra resultados.md sin diferencias.")
    print("Archivos leídos:", ", ".join(out["fuentes"]))


if __name__ == "__main__":
    np.seterr(all="ignore")
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    main()
