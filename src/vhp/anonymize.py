"""Anonimización de los datos para la parte pública del repo.

- Teléfono y empresa → hash SHA-256 con VHP_SALT. Los hashes quedan SOLO en
  data/interim/ (ignorado): al repo no sube ningún identificador, ni hasheado.
- Cantidades × VHP_K, redondeadas.
- Importes y gasto de Meta → índice base 100.

Las métricas relativas (MASE, WAPE, cobertura) no cambian al multiplicar
la serie por una constante; el redondeo agrega un error de a lo sumo 0,5 por celda.
"""
from __future__ import annotations

import hashlib
import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from vhp.config import RAIZ, cargar_config, ruta
from vhp.load import pedidos_diarios_particulares, pedidos_semanales_particulares
from vhp.series import asignar_categoria, cargar_categorias

COLUMNAS_PROHIBIDAS = {"producto", "telefono", "empresa", "nombre", "direccion", "notas", "importe", "precio_unitario",
                       "nro_pedido", "id_cliente", "id_empresa"}


def secretos() -> tuple[str, float]:
    """Lee VHP_SALT y VHP_K del .env. Falla si no están."""
    load_dotenv(RAIZ / ".env")
    salt, k = os.getenv("VHP_SALT"), os.getenv("VHP_K")
    if not salt or not k:
        raise RuntimeError("Faltan VHP_SALT o VHP_K en .env")
    return salt, float(k)


def hashear(s: pd.Series, salt: str) -> pd.Series:
    """SHA-256 de salt + valor. Los vacíos quedan vacíos."""
    return s.map(lambda v: hashlib.sha256((salt + v).encode()).hexdigest() if isinstance(v, str) else pd.NA)


def escalar(x: pd.Series, k: float) -> pd.Series:
    """Cantidades × K, redondeadas al entero."""
    return np.rint(x.astype(float) * k).astype(int)


def escalar_conservando_total(x: pd.Series, k: float) -> pd.Series:
    """Escala × K redondeando por el método del mayor resto.

    El total del grupo queda en round(K × total real) y cada celda difiere de
    K × real en menos de 1. Evita el sesgo de redondear celda por celda cuando
    hay muchas celdas chicas (ej.: un plato con 1 unidad en el día).
    """
    v = x.astype(float).to_numpy() * k
    piso = np.floor(v)
    faltan = int(round(v.sum())) - int(piso.sum())
    orden = np.argsort(-(v - piso), kind="stable")
    piso[orden[:faltan]] += 1
    return pd.Series(piso.astype(int), index=x.index)


def indice_base_100(df: pd.DataFrame, columnas: list[str], base: float) -> pd.DataFrame:
    """Convierte columnas a índice: valor / base × 100 (redondeado a 2 decimales)."""
    out = df.copy()
    for c in columnas:
        out[c] = (100 * out[c] / base).round(2)
    return out


def lineas_seudonimizadas(lineas: pd.DataFrame, salt: str) -> pd.DataFrame:
    """Reemplaza teléfono y empresa por hashes (uso interno, no se publica)."""
    out = lineas.copy()
    out["id_cliente"] = hashear(out.pop("telefono"), salt)
    out["id_empresa"] = hashear(out.pop("empresa"), salt)
    return out


def ventas_diarias(lineas: pd.DataFrame, k: float, claves_extra: list[str] | None = None) -> pd.DataFrame:
    """Unidades diarias por fecha × segmento × tipo de producto (+ claves_extra), escaladas.

    Se publica por categoría, no por plato (decisión de Lucía): con celdas chicas
    se podría estimar K. Mientras config/categorias.yaml no esté validado se
    publica sin desagregar por debajo del tipo de producto.

    El importe diario va como índice base 100 (base = importe diario medio de
    todo el período, todos los segmentos juntos, para que sean comparables).
    """
    claves = ["fecha_entrega", "segmento", "tipo_producto"] + (claves_extra or [])
    g = lineas.groupby(claves, as_index=False).agg(unidades=("cantidad", "sum"), importe=("importe", "sum"))
    base = g.groupby("fecha_entrega")["importe"].sum().mean()
    g["indice_importe"] = (100 * g.pop("importe") / base).round(4)
    g["unidades"] = g.groupby(["fecha_entrega", "segmento", "tipo_producto"])["unidades"].transform(
        lambda s: escalar_conservando_total(s, k))
    return g.rename(columns={"fecha_entrega": "fecha"})


