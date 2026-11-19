"""reports/resultados.md con las tablas clave (las figuras ya están en reports/figures/).

Solo usa datos PÚBLICOS: reports/tables/ (métricas que no dependen de K) y
data/processed/. Nunca lee data/interim/ ni data/raw_private/. Las decisiones
y su porqué salen de reports/decisiones.yaml.
"""
from __future__ import annotations

import pandas as pd
import yaml

from vhp import eda
from vhp.config import RAIZ, cargar_config, ruta

FASES = {"datos": "Datos y preparación", "eda": "Análisis exploratorio", "modelos": "Pronóstico del total",
         "mix": "Clima y mix de categorías", "eventos": "Efecto de eventos", "ads": "Gasto en Meta Ads",
         "plan": "Plan de compras", "compras": "De platos a ingredientes"}
NOMBRES = {"naive": "Naive", "naive_estacional": "Naive estacional", "media_movil_4sem": "Media móvil 4 semanas",
           "ets": "ETS", "sarima": "SARIMA", "lgbm_directo": "LightGBM directo", "mlp": "MLP"}
NOTA_ESCALA = ("Unidades multiplicadas por una constante secreta K (anonimización). Las métricas relativas "
               "(MASE, WAPE, coberturas, %) no cambian con K.")


# ------------------------------------------------------------------ formato
def n(x, d=1, signo=False) -> str:
    """Número con coma decimal."""
    s = f"{x:+.{d}f}" if signo else f"{x:.{d}f}"
    return s.replace("-", "−").replace(".", ",")


def pct(x, d=1, signo=False) -> str:
    return n(x, d, signo) + " %"


def md(t: pd.DataFrame) -> str:
    """Tabla en Markdown (sin depender de tabulate)."""
    celdas = t.astype(object).where(t.notna(), "")
    filas = ["| " + " | ".join(map(str, t.columns)) + " |", "|" + "---|" * len(t.columns)]
    filas += ["| " + " | ".join(map(str, r)) + " |" for r in celdas.itertuples(index=False)]
    return "\n".join(filas)


def _t(nombre: str, **kw) -> pd.DataFrame:
    return pd.read_csv(ruta("tablas") / f"{nombre}.csv", **kw)


# ------------------------------------------------------------------ números
class Num:
    """Acceso cómodo a las cifras de reports/tables/."""

    def __init__(self):
        self.met = _t("backtest_total_metricas").set_index("modelo")
        self.dm = _t("backtest_total_dm")
        self.sim = _t("plan_simulacion")
        self.sens = _t("plan_sensibilidad_costo")
        self.semana = _t("plan_semana_siguiente")
        self.ef = _t("mix_efecto_temperatura")
        self.mpart = _t("mix_metricas_participacion")
        self.ev = _t("eventos_efectos")
        self.cal = _t("eda_efectos_calendario")
        self.dow = _t("eda_dia_semana").rename(columns={"Unnamed: 0": "dia"}).set_index("dia")
        self.est = _t("eda_estacionariedad")
        self.var = _t("ads_variacion_gasto")
        self.reg = _t("ads_regresion")
        self.gr = _t("ads_granger")
        self.lb = _t("backtest_total_ljung_box")
        self.muni = _t("mix_metricas_unidades")
        self.p_info = _t("plan_p_elegido").iloc[0]
        self.sim_seg = _t("plan_simulacion_segmento")
        self.xl = _t("plan_prop_xl")
        self.compras = _t("compras_resumen").iloc[0] if (ruta("tablas") / "compras_resumen.csv").exists() else None
        self.familia = _t("compras_familia_indice") if (ruta("tablas") / "compras_familia_indice.csv").exists() else None
        pc = cargar_config()["plan_compras"]
        self.faltante, self.sobrante = pc["costo_faltante_vianda"], pc["costo_sobrante_vianda"]
        self.p_elegido = int(self.sim.loc[self.sim.elegido, "p"].iat[0])

    def mase(self, m):
        return self.met.loc[m, "MASE"]

    def dm_p(self, a, b, dm=None):
        dm = self.dm if dm is None else dm
        r = dm[((dm.modelo_1 == a) & (dm.modelo_2 == b)) | ((dm.modelo_1 == b) & (dm.modelo_2 == a))]
        return float(r["p_valor"].iat[0])

    def efecto(self, seg, cat):
        r = self.ef[(self.ef.segmento == seg) & (self.ef.categoria == cat)]
        return r.iloc[0]


