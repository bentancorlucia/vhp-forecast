"""Carga y limpieza de los exports de pedidos.

Cada fila de los exports es una LÍNEA DE PRODUCTO, no un pedido.
Un pedido se identifica por (segmento, nro_pedido, fecha_entrega): en empresas
el mismo número reaparece en meses consecutivos con otra fecha.

Los archivos de data/raw_private/ solo se leen; nunca se modifican.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from vhp.config import cargar_config, ruta

# Columnas que se conservan (con su nombre nuevo). Teléfono y empresa se
# guardan solo en data/interim/ (ignorado) para hashearlos en la fase 2.
COLUMNAS_USADAS = {
    "Nro de pedido": "nro_pedido",
    "Fecha de entrega": "fecha_entrega",
    "Teléfono": "telefono",
    "Empresa": "empresa",
    "Tipo de producto": "tipo_producto",
    "Producto solicitado": "producto",
    "Guarniciones": "guarnicion",
    "Salsa": "salsa",
    "Cantidad": "cantidad",
    "Precio unitario": "precio_unitario",
    "Importe": "importe",
}

PATRON_ARCHIVO = re.compile(r"^(\d{4})\.(\d{2})\s+VHP\s+(EMPRESAS|INDIVIDUALES)\.xlsx$")
SEGMENTO = {"EMPRESAS": "empresas", "INDIVIDUALES": "particulares"}


def listar_archivos(carpeta: Path) -> list[Path]:
    """Todos los .xlsx de pedidos que haya en la carpeta (no una lista fija)."""
    archivos = sorted(p for p in carpeta.glob("*.xlsx") if PATRON_ARCHIVO.match(p.name))
    if not archivos:
        raise FileNotFoundError(f"No hay exports de pedidos en {carpeta}")
    return archivos


def info_archivo(p: Path) -> tuple[pd.Period, str]:
    """Mes y segmento a partir del nombre del archivo."""
    m = PATRON_ARCHIVO.match(p.name)
    return pd.Period(f"{m.group(1)}-{m.group(2)}", freq="M"), SEGMENTO[m.group(3)]


def quitar_duplicados(crudo: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Elimina filas duplicadas exactas comparando TODAS las columnas originales.

    Se hace antes de descartar columnas: si se hiciera después, dos líneas
    distintas que solo difieren en una columna descartada pasarían por duplicadas.
    """
    dup = crudo.duplicated(keep="first")
    return crudo.loc[~dup].copy(), int(dup.sum())


def _a_entero(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.str.strip(), errors="coerce").astype("Int64")


def limpiar(crudo: pd.DataFrame, mes: pd.Period, segmento: str, archivo: str) -> pd.DataFrame:
    """Descarta columnas personales y no usadas, parsea tipos y marca XL."""
    df = crudo[list(COLUMNAS_USADAS)].rename(columns=COLUMNAS_USADAS)
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"].str.strip(), format="%d/%m/%Y", errors="coerce")
    for c in ["cantidad", "precio_unitario", "importe"]:
        df[c] = _a_entero(df[c])
    for c in ["nro_pedido", "tipo_producto", "producto", "guarnicion", "salsa", "empresa"]:
        df[c] = df[c].str.strip()
    # Teléfono normalizado: solo dígitos (para identificar clientes)
    df["telefono"] = df["telefono"].str.replace(r"\D", "", regex=True).replace("", pd.NA)
    df["es_xl"] = df["producto"].str.contains("[XL]", regex=False, na=False)
    df.insert(0, "segmento", segmento)
    df.insert(1, "mes_archivo", str(mes))
    df.insert(2, "archivo", archivo)
    return df


