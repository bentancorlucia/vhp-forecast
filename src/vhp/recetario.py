"""Del pronóstico a los ingredientes (recetario): lista de compras de la semana siguiente.

Solo multiplicaciones, sin modelos nuevos:
    plan por segmento × categoría (decision.py, porciones reales)
    → reparto entre los platos de la categoría con la participación de las últimas 4 semanas
    → gramos de cada ingrediente según la receta (abriendo las preparaciones base, recursivo)
    → ÷ (1 − merma del ingrediente)
    → kilos por ingrediente → agrupado por proveedor.
Guarniciones: 250 g por vianda en los platos que llevan acompañamiento, repartidos entre
guarniciones con la columna `Guarniciones` del export (últimas 4 semanas).

Reglas del recetario (Costo del recetario, leído el 18/11/2026):
- Platos por lote (porciones_lote > 1): cantidad por vianda = cantidad ÷ porciones del lote.
- Ingredientes en `unidad` (empanadas, hamburguesas, medallones…) se suman en unidades.
- Una preparación base se abre con su receta escalada por rendimiento real:
  g pedidos ÷ rendimiento real × cada ingrediente. Las bases pueden tener otras bases.
- Ingrediente ↔ ingredientes.csv por nombre normalizado (minúsculas, sin acentos); si no,
  por plural/singular o por la clave del proveedor. Sin match: se reporta y queda fuera.
- Merma: la del ingrediente en ingredientes.csv (si falta, la de su familia). Merma < 0
  (spaghetti, −1,5: absorbe agua): no se divide, se usa el peso seco tal cual y se avisa.
- XL: receta "<plato> XL" si existe; si no, [SUPUESTO] gramos × 1,30.

TODO lo que sale de acá es información comercial (recetas, gramos, mermas, proveedores):
la lista completa va a reports_private/ (ignorado por git). Al repo sube solo un índice
por familia de ingrediente (participación en los kg, no depende de K ni revela recetas).
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd
import yaml

from vhp.config import RAIZ, cargar_config, ruta
from vhp.series import plato_base

RUTA_MAPA = RAIZ / "config" / "recetas_map.yaml"
RUTA_ALIAS = RAIZ / "config" / "privado" / "ingredientes_alias.yaml"  # ignorado por git
SIN_RECETA = "SIN_RECETA"


def norm(s) -> str:
    """Minúsculas, sin acentos, sin espacios repetidos."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------- datos
def cargar_recetario(carpeta=None) -> dict:
    carpeta = carpeta or ruta("recetario")
    platos = pd.read_csv(carpeta / "recetas_platos.csv")
    bases = pd.read_csv(carpeta / "recetas_base.csv")
    ing = pd.read_csv(carpeta / "ingredientes.csv", sep="|")
    fam = pd.read_csv(carpeta / "mermas_por_familia.csv", sep="|")
    ing = ing.merge(fam[["familia", "merma_por_defecto"]], on="familia", how="left")
    ing["merma"] = ing["merma"].fillna(ing["merma_por_defecto"])
    return {"platos": platos, "bases": bases, "ing": ing}


def cargar_mapa(ruta_yaml=RUTA_MAPA, ruta_alias=RUTA_ALIAS) -> dict:
    """Mapeo plato → receta (público) + alias de ingredientes (privado, si existe)."""
    with open(ruta_yaml, encoding="utf-8") as f:
        mapa = yaml.safe_load(f)
    if ruta_alias.exists():
        with open(ruta_alias, encoding="utf-8") as f:
            mapa["alias_ingredientes"] = (yaml.safe_load(f) or {}).get("alias_ingredientes", {})
    return mapa