# ------------------------------------------------------------- tablas
def tabla_modelos(N: Num, met: pd.DataFrame | None = None) -> pd.DataFrame:
    t = (N.met if met is None else met).reset_index()[["modelo", "MASE", "WAPE", "cobertura_80"]].copy()
    t["modelo"] = t["modelo"].map(NOMBRES)
    t["WAPE"] = (100 * t["WAPE"]).map(lambda x: pct(x))
    t["cobertura_80"] = (100 * t["cobertura_80"]).map(lambda x: pct(x, 0))
    t["MASE"] = t["MASE"].map(lambda x: n(x, 3))
    return t.rename(columns={"modelo": "Modelo", "cobertura_80": "Cobertura 80 %"})


def tabla_plan(N: Num) -> pd.DataFrame:
    s = N.sim.copy()
    s["Método"] = s["metodo"].map({"lgbm": "LightGBM × participación", "naive_estacional": "Naive estacional"})
    s["p"] = [f"{int(p)} (elegido)" if e else str(int(p)) for p, e in zip(s.p, s.elegido)]
    out = s.assign(**{"Cobertura": (100 * s.cobertura).map(lambda x: pct(x)),
                      "Sobrante": s.sobrante_pct.map(lambda x: pct(x)),
                      "Faltante": s.faltante_pct.map(lambda x: pct(x)),
                      "UYU por vianda": s.costo_por_vianda.map(lambda x: n(x))})
    return out[["Método", "p", "Cobertura", "Sobrante", "Faltante", "UYU por vianda"]]


def tabla_eventos(N: Num) -> pd.DataFrame:
    filas = []
    for _, r in N.ev.iterrows():
        es_pct = not r["serie"].startswith("tasa")
        if es_pct:
            ef = f"{pct(r.efecto_pct, 0, True)} [{n(r.pct_inf, 0, True)}; {n(r.pct_sup, 0, True)}]"
        else:
            ef = f"{n(r.efecto, 3, True)} [{n(r.efecto_inf, 3, True)}; {n(r.efecto_sup, 3, True)}] por vianda"
        pl = "—" if pd.isna(r.get("n_placebos")) else f"{int(r.placebos_significativos)} de {int(r.n_placebos)}"
        emd = r.get("efecto_minimo_detectable")
        emd = "—" if pd.isna(emd) else (f"±{n(emd, 0)} %" if es_pct else f"±{n(emd, 3)}")
        filas.append({"Evento": r.evento.replace("_", " "),
                      "Serie": r.serie.replace("_", " "),
                      "Período": f"{pd.Timestamp(r.desde):%d/%m/%Y}–{pd.Timestamp(r.hasta):%d/%m/%Y}",
                      "Efecto [IC 95 %]": ef, "SARIMA": r.orden, "Placebos significativos": pl,
                      "Efecto mínimo detectable": emd})
    return pd.DataFrame(filas)


def tabla_dm(N: Num, dm: pd.DataFrame | None = None) -> pd.DataFrame:
    t = (N.dm if dm is None else dm).copy()
    return pd.DataFrame({"Modelo 1": t.modelo_1.map(NOMBRES), "Modelo 2": t.modelo_2.map(NOMBRES),
                         "DM": t.DM.map(lambda x: n(x, 2)), "p": t.p_valor.map(lambda x: n(x, 3)),
                         "Mejor": t.mejor.map(NOMBRES)})