def calidad_archivo(df: pd.DataFrame, mes: pd.Period, n_crudas: int, n_dup: int) -> dict:
    """Indicadores de calidad de un archivo ya limpio."""
    fechas = df["fecha_entrega"]
    return {
        "archivo": df["archivo"].iat[0],
        "segmento": df["segmento"].iat[0],
        "mes": str(mes),
        "filas_crudas": n_crudas,
        "duplicados_exactos": n_dup,
        "filas_limpias": len(df),
        "fecha_min": fechas.min().date() if fechas.notna().any() else None,
        "fecha_max": fechas.max().date() if fechas.notna().any() else None,
        "fechas_invalidas": int(fechas.isna().sum()),
        "entregas_fuera_de_mes": int((fechas.dt.to_period("M") != mes).sum()),
        "domingos_descartados": int((fechas.dt.dayofweek == 6).sum()),
        "cantidad_no_positiva": int((df["cantidad"].fillna(0) <= 0).sum()),
        "telefono_vacio": int(df["telefono"].isna().sum()),
        "pct_precio_cero": round(100 * (df["precio_unitario"].fillna(0) == 0).mean(), 2),
        "importe_distinto_cant_x_precio": int((df["importe"] != df["cantidad"] * df["precio_unitario"]).fillna(True).sum()),
        "pct_xl": round(100 * df["es_xl"].mean(), 2),
    }


def meses_faltantes(meses: list[pd.Period], segmentos: list[str], tabla: pd.DataFrame,
                    fin_segmento: dict | None = None) -> list[str]:
    """Pares mes × segmento que faltan entre el primer y el último mes.

    `fin_segmento` ({segmento: fecha}): el segmento no tiene datos después de esa fecha
    (empresas desde septiembre 2026); esos meses no cuentan como faltantes."""
    esperados = pd.period_range(min(meses), max(meses), freq="M")
    presentes = set(zip(tabla["mes"], tabla["segmento"]))
    fin = {s: pd.Timestamp(f).to_period("M") for s, f in (fin_segmento or {}).items()}
    return [f"{m} {s}" for m in esperados for s in segmentos
            if (str(m), s) not in presentes and not (s in fin and m > fin[s])]