# ------------------------------------------------------------ resolución de nombres
class Resolutor:
    """Decide si un nombre de ingrediente es una preparación base o un ingrediente comprado."""

    def __init__(self, rec: dict, alias: dict | None = None):
        self.bases = {norm(b): b for b in rec["bases"]["preparacion"].unique()}
        ing = rec["ing"]
        self.ing = {norm(k): k for k in ing["ingrediente_clave"]}
        self.por_producto = {norm(p): k for p, k in zip(ing["producto"], ing["ingrediente_clave"])}
        self.alias = {norm(a): norm(b) for a, b in (alias or {}).items()}

    def resolver(self, nombre: str, clave: str | None = None, dentro_de: str | None = None):
        """('base', nombre_base) | ('ing', ingrediente_clave) | ('sin', nombre)."""
        n = self.alias.get(norm(nombre), norm(nombre))
        if n in self.bases and n != norm(dentro_de or ""):  # una base que se nombra a sí misma = comprado
            return "base", self.bases[n]
        if n in self.ing:
            return "ing", self.ing[n]
        for v in (n.rstrip("s"), n + "s"):  # plural / singular
            if v in self.ing:
                return "ing", self.ing[v]
        if isinstance(clave, str):
            c = norm(re.sub(r"\(.*?\)", "", clave))
            if c in self.por_producto:
                return "ing", self.por_producto[c]
            if c in self.bases:
                return "base", self.bases[c]
        return "sin", nombre


def abrir(nombre_base: str, gramos: float, rec: dict, res: Resolutor, factor: float = 1.0,
          profundidad: int = 0) -> list[dict]:
    """Ingredientes comprados para `gramos` de una preparación base (recursivo)."""
    if profundidad > 10:
        raise RecursionError(f"Ciclo de bases en {nombre_base}")
    b = rec["bases"][rec["bases"]["preparacion"] == nombre_base]
    rend = float(b["rendimiento_real_g"].iat[0])
    esc = gramos / rend
    filas = []
    for r in b.itertuples(index=False):
        tipo, quien = res.resolver(r.ingrediente, r.clave, dentro_de=nombre_base)
        q = r.cantidad * esc * factor
        if tipo == "base":
            if r.unidad != "g":
                raise ValueError(f"Base {quien} pedida en {r.unidad} dentro de {nombre_base}")
            filas += abrir(quien, q, rec, res, 1.0, profundidad + 1)
        else:
            filas.append({"tipo": tipo, "ingrediente": quien, "cantidad": q, "unidad": r.unidad,
                          "via": nombre_base})
    return filas


def explotar_plato(receta: str, rec: dict, res: Resolutor, factor: float = 1.0) -> pd.DataFrame:
    """Ingredientes comprados (antes de merma) para UNA vianda de la receta."""
    p = rec["platos"][rec["platos"]["plato"] == receta]
    if p.empty:
        raise KeyError(f"Receta inexistente: {receta}")
    filas = []
    for r in p.itertuples(index=False):
        q = r.cantidad / r.porciones_lote * factor
        tipo, quien = res.resolver(r.ingrediente, r.clave)
        if tipo == "base":
            if r.unidad != "g":
                raise ValueError(f"Base {quien} pedida en {r.unidad} en {receta}")
            filas += abrir(quien, q, rec, res)
        else:
            filas.append({"tipo": tipo, "ingrediente": quien, "cantidad": q, "unidad": r.unidad, "via": receta})
    return pd.DataFrame(filas)


# ------------------------------------------------------------- mapeo de platos
def receta_de(plato: str, es_xl: bool, mapa: dict, recetas: set[str], factor_xl: float) -> tuple[str, float, str]:
    """(receta, factor, nota) para un plato vendido. factor = multiplicador de gramos."""
    m = mapa["platos"].get(plato, SIN_RECETA)
    if m == SIN_RECETA:
        return SIN_RECETA, 0.0, "sin receta"
    if not es_xl:
        return m, 1.0, ""
    if f"{m} XL" in recetas:
        return f"{m} XL", 1.0, "XL con receta propia"
    return m, factor_xl, f"[SUPUESTO] XL = normal × {factor_xl:.2f}"