def particulares_semanal(lineas: pd.DataFrame, k: float) -> pd.DataFrame:
    """Pedidos y clientes nuevos de particulares por semana (lunes a domingo), escalados."""
    s = pedidos_semanales_particulares(lineas)
    for c in ["pedidos_particulares", "clientes_nuevos_particulares"]:
        s[c] = escalar(s[c], k)
    return s


def particulares_diario(lineas: pd.DataFrame, k: float) -> pd.DataFrame:
    """Clientes nuevos y pedidos de clientes que ya compraron, por día (particulares), × K."""
    d = pedidos_diarios_particulares(lineas)
    for c in ["clientes_nuevos", "pedidos_recurrentes"]:
        d[c] = escalar(d[c], k)
    return d


def xl_semanal(lineas: pd.DataFrame) -> pd.DataFrame:
    """Proporción de viandas XL por segmento y semana (lunes a domingo). Es un cociente:
    no depende de K y no revela cantidades."""
    v = lineas[lineas["tipo_producto"] == "Vianda"]
    v = v.assign(semana_ini=v["fecha_entrega"].dt.to_period("W-SUN").dt.start_time,
                 xl=v["cantidad"] * v["es_xl"])
    g = v.groupby(["semana_ini", "segmento"])[["xl", "cantidad"]].sum()
    return (g["xl"] / g["cantidad"]).round(4).rename("prop_xl").reset_index()


def meta_ads_indice(meta: pd.DataFrame) -> pd.DataFrame:
    """Serie semanal de Meta en índice base 100.

    Las columnas de gasto comparten la base (gasto total medio semanal) para que
    se puedan comparar entre sí; impresiones, clics y alcance usan su propia media.
    """
    gasto = [c for c in meta.columns if c.startswith("gasto_")]
    out = indice_base_100(meta, gasto, meta["gasto_meta_total"].mean())
    for c in ["impresiones", "clics", "alcance"]:
        if c in out:
            out = indice_base_100(out, [c], meta[c].mean())
    return out


def anonimizar() -> None:
    """Fase 2: genera data/interim/lineas_seudo.parquet y las salidas públicas."""
    cfg = cargar_config()
    salt, k = secretos()
    lineas = pd.read_parquet(ruta("interim", cfg) / "lineas.parquet")

    lineas_seudonimizadas(lineas, salt).to_parquet(ruta("interim", cfg) / "lineas_seudo.parquet", index=False)

    dest = ruta("processed", cfg)
    dest.mkdir(parents=True, exist_ok=True)
    # Por categoría solo si Lucía validó categorias.yaml (decisión: nivel público)
    mapa, validado = cargar_categorias()
    if validado:
        diarias = ventas_diarias(asignar_categoria(lineas, mapa), k, claves_extra=["categoria"])
    else:
        print("categorias.yaml sin validar: ventas_diarias.csv va solo por tipo de producto")
        diarias = ventas_diarias(lineas, k)
    semanal = particulares_semanal(lineas, k)
    meta = meta_ads_indice(pd.read_csv(ruta("meta_ads", cfg)))
    diario = particulares_diario(lineas, k)
    xl = xl_semanal(lineas)
    diario.to_csv(dest / "particulares_diario.csv", index=False)
    xl.to_csv(dest / "xl_semanal.csv", index=False)
    diarias.to_csv(dest / "ventas_diarias.csv", index=False)
    semanal.to_csv(dest / "particulares_semanal.csv", index=False)
    meta.to_csv(dest / "meta_ads_semanal_indice.csv", index=False)

    for nombre, df in [("ventas_diarias", diarias), ("particulares_semanal", semanal), ("meta_ads_semanal_indice", meta),
                       ("particulares_diario", diario), ("xl_semanal", xl)]:
        print(f"{nombre}.csv: {len(df)} filas | columnas: {list(df.columns)}")