def tabla_calendario(N: Num) -> pd.DataFrame:
    t = N.cal.copy()
    t["Efecto [IC 95 %]"] = [f"{pct(r.efecto_pct, 1, True)} [{n(r.ic95_inf_pct, 1, True)}; {n(r.ic95_sup_pct, 1, True)}]"
                             for r in t.itertuples()]
    t["p"] = t.p_valor.map(lambda x: n(x, 3))
    return t.rename(columns={"serie": "Serie", "variable": "Variable", "dias": "Días"})[
        ["Serie", "Variable", "Días", "Efecto [IC 95 %]", "p"]]


def tabla_mix_unidades(N: Num) -> pd.DataFrame:
    t = N.muni.copy()
    return pd.DataFrame({"Nivel": t.nivel, "Modelo": t.modelo, "MASE": t.MASE.map(lambda x: n(x, 3)),
                         "WAPE": (100 * t.WAPE).map(lambda x: pct(x)),
                         "Cobertura 80 %": (100 * t.cobertura_80).map(lambda x: pct(x))})


def tabla_sensibilidad(N: Num) -> pd.DataFrame:
    t = N.sens
    return pd.DataFrame({"Costo de faltante": t.costo_faltante.map(lambda x: f"${int(x)}"), "p elegido": t.p.astype(int),
                         "Cobertura": (100 * t.cobertura).map(lambda x: pct(x)),
                         "Sobrante": t.sobrante_pct.map(lambda x: pct(x)), "Faltante": t.faltante_pct.map(lambda x: pct(x)),
                         "UYU por vianda": t.costo_por_vianda.map(lambda x: n(x))})


def periodo_semanas(desde, hasta) -> str:
    """Semanas rotuladas en lunes: el período termina el domingo de la última semana."""
    return f"{pd.Timestamp(desde):%d/%m/%Y}–{pd.Timestamp(hasta) + pd.Timedelta(days=6):%d/%m/%Y}"


def tabla_decisiones(dec: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{"Fase": FASES[d["fase"]], "Decisión": d["titulo"], "Por qué": d["porque"],
                          "Quién": "negocio" if d["quien"] == "Lucía" else "técnica"} for d in dec])


def texto_modelos(N: Num) -> str:
    """Párrafo del backtest del total, armado con los números de las tablas."""
    orden = list(N.met.index)
    g, s2, s3 = orden[0], orden[1], orden[2]
    p2, p3 = N.dm_p(g, s2), N.dm_p(g, s3)
    nexo = ("no lo separa de {a} (p = {pa}) ni de {b} (p = {pb})" if min(p2, p3) >= 0.05
            else "da estas diferencias: {a} p = {pa}, {b} p = {pb}")
    t = (f"{NOMBRES[g]} es el de menor MASE ({n(N.mase(g), 3)}); Diebold-Mariano "
         + nexo.format(a=NOMBRES[s2], pa=n(p2, 2), b=NOMBRES[s3], pb=n(p3, 2)) + ". ")
    pn = [N.dm_p(m, "naive_estacional") for m in orden[:4] if m != "naive_estacional"]
    t += f"Los mejores le ganan al naive estacional (p ≤ {n(max(pn), 3)}). "
    if "mlp" in N.met.index and "lgbm_directo" in N.met.index:
        t += (f"El MLP (MASE {n(N.mase('mlp'), 3)}) {'no ' if N.mase('mlp') >= N.mase('lgbm_directo') else ''}"
              f"le gana a LightGBM ({n(N.mase('lgbm_directo'), 3)}). ")
    t += ("El intervalo 80 % de todos los modelos son los percentiles 10 y 90 del error relativo (y / ŷ) del propio "
          "modelo en las 12 semanas previas al origen. ")
    lb = N.lb
    t += (f"Ljung-Box sobre los residuos de ETS y SARIMA (rezagos 6 y 12): p entre {n(lb.lb_pvalue.min(), 2)} y "
          f"{n(lb.lb_pvalue.max(), 2)}, sin autocorrelación que quede por modelar.")
    return t