def proponer_mapa(vendidos: list[str], recetas: list[str]) -> dict:
    """Mapeo automático por nombre normalizado (lo demás queda SIN_RECETA para revisar)."""
    rn = {norm(r): r for r in recetas}
    return {p: rn.get(norm(p), SIN_RECETA) for p in vendidos}


def viandas_sin_receta(lineas: pd.DataFrame, mapa: dict, desde_por_seg: dict) -> pd.DataFrame:
    """Viandas de platos sin receta (y su % del total) en las últimas 12 semanas de cada segmento."""
    v = _viandas(lineas, desde_por_seg)
    v["receta"] = v["plato"].map(mapa["platos"]).fillna(SIN_RECETA)
    g = v.groupby(["plato", "receta"], as_index=False)["cantidad"].sum()
    g["pct_viandas"] = 100 * g["cantidad"] / g["cantidad"].sum()
    return g[g["receta"] == SIN_RECETA].sort_values("pct_viandas", ascending=False)


def _viandas(lineas: pd.DataFrame, desde_hasta: dict) -> pd.DataFrame:
    """Líneas de vianda de cada segmento entre (desde, hasta]."""
    v = lineas[lineas["tipo_producto"] == "Vianda"]
    partes = [v[(v["segmento"] == s) & (v["fecha_entrega"] > d) & (v["fecha_entrega"] <= h)]
              for s, (d, h) in desde_hasta.items()]
    v = pd.concat(partes).copy()
    v["plato"] = plato_base(v["producto"])
    return v


# --------------------------------------------------------------- repartos
def reparto_platos(lineas: pd.DataFrame, categorias: dict, desde_hasta: dict) -> pd.DataFrame:
    """Participación de cada plato × (normal/XL) dentro de su segmento × categoría (últimas 4 semanas)."""
    v = _viandas(lineas, desde_hasta)
    v["categoria"] = v["plato"].map(categorias)
    g = v.groupby(["segmento", "categoria", "plato", "es_xl"], as_index=False)["cantidad"].sum()
    g["participacion"] = g["cantidad"] / g.groupby(["segmento", "categoria"])["cantidad"].transform("sum")
    return g


def separar_guarniciones(s: pd.Series) -> pd.Series:
    """'Puré de papas, Puré de papas' → una fila por guarnición (una por unidad)."""
    return s.dropna().str.split(",").explode().str.strip().replace("", np.nan).dropna()