def cargar_lineas(carpeta: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lee todos los exports y devuelve (líneas limpias, tabla de calidad)."""
    cfg = cargar_config()
    carpeta = carpeta or ruta("raw_private", cfg)
    partes, calidad, meses = [], [], []
    fin = pd.Timestamp(cfg["periodo"]["fin"])
    for p in listar_archivos(carpeta):
        mes, segmento = info_archivo(p)
        crudo = pd.read_excel(p, dtype=str)
        sin_dup, n_dup = quitar_duplicados(crudo)
        df = limpiar(sin_dup, mes, segmento, p.name)
        fila = calidad_archivo(df, mes, len(crudo), n_dup)
        # El negocio cierra los domingos: esas líneas se descartan (decisión de Lucía)
        df = df[df["fecha_entrega"].dt.dayofweek != 6]
        # Corte del período: entregas posteriores al fin (pedidos ya cargados para días
        # futuros, ej.: noviembre 2026 exportado el 18/11) se descartan y se cuentan.
        posteriores = df["fecha_entrega"] > fin
        fila["posteriores_al_corte"] = int(posteriores.sum())
        df = df[~posteriores]
        fila["filas_limpias"] = len(df)
        partes.append(df)
        calidad.append(fila)
        meses.append(mes)
    lineas = pd.concat(partes, ignore_index=True)
    tabla = pd.DataFrame(calidad)
    faltan = meses_faltantes(meses, cfg["serie"]["segmentos"], tabla, cfg["serie"].get("fin_segmento"))
    tabla.attrs["meses_faltantes"] = faltan
    return lineas, tabla


def validar(lineas: pd.DataFrame, tabla: pd.DataFrame) -> list[str]:
    """Devuelve la lista de problemas encontrados (vacía si está todo bien)."""
    problemas = []
    if tabla.attrs.get("meses_faltantes"):
        problemas.append(f"Faltan meses: {tabla.attrs['meses_faltantes']}")
    for col in ["fechas_invalidas", "entregas_fuera_de_mes", "cantidad_no_positiva"]:
        malos = tabla.loc[tabla[col] > 0, "archivo"].tolist()
        if malos:
            problemas.append(f"{col}: {malos}")
    return problemas


def pedidos_semanales_particulares(lineas: pd.DataFrame) -> pd.DataFrame:
    """Pedidos y clientes nuevos de particulares por semana (lunes a domingo).

    Pedido = (nro_pedido, fecha_entrega). Cliente nuevo = teléfono cuyo primer
    pedido en TODOS los datos disponibles (desde 2025.05) cae en esa semana.
    """
    part = lineas[lineas["segmento"] == "particulares"]
    pedidos = part.drop_duplicates(["nro_pedido", "fecha_entrega"])[["nro_pedido", "fecha_entrega", "telefono"]]
    pedidos = pedidos.assign(semana_ini=pedidos["fecha_entrega"].dt.to_period("W-SUN").dt.start_time)
    n_ped = pedidos.groupby("semana_ini").size().rename("pedidos_particulares")
    primera = pedidos.dropna(subset=["telefono"]).groupby("telefono")["semana_ini"].min()
    n_nuevos = primera.value_counts().rename("clientes_nuevos_particulares")
    out = pd.concat([n_nuevos, n_ped], axis=1).fillna(0).astype(int)
    out.index.name = "semana_ini"
    return out.sort_index().reset_index()


def pedidos_diarios_particulares(lineas: pd.DataFrame) -> pd.DataFrame:
    """Clientes nuevos y pedidos de clientes que ya compraron, particulares, por día de entrega.

    Cliente nuevo = teléfono cuyo primer pedido (desde 2025.05) es ese día. Pedido de un
    cliente que ya compraron = pedido cuyo teléfono tuvo un pedido en una fecha anterior.
    Pedidos sin teléfono no entran en ninguna de las dos."""
    part = lineas[lineas["segmento"] == "particulares"]
    pedidos = (part.drop_duplicates(["nro_pedido", "fecha_entrega"])[["nro_pedido", "fecha_entrega", "telefono"]]
               .dropna(subset=["telefono"]))
    primera = pedidos.groupby("telefono")["fecha_entrega"].transform("min")
    nuevos = pedidos[pedidos["fecha_entrega"] == primera].drop_duplicates("telefono")
    recurrentes = pedidos[pedidos["fecha_entrega"] > primera]
    out = pd.concat([nuevos.groupby("fecha_entrega").size().rename("clientes_nuevos"),
                     recurrentes.groupby("fecha_entrega").size().rename("pedidos_recurrentes")], axis=1)
    out = out.fillna(0).astype(int).sort_index()
    out.index.name = "fecha"
    return out.reset_index()


def comparar_con_tablero(lineas: pd.DataFrame, ruta_tablero: Path | None = None) -> pd.DataFrame:
    """Diferencias semanales pipeline − Tablero. Se reportan, no se fuerzan."""
    tablero = pd.read_csv(ruta_tablero or ruta("tablero_control"), parse_dates=["semana_ini"])
    propio = pedidos_semanales_particulares(lineas)
    m = tablero.merge(propio, on="semana_ini", how="left", suffixes=("_tablero", "_pipeline"))
    for c in ["pedidos_particulares", "clientes_nuevos_particulares"]:
        m[f"{c}_pipeline"] = m[f"{c}_pipeline"].fillna(0).astype(int)
        m[f"dif_{c}"] = m[f"{c}_pipeline"] - m[f"{c}_tablero"]
        m[f"dif_pct_{c}"] = (100 * m[f"dif_{c}"] / m[f"{c}_tablero"]).round(1)
    return m


def preparar() -> None:
    """Fase 1 completa: carga, validación, guardado y control contra el Tablero."""
    cfg = cargar_config()
    lineas, tabla = cargar_lineas()
    problemas = validar(lineas, tabla)

    dir_interim = ruta("interim", cfg)
    dir_interim.mkdir(parents=True, exist_ok=True)
    lineas.to_parquet(dir_interim / "lineas.parquet", index=False)

    dir_tablas = ruta("tablas", cfg)
    dir_tablas.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(dir_tablas / "calidad_datos.csv", index=False)

    # El control usa conteos reales: queda en data/control/ (ignorado por git)
    control = comparar_con_tablero(lineas)
    control.to_csv(ruta("control", cfg) / "control_vs_tablero.csv", index=False)

    print(f"Archivos leídos: {len(tabla)} | filas crudas: {tabla.filas_crudas.sum()} | "
          f"duplicados eliminados: {tabla.duplicados_exactos.sum()} | domingos descartados: "
          f"{tabla.domingos_descartados.sum()} | filas limpias: {len(lineas)}")
    print("Problemas de validación:", problemas or "ninguno")