def texto_eventos(N: Num) -> str:
    ev = N.ev.set_index(["evento", "serie"])
    t = []
    if ("baja_pauta", "clientes_nuevos_particulares") in ev.index:
        a = ev.loc[("baja_pauta", "clientes_nuevos_particulares")]
        b = ev.loc[("baja_pauta", "pedidos_recurrentes_particulares")]
        t.append(f"Baja de pauta de noviembre 2026 (PRELIMINAR, {int(a.dias)} días hábiles, "
                 f"{pd.Timestamp(a.desde):%d/%m}–{pd.Timestamp(a.hasta):%d/%m/%Y}): clientes nuevos "
                 f"{pct(a.efecto_pct, 0, True)} [{n(a.pct_inf, 0, True)}; {n(a.pct_sup, 0, True)}], pedidos de clientes "
                 f"que ya compraron {pct(b.efecto_pct, 0, True)} [{n(b.pct_inf, 0, True)}; {n(b.pct_sup, 0, True)}]. "
                 f"Con este ruido, en dos semanas solo se distinguiría un efecto de ±{n(a.efecto_minimo_detectable, 0)} % "
                 f"en los nuevos y ±{n(b.efecto_minimo_detectable, 0)} % en los recurrentes. La fecha de inicio "
                 "(02/11/2026) es un supuesto: es la primera semana con menos gasto en el Tablero (la campaña bajó ~8 %); "
                 "no hay gasto diario de octubre–noviembre.")
    if ("meta_reparto", "clientes_nuevos_particulares") in ev.index:
        a = ev.loc[("meta_reparto", "clientes_nuevos_particulares")]
        t.append(f"Cambio de reparto entre anuncios del 05/09/2026 (8 semanas): clientes nuevos "
                 f"{pct(a.efecto_pct, 0, True)} [{n(a.pct_inf, 0, True)}; {n(a.pct_sup, 0, True)}], "
                 f"{int(a.placebos_significativos)} de {int(a.n_placebos)} placebos significativos.")
    if ("suba_precio", "viandas_particulares") in ev.index:
        a = ev.loc[("suba_precio", "viandas_particulares")]
        t.append(f"Suba de precio con 8 semanas posteriores: viandas {pct(a.efecto_pct, 0, True)} "
                 f"[{n(a.pct_inf, 0, True)}; {n(a.pct_sup, 0, True)}], p-placebo {n(a.p_placebo, 2)} con "
                 f"{int(a.n_placebos)} placebos. Sigue PRELIMINAR: con ventanas de 8 semanas o más entran como mucho "
                 "4 placebos, así que el p-placebo no puede bajar de 0,2.")
    return " ".join(t)


def seccion_meta(N: Num) -> list[str]:
    var = N.var.set_index("serie")
    gt = N.var[N.var.serie == "gasto_campania_viandas"].iloc[0]
    esc = N.var[N.var.serie == "gasto_meta_total"].iloc[0]
    cl = var.loc["clics"]
    reg = N.reg.set_index("termino")
    rg, rc_, rk = reg.loc["log_gasto_total"], reg.loc["log_gasto_campania"], reg.loc["log_clics"]
    gr = N.gr.set_index("causa")
    gg, gk = gr.loc["log_gasto_campania"], gr.loc["log_clics"]

    def fr(r):
        return (f"{n(r.coef, 2, True)} [{n(r.ic95_inf, 2, True)}; {n(r.ic95_sup, 2, True)}], p = {n(r.p_valor, 3)}, "
                f"R² = {n(r.r2, 2)} ({int(r.semanas)} semanas, {periodo_semanas(r.desde, r.hasta)})")
    return [f"## 5. Gasto en Meta Ads (semanal, {periodo_semanas(rg.desde, rg.hasta)})", "",
            f"- El gasto de la campaña casi no varía desde febrero (CV {pct(gt.cv_pct)}, semanas "
            f"{periodo_semanas(gt.desde, gt.hasta)}, incluida la primera semana de la baja de noviembre); la variación "
            f"grande sigue siendo el escalón enero → febrero (gasto total ×{n(esc.max_sobre_min)}), que coincide con "
            f"el fin del verano. Los clics sí varían (CV {pct(cl.cv_pct)}, máx/mín ×{n(cl.max_sobre_min)}), por los "
            "cambios de anuncios.",
            f"- log(clientes nuevos) ~ log(gasto total) + verano: elasticidad {fr(rg)}. Correlación log gasto–verano "
            f"{n(rg.corr_x_control, 3, True)}: los dos efectos no se pueden separar.",
            f"- log(clientes nuevos) ~ log(gasto de la campaña), desde el 02/02/2026 (verano constante: sale): "
            f"elasticidad {fr(rc_)}.",
            f"- log(clientes nuevos) ~ log(clics de la campaña), desde el 02/02/2026: elasticidad {fr(rk)}.",
            f"- Granger con 1 rezago (fijado antes de mirar): gasto de la campaña → clientes nuevos F = {n(gg.F, 2)}, "
            f"p = {n(gg.p_valor, 3)}; clics → clientes nuevos F = {n(gk.F, 2)}, p = {n(gk.p_valor, 3)} "
            f"({int(gk.semanas)} semanas).", "",
            "Conclusión: el efecto del gasto sigue sin identificarse (el gasto casi no varió). Los clics se mueven "
            "junto con los clientes nuevos, pero no se asignan al azar (dependen de qué anuncios elige la agencia): es "
            "correlación, no causa. Recomendación que se mantiene: variar el gasto a propósito (por ejemplo, semanas "
            "alternas). La baja de noviembre es la primera variación del gasto desde febrero, pero con 2 semanas el "
            "resultado es preliminar (sección 4). No hay origen del pedido (UTM) en el export: la atribución por "
            "anuncio queda como trabajo futuro.", "",
            "![Meta Ads](figures/11_meta_ads.png)", ""]