def reparto_guarniciones(lineas: pd.DataFrame, desde_hasta: dict, res: Resolutor) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(reparto entre guarniciones que son preparaciones base, por segmento; platos con acompañamiento).

    Un valor de `Guarniciones` que no es una preparación base (sabores de empanada,
    'Omelette', 'Ricotta'…) es una variante del plato, no una guarnición: no cuenta.
    Plato con acompañamiento = más de la mitad de sus unidades traen una guarnición base."""
    v = _viandas(lineas, desde_hasta)
    filas = []
    for (s, plato), d in v.groupby(["segmento", "plato"]):
        g = separar_guarniciones(d["guarnicion"])
        es_base = g.map(lambda x: res.resolver(x)[0] == "base")
        filas.append({"segmento": s, "plato": plato, "unidades": d["cantidad"].sum(),
                      "guarniciones_base": int(es_base.sum()),
                      "con_acompaniamiento": es_base.sum() > 0.5 * d["cantidad"].sum()})
    acomp = pd.DataFrame(filas)
    g = v[["segmento", "guarnicion"]].copy()
    g["guarnicion"] = g["guarnicion"].str.split(",")
    g = g.explode("guarnicion")
    g["guarnicion"] = g["guarnicion"].str.strip()
    g = g[g["guarnicion"].map(lambda x: isinstance(x, str) and res.resolver(x)[0] == "base")]
    g["base"] = g["guarnicion"].map(lambda x: res.resolver(x)[1])
    rep = g.groupby(["segmento", "base"]).size().rename("n").reset_index()
    rep["participacion"] = rep["n"] / rep.groupby("segmento")["n"].transform("sum")
    return rep, acomp


# ---------------------------------------------------------------- cadena
def unidades_por_plato(plan: pd.DataFrame, columnas: list[str], reparto: pd.DataFrame) -> pd.DataFrame:
    """Plan por segmento × categoría (porciones) → porciones por plato × XL."""
    m = reparto.merge(plan[["segmento", "categoria", *columnas]], on=["segmento", "categoria"], how="inner")
    for c in columnas:
        m[c] = m[c] * m["participacion"]
    return m


def lista_compras(up: pd.DataFrame, columnas: list[str], rec: dict, res: Resolutor, mapa: dict,
                  rep_g: pd.DataFrame, acomp: pd.DataFrame, gramos_guarnicion: float,
                  factor_xl: float) -> dict:
    """Cantidades compradas por ingrediente para cada columna de `up` (pronóstico, planes).

    Devuelve {"detalle": una fila por plato/guarnición × ingrediente, "avisos": [...]}."""
    recetas = set(rec["platos"]["plato"])
    cache, filas, avisos = {}, [], []
    up = up.copy()
    rmap = [receta_de(p, x, mapa, recetas, factor_xl) for p, x in zip(up["plato"], up["es_xl"])]
    up["receta"], up["factor"], up["nota"] = zip(*rmap)
    for r in up[up["receta"] != SIN_RECETA].itertuples(index=False):
        k = (r.receta, r.factor)
        if k not in cache:
            cache[k] = explotar_plato(r.receta, rec, res, r.factor)
        d = cache[k].copy()
        for c in columnas:
            d[c] = d["cantidad"] * getattr(r, c)
        d["origen"], d["segmento"], d["plato"], d["es_xl"] = "plato", r.segmento, r.plato, r.es_xl
        filas.append(d)
    # guarniciones: viandas de platos con acompañamiento × 250 g × reparto del segmento
    con = acomp[acomp["con_acompaniamiento"]][["segmento", "plato"]]
    ua = up.merge(con, on=["segmento", "plato"])
    for s, d_s in ua.groupby("segmento"):
        for b in rep_g[rep_g["segmento"] == s].itertuples(index=False):
            k = ("base", b.base)
            if k not in cache:
                cache[k] = pd.DataFrame(abrir(b.base, 1.0, rec, res))  # por gramo de guarnición
            d = cache[k].copy()
            for c in columnas:
                # XL: la guarnición también crece (+30 %) [SUPUESTO]
                g_tot = (d_s[c] * np.where(d_s["es_xl"], factor_xl, 1.0)).sum() * gramos_guarnicion * b.participacion
                d[c] = d["cantidad"] * g_tot
            d["origen"], d["segmento"], d["plato"], d["es_xl"] = "guarnicion", s, b.base, False
            filas.append(d)
    det = pd.concat(filas, ignore_index=True)
    sin = sorted(det.loc[det["tipo"] == "sin", "ingrediente"].unique())
    if sin:
        avisos.append(f"Ingredientes sin match en ingredientes.csv (quedan fuera): {sin}")
    return {"detalle": det, "avisos": avisos, "unidades": up}


def con_merma(det: pd.DataFrame, columnas: list[str], ing: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Suma por ingrediente y unidad, aplica la merma y pasa a kg (las unidades quedan en unidades)."""
    d = det[det["tipo"] == "ing"].groupby(["ingrediente", "unidad"], as_index=False)[columnas].sum()
    d = d.merge(ing[["ingrediente_clave", "producto", "proveedor", "familia", "merma"]],
                left_on="ingrediente", right_on="ingrediente_clave", how="left").drop(columns="ingrediente_clave")
    avisos = []
    gratis = d["familia"] == "Sin costo"  # agua de red: no se compra
    if gratis.any():
        avisos.append(f"Familia 'Sin costo' fuera de la lista (no se compra): {sorted(d.loc[gratis, 'ingrediente'])}")
        d = d[~gratis]
    neg = d["merma"] < 0
    if neg.any():
        avisos.append(f"Merma negativa (absorbe agua al cocinarse), se usa el peso seco sin dividir: "
                      f"{sorted(d.loc[neg, 'ingrediente'])}")
    div = np.where(neg, 1.0, 1 - d["merma"])
    for c in columnas:
        d[c] = d[c] / div
        d[c] = np.where(d["unidad"] == "g", d[c] / 1000, d[c])  # gramos → kg
    d["unidad"] = d["unidad"].replace({"g": "kg"})
    return d.sort_values(["proveedor", "ingrediente"]).reset_index(drop=True), avisos


