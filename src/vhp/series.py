"""Categorías de plato y series jerárquicas de viandas.

Jerarquía: Total → segmento (particulares / empresas) → segmento/categoría.
Las series están en días hábiles; un día hábil sin ventas de una categoría es
un cero real (el negocio abrió). Formato largo (unique_id, ds, y), más la
matriz de sumas S y los tags.
"""
from __future__ import annotations

import pandas as pd
import yaml

from vhp.config import RAIZ

TOTAL = "Total"
RUTA_CATEGORIAS = RAIZ / "config" / "categorias.yaml"


def cargar_categorias(ruta=RUTA_CATEGORIAS) -> tuple[dict[str, str], bool]:
    """Lee categorias.yaml. Devuelve (plato → categoría, validado)."""
    with open(ruta, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    mapa = {}
    for cat, platos in cfg["categorias"].items():
        for p in platos:
            if p in mapa:
                raise ValueError(f"Plato en dos categorías: {p} ({mapa[p]} y {cat})")
            mapa[p] = cat
    return mapa, bool(cfg.get("validado", False))


def plato_base(producto: pd.Series) -> pd.Series:
    """Nombre del plato sin el sufijo [XL]."""
    return producto.str.replace(r"\s*\[XL\]\s*", "", regex=True).str.strip()


def asignar_categoria(lineas: pd.DataFrame, mapa: dict[str, str]) -> pd.DataFrame:
    """Agrega la columna `categoria`.

    Viandas: según el mapa (falla si hay platos sin categoría, para no perder
    unidades en silencio). Otros tipos: el tipo en minúscula (postre, pan…).
    """
    out = lineas.copy()
    es_vianda = out["tipo_producto"] == "Vianda"
    base = plato_base(out["producto"])
    sin = sorted(set(base[es_vianda]) - set(mapa))
    if sin:
        raise ValueError(f"Platos sin categoría en categorias.yaml: {sin}")
    out["categoria"] = out["tipo_producto"].str.lower()
    out.loc[es_vianda, "categoria"] = base[es_vianda].map(mapa)
    return out


def _id(*partes: str) -> str:
    return "/".join(partes)


def jerarquia(diarias: pd.DataFrame, indice: pd.DatetimeIndex,
              cierres_segmento: dict[str, list] | None = None, fin_segmento: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Series jerárquicas de viandas sobre el índice de días hábiles.

    `diarias` tiene columnas fecha, segmento, tipo_producto, categoria, unidades
    (por ejemplo data/processed/ventas_diarias.csv). Devuelve:
    - Y: formato largo unique_id, ds, y (todos los niveles).
    - S: matriz de sumas (filas = todas las series, columnas = series de abajo).
    - tags: nivel → lista de unique_id.

    `cierres_segmento` ({segmento: [fechas]}): días en que cerró un solo segmento.
    Esas filas se sacan de las series del segmento y sus categorías (el día no
    existe para ellas); el Total sí lo conserva, con lo que vendió el otro segmento.

    `fin_segmento` ({segmento: fecha}): último día con datos del segmento (empresas
    termina el 31/08/2026). Después de esa fecha se sacan las filas del segmento, de sus
    categorías y del Total (sin ese segmento el Total no se puede calcular): no son ceros.
    """
    v = diarias[diarias["tipo_producto"] == "Vianda"]
    fuera = set(pd.to_datetime(v["fecha"])) - set(indice)
    if fuera:
        raise ValueError(f"Hay ventas en días fuera del índice: {sorted(fuera)[:5]}")
    abajo = v.assign(unique_id=[_id(TOTAL, s, c) for s, c in zip(v["segmento"], v["categoria"])])
    ancho = (abajo.assign(fecha=pd.to_datetime(abajo["fecha"]))
             .pivot_table(index="fecha", columns="unique_id", values="unidades", aggfunc="sum"))
    ancho = ancho.reindex(indice, fill_value=0).fillna(0).sort_index(axis=1)

    hojas = list(ancho.columns)
    segmentos = sorted({h.split("/")[1] for h in hojas})
    filas = [TOTAL] + [_id(TOTAL, s) for s in segmentos] + hojas
    S = pd.DataFrame(0, index=filas, columns=hojas, dtype=int)
    S.loc[TOTAL] = 1
    for s in segmentos:
        S.loc[_id(TOTAL, s), [h for h in hojas if h.split("/")[1] == s]] = 1
    for h in hojas:
        S.loc[h, h] = 1

    todas = ancho @ S.T  # cada columna = suma de sus hojas
    Y = (todas.rename_axis(index="ds", columns="unique_id").stack().rename("y").reset_index()
         [["unique_id", "ds", "y"]])
    for seg, fechas in (cierres_segmento or {}).items():
        fechas = pd.to_datetime(fechas)
        vendio = ancho.loc[ancho.index.isin(fechas), [h for h in hojas if h.split("/")[1] == seg]].to_numpy().sum()
        if vendio:
            raise ValueError(f"{seg} tiene ventas en un día marcado como cierre")
        del_seg = Y["unique_id"].str.startswith(_id(TOTAL, seg)) & Y["ds"].isin(fechas)
        Y = Y.loc[~del_seg].reset_index(drop=True)
    for seg, fin in (fin_segmento or {}).items():
        fin = pd.Timestamp(fin)
        fuera_seg = ((Y["unique_id"].str.startswith(_id(TOTAL, seg)) | (Y["unique_id"] == TOTAL))
                     & (Y["ds"] > fin))
        Y = Y.loc[~fuera_seg].reset_index(drop=True)
    tags = {"total": [TOTAL], "total/segmento": [_id(TOTAL, s) for s in segmentos], "total/segmento/categoria": hojas}
    return Y, S, tags