def seccion_plan(N: Num) -> list[str]:
    pi = N.p_info
    xl = N.xl.groupby("segmento")["prop_xl"].mean()
    seg = N.sim_seg[N.sim_seg.metodo == "lgbm"].set_index("segmento")
    return [f"## 6. Plan de compras (compra semanal por segmento × categoría; backtest {pi.periodo_test})", "",
            "Plan = pronóstico + colchón: pronóstico semanal × percentil p del cociente real / pronóstico de las "
            "12 semanas previas (las 7 categorías del segmento juntas). Cada segmento usa sus últimas 12 semanas con "
            "datos. Se elige el p de menor costo simulado. Desde noviembre 2026 el "
            "sobrante y el faltante se ponderan por la proporción de XL del segmento en las 12 semanas previas a cada "
            f"origen (empresas {pct(100 * xl['empresas'])}, particulares {pct(100 * xl['particulares'])} en promedio): "
            "sobrante = $200 (normal) / $260 (XL), faltante = $150 / $155 (precio $350 / $415 menos costo).", "",
            f"p elegido = {int(pi.p_elegido)} (antes: 45; con los costos fijos $200 / $150 en esta misma ventana "
            f"sería {int(pi.p_costos_fijos)}).", "",
            md(tabla_plan(N)), "",
            "Por segmento con el p elegido: " + "; ".join(
                f"{s} cobertura {pct(100 * r.cobertura)}, sobrante {pct(r.sobrante_pct)}, faltante "
                f"{pct(r.faltante_pct)}, {n(r.costo_por_vianda)} UYU por vianda" for s, r in seg.iterrows()) + ".", "",
            "Sensibilidad al costo de faltante de la vianda normal (la XL, +$5; con cada costo se vuelve a elegir p):",
            "", md(tabla_sensibilidad(N)), "",
            "El p se elige en el mismo backtest en que se evalúa, así que el costo del elegido es algo optimista.", "",
            "![Plan de compras](figures/12_plan_compras.png)", "",
            "Plan para la semana 16/11–21/11/2026, una compra semanal (porciones × K), con datos de los dos "
            "segmentos hasta el 14/11/2026.", "",
            md(N.semana.rename(columns={"segmento": "Segmento", "categoria": "Categoría", "pronostico": "Pronóstico",
                                        "origen_datos": "Datos hasta"})
               .assign(Pronóstico=lambda t: t["Pronóstico"].round(0).astype(int))), ""]