def por_proveedor(lista: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    return lista.groupby(["proveedor", "unidad"], as_index=False)[columnas].sum()


def indice_familia(lista: pd.DataFrame, col: str) -> pd.DataFrame:
    """Índice público: % de los kg de la semana por familia de ingrediente (no depende de K ni revela recetas)."""
    kg = lista[lista["unidad"] == "kg"].groupby("familia")[col].sum()
    n_unid = lista[lista["unidad"] == "unidad"].groupby("familia").size()
    out = pd.DataFrame({"pct_kg": (100 * kg / kg.sum()).round(1), "ingredientes_en_unidades": n_unid})
    out = out.fillna({"pct_kg": 0.0, "ingredientes_en_unidades": 0}).astype({"ingredientes_en_unidades": int})
    return out.rename_axis("familia").reset_index().sort_values("pct_kg", ascending=False)


# ------------------------------------------------------------------- correr
def correr() -> dict:
    cfg = cargar_config()
    rc, p_cfg = cfg["recetario"], cfg["pronostico"]
    rec = cargar_recetario()
    mapa = cargar_mapa()
    res = Resolutor(rec, mapa.get("alias_ingredientes"))
    lineas = pd.read_parquet(ruta("interim", cfg) / "lineas.parquet")
    from vhp.series import cargar_categorias
    categorias, _ = cargar_categorias()

    fin = {s: pd.Timestamp(p_cfg.get(f"fin_test_{s}", p_cfg["fin_test"])) for s in cfg["serie"]["segmentos"]}
    ult4 = {s: (f - pd.Timedelta(weeks=rc["semanas_reparto"]), f) for s, f in fin.items()}
    ult12 = {s: (f - pd.Timedelta(weeks=12), f) for s, f in fin.items()}

    # 1. mapeo y platos sin receta (últimas 12 semanas de cada segmento)
    sin = viandas_sin_receta(lineas, mapa, ult12)
    vendidos = set(_viandas(lineas, ult12)["plato"])
    no_mapeados = sorted(vendidos - set(mapa["platos"]))
    if no_mapeados:
        raise ValueError(f"Platos vendidos que no están en recetas_map.yaml: {no_mapeados}")

    # 2-4. cadena
    plan = pd.read_csv(ruta("interim", cfg) / "plan_semana_siguiente_real.csv")
    columnas = ["pronostico"] + [c for c in plan.columns if c.startswith("plan_p")]
    rep = reparto_platos(lineas, categorias, ult4)
    up = unidades_por_plato(plan, columnas, rep)
    rep_g, acomp = reparto_guarniciones(lineas, ult4, res)
    out = lista_compras(up, columnas, rec, res, mapa, rep_g, acomp, rc["gramos_guarnicion"], rc["factor_xl"])
    lista, av2 = con_merma(out["detalle"], columnas, rec["ing"])
    prov = por_proveedor(lista, columnas)
    avisos = out["avisos"] + av2

    # controles: viandas repartidas y platos sin receta de la semana
    u = out["unidades"]
    sin_sem = u[u["receta"] == SIN_RECETA]
    control = pd.DataFrame({"columna": columnas,
                            "viandas_plan": [plan[c].sum() for c in columnas],
                            "viandas_repartidas": [u[c].sum() for c in columnas],
                            "viandas_sin_receta": [sin_sem[c].sum() for c in columnas]})
    control["pct_sin_receta"] = 100 * control["viandas_sin_receta"] / control["viandas_plan"]
    xl_sup = u[u["nota"].str.startswith("[SUPUESTO]")].groupby("plato")["pronostico"].sum()

    # salidas privadas
    priv = RAIZ / cfg["rutas"]["reports_private"]
    priv.mkdir(parents=True, exist_ok=True)
    semana = (fin["particulares"] + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    lista.round(3).to_csv(priv / f"lista_compras_{semana}.csv", index=False)
    prov.round(3).to_csv(priv / f"lista_compras_proveedor_{semana}.csv", index=False)
    out["unidades"].round(2).to_csv(priv / f"viandas_por_plato_{semana}.csv", index=False)
    rep_g.round(4).to_csv(priv / "reparto_guarniciones.csv", index=False)
    acomp.to_csv(priv / "platos_con_acompaniamiento.csv", index=False)
    sin.round(3).to_csv(priv / "platos_sin_receta.csv", index=False)
    control.round(2).to_csv(priv / "control_compras.csv", index=False)

    # salida pública: índice por familia (pronóstico y plan elegido)
    fam = indice_familia(lista, "pronostico")
    kg = lista[lista["unidad"] == "kg"]
    ratios = {c: kg[c].sum() / kg["pronostico"].sum() for c in columnas[1:]}
    fam.to_csv(ruta("tablas", cfg) / "compras_familia_indice.csv", index=False)
    pub = pd.DataFrame([{"semana": f"{fin['particulares'] + pd.Timedelta(days=2):%d/%m/%Y}–"
                                   f"{fin['particulares'] + pd.Timedelta(days=7):%d/%m/%Y}",
                         "ingredientes": len(lista), "proveedores": lista["proveedor"].nunique(),
                         "pct_viandas_sin_receta_12sem": round(sin["pct_viandas"].sum(), 2),
                         "pct_viandas_sin_receta_semana": round(control["pct_sin_receta"].iat[0], 2),
                         "platos_sin_receta_12sem": len(sin),
                         **{f"kg_{c}_sobre_pronostico": round(v, 3) for c, v in ratios.items()}}])
    pub.to_csv(ruta("tablas", cfg) / "compras_resumen.csv", index=False)

    print(f"Recetario: {rec['platos']['plato'].nunique()} platos, {rec['bases']['preparacion'].nunique()} bases, "
          f"{len(rec['ing'])} ingredientes")
    print(f"Platos sin receta, últimas 12 semanas ({', '.join(f'{s} {d:%d/%m}–{h:%d/%m/%Y}' for s, (d, h) in ult12.items())}): "
          f"{len(sin)} platos, {sin['pct_viandas'].sum():.2f} % de las viandas")
    print(sin.round(2).to_string(index=False))
    print("XL sin receta propia [SUPUESTO ×1,30]:", ", ".join(xl_sup.index))
    print("Platos con acompañamiento:", int(acomp["con_acompaniamiento"].sum()), "de", len(acomp), "(plato × segmento)")
    print("Control de viandas:\n" + control.round(1).to_string(index=False))
    for a in avisos:
        print("AVISO:", a)
    print(f"Lista de compras ({len(lista)} ingredientes, {lista['proveedor'].nunique()} proveedores) → {priv.name}/")
    print("Índice por familia (% de los kg):\n" + fam.to_string(index=False))
    return {"lista": lista, "proveedor": prov, "control": control, "sin_receta": sin, "familia": fam,
            "detalle": out["detalle"], "unidades": out["unidades"], "avisos": avisos, "mapa": mapa}