def seccion_compras(N: Num) -> list[str]:
    if N.compras is None:
        return []
    c, fam = N.compras, N.familia
    ratios = {k.replace("kg_", "").replace("_sobre_pronostico", ""): v for k, v in c.items() if k.startswith("kg_plan")}
    return ["## 7. De platos a ingredientes (recetario)", "",
            "Cadena de multiplicaciones: plan por segmento × categoría → reparto entre los platos de la categoría "
            "(participación de las últimas 4 semanas, normal y XL por separado) → gramos de cada ingrediente según "
            "la receta, abriendo las preparaciones base de forma recursiva (escaladas por rendimiento real) → "
            "÷ (1 − merma) → kg por ingrediente y por proveedor. Guarniciones: 250 g por vianda en los platos con "
            "acompañamiento, repartidos según la columna Guarniciones de las últimas 4 semanas. XL sin receta propia: "
            "gramos × 1,30 (supuesto, a validar).", "",
            f"- Semana {c.semana}: {int(c.ingredientes)} ingredientes de {int(c.proveedores)} proveedores. La lista "
            "completa (con recetas, mermas y proveedores) es información comercial y queda en `reports_private/` "
            "(no se sube).",
            f"- Platos sin receta: {int(c.platos_sin_receta_12sem)} platos, {pct(c.pct_viandas_sin_receta_12sem)} de "
            f"las viandas de las últimas 12 semanas ({pct(c.pct_viandas_sin_receta_semana)} del pronóstico de la "
            "semana): quedan fuera de la lista y se reportan.",
            "- 5 ingredientes de las recetas no están en la lista de ingredientes (sin costo cargado en la app) y quedan "
            "fuera; el agua no se compra. Un ingrediente con merma negativa (la pasta seca absorbe agua) se usa con su "
            "peso seco, sin dividir.",
            "- kg del plan sobre kg del pronóstico: " + ", ".join(f"{k} ×{n(v, 3)}" for k, v in ratios.items()) + ".",
            "", "Índice por familia de ingrediente (% de los kg del pronóstico de la semana; los productos porcionados "
            "se compran por unidad):", "",
            md(pd.DataFrame({"Familia": fam.familia, "% de los kg": fam.pct_kg.map(lambda x: n(x, 1)),
                             "Ingredientes en unidades": fam.ingredientes_en_unidades})), ""]


# ============================================================ resultados.md
def resultados_md() -> str:
    N = Num()
    ancho = eda.cargar_datos()["ancho"]
    dias = ancho["Total"].dropna()
    pb = eda.periodo(_t("backtest_total_predicciones", parse_dates=["fecha"])["fecha"])
    decisiones = yaml.safe_load(open(RAIZ / "reports" / "decisiones.yaml", encoding="utf-8"))["decisiones"]
    L = ["# Resultados — Del pedido al plato", "",
         "Pronóstico de la demanda de Viandas Hotel del Prado, efecto de eventos y de la pauta en Meta, y plan de compras.", "",
         f"Datos: Total, particulares y empresas {eda.periodo(dias.index)} ({len(dias)} días hábiles; noviembre "
         "cortado en la última semana completa). Empresas de septiembre a noviembre sale del export de Excel (la "
         f"pantalla de Resumen comercial las muestra en 0). Backtest walk-forward del Total: semanas {pb} "
         "(12 orígenes, uno por sábado). " + NOTA_ESCALA, "",
         "Todo se regenera con `python main.py all`. Las tablas están en `reports/tables/`, las figuras en "
         "`reports/figures/`, y el porqué de cada decisión en `reports/decisiones.yaml`.", ""]

    L += ["## 1. Patrones (análisis exploratorio)", "",
          f"- La serie en nivel no es estacionaria (ADF p = {n(N.est.adf_p[0], 2)}); con una diferencia "
          f"estacional de 6 días sí lo es (ADF p < 0,001). Por eso SARIMA usa D = 1 con período 6.",
          f"- Perfil semanal opuesto: el lunes los particulares están en {n(N.dow.loc['Lun', 'Particulares'], 2)} "
          f"veces su media y el sábado las empresas en {n(N.dow.loc['Sáb', 'Empresas'], 2)}.",
          "- Feriados laborables (se abre): " + ", ".join(
              f"{r.serie} {pct(r.efecto_pct, 0, True)} [{n(r.ic95_inf_pct, 0, True)}; {n(r.ic95_sup_pct, 0, True)}]"
              for r in N.cal[N.cal.variable == "feriado_laborable"].itertuples()) + ".",
          "", f"Efectos de calendario: regresión lineal de log(y) en días hábiles ({eda.periodo(dias.index)}) con día de "
          "la semana, tendencia, feriado laborable, víspera y día después de un cierre, y verano (enero). "
          "Efecto en % sobre el nivel:", "", md(tabla_calendario(N)), "",
          "![Serie diaria](figures/01_series_diarias.png)", "", "![Día de la semana](figures/04_dia_semana.png)", ""]

    L += [f"## 2. Pronóstico del total (backtest {pb})", "", md(tabla_modelos(N)), "", texto_modelos(N), "",
          f"Diebold-Mariano (error absoluto, h = 1 a 6, backtest {pb}):", "", md(tabla_dm(N)), "",
          "![Backtest del total](figures/07_backtest_total.png)", ""]

    c_e, c_p = N.efecto("empresas", "carne vacuna"), N.efecto("particulares", "carne vacuna")
    L += ["## 3. Clima → mix de categorías", "",
          f"Efecto descriptivo (todo el período) de un día de calor contra uno de frío: la carne vacuna baja "
          f"{n(-c_e.calor_menos_frio_pp)} pp en empresas [{n(c_e.ic95_inf_pp, 1, True)}; {n(c_e.ic95_sup_pp, 1, True)}] "
          f"y {n(-c_p.calor_menos_frio_pp)} pp en particulares. Para pronosticar a una semana, el clima no mejora "
          f"la participación media de las últimas 4 semanas (log loss por vianda, backtest {pb}):", "",
          md(pd.DataFrame({"Segmento": N.mpart.segmento, "Método": N.mpart.metodo,
                           "Log loss por vianda": N.mpart.logloss_por_vianda.map(lambda x: n(x, 4)),
                           "Error absoluto medio (pp)": N.mpart.error_abs_medio_pp.map(lambda x: n(x, 2))})), "",
          f"Unidades por categoría = pronóstico del segmento (LightGBM directo) × participación prevista (backtest {pb}; "
          "intervalo 80 % con los errores de las 12 semanas previas):", "", md(tabla_mix_unidades(N)), "",
          "![Efecto de la temperatura](figures/08_mix_efecto_temperatura.png)", ""]

    L += ["## 4. Efecto de eventos (contrafactual SARIMA + placebos)", "",
          "Para cada evento se ajusta un SARIMA sobre log(y) solo con los días previos (órdenes por AIC en una grilla "
          "chica, exógenas de calendario, sin constante), se pronostica el período posterior como contrafactual y se "
          "compara con lo observado (IC 95 % por simulación). Los placebos repiten el método en fechas falsas "
          "anteriores al evento. Efecto medio en el período de cada evento (particulares, datos "
          f"{eda.periodo(dias.index)}). Clientes nuevos y pedidos de clientes que ya compraron van en nivel (hay días "
          "con 0) y el efecto se da en %. Efecto mínimo detectable = 2,8 × desvío de los efectos placebo (test al 5 %, "
          "potencia 80 %):", "", md(tabla_eventos(N)), "", texto_eventos(N), "",
          "![Eventos](figures/10_eventos.png)", ""]

    L += seccion_meta(N)

    L += seccion_plan(N)
    L += seccion_compras(N)

    L += ["## 8. Decisiones y por qué", "", md(tabla_decisiones(decisiones)), ""]
    return "\n".join(L)


def correr() -> None:
    destino = RAIZ / "reports" / "resultados.md"
    destino.write_text(resultados_md(), encoding="utf-8")
    print(f"{destino.relative_to(RAIZ)} generado")
