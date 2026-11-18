"""Índice de días hábiles y variables de calendario.

Día hábil = lunes a sábado que no es feriado NO laborable. Los feriados
laborables (Carnaval, Turismo, etc.) son días hábiles: el negocio abrió en
todos los del período (verificado en fase 3). Los días cerrados no son ceros:
no existen en la serie.

Todas las variables dependen solo de la fecha, así que se conocen de antemano
(sirven como exógenas en el pronóstico sin leakage).
"""
from __future__ import annotations

import pandas as pd

from vhp.external import feriados


def tabla_feriados(inicio, fin) -> pd.DataFrame:
    """Feriados UY entre inicio y fin (con un margen de un año por las vísperas)."""
    inicio, fin = pd.Timestamp(inicio), pd.Timestamp(fin)
    return feriados(list(range(inicio.year - 1, fin.year + 2)))


def dias_habiles(inicio, fin, fer: pd.DataFrame | None = None) -> pd.DatetimeIndex:
    """Lunes a sábado entre inicio y fin, sin feriados no laborables."""
    fer = tabla_feriados(inicio, fin) if fer is None else fer
    cerrados = set(fer.loc[fer["tipo"] == "no_laborable", "fecha"])
    dias = pd.date_range(inicio, fin, freq="D")
    return pd.DatetimeIndex([d for d in dias if d.dayofweek <= 5 and d not in cerrados], name="fecha")


def dias_sin_entregas(lineas: pd.DataFrame, indice: pd.DatetimeIndex,
                      cierres_segmento: dict | None = None) -> pd.DataFrame:
    """Días hábiles sin ninguna entrega, en total y por segmento.

    Cada segmento se mira desde su primera hasta su última entrega (empresas no tiene
    datos desde septiembre 2026: esos días no son días sin entregas). Es para que Lucía confirme
    si fueron cierres o días con cero ventas reales. La columna `cierre_confirmado`
    marca los que ya están en config.yaml (serie.cierres_segmento).
    """
    confirmados = {(s, pd.Timestamp(f)) for s, fs in (cierres_segmento or {}).items() for f in fs}
    filas = []
    grupos = [("total", lineas)] + list(lineas.groupby("segmento"))
    for nombre, df in grupos:
        con = set(df["fecha_entrega"].unique())
        desde, hasta = df["fecha_entrega"].min(), df["fecha_entrega"].max()
        for d in indice[(indice >= desde) & (indice <= hasta)]:
            if d not in con:
                filas.append({"fecha": d.date(), "dia": d.day_name(), "segmento": nombre,
                              "cierre_confirmado": (nombre, d) in confirmados})
    return pd.DataFrame(filas, columns=["fecha", "dia", "segmento", "cierre_confirmado"])


def variables_calendario(indice: pd.DatetimeIndex, fer: pd.DataFrame | None = None,
                         meses_verano: tuple[int, ...] = (1,)) -> pd.DataFrame:
    """Variables de calendario para cada día hábil del índice.

    - dia_semana: 0 = lunes … 5 = sábado.
    - feriado_laborable: el día es feriado pero se abre (Carnaval, Turismo, 18/5…).
    - carnaval, turismo: días de Carnaval y de la Semana de Turismo.
    - vispera_cierre: el próximo lunes-a-sábado es un feriado no laborable
      (al día siguiente no hay entregas: se puede adelantar demanda).
    - post_cierre: el lunes-a-sábado anterior fue un feriado no laborable.
    - verano: el día cae en enero (decisión de Lucía: la caída de enero se
      trata como estacionalidad de verano, no como quiebre).
    """
    indice = pd.DatetimeIndex(indice, name="fecha")
    fer = tabla_feriados(indice.min(), indice.max()) if fer is None else fer
    nombres = fer.set_index("fecha")["nombre"]
    laborables = set(fer.loc[fer["tipo"] == "laborable", "fecha"])
    cerrados = set(fer.loc[fer["tipo"] == "no_laborable", "fecha"])

    def siguiente_lun_sab(d, paso):
        d = d + pd.Timedelta(int(paso), unit="D")
        return d + pd.Timedelta(int(paso), unit="D") if d.dayofweek == 6 else d

    out = pd.DataFrame(index=indice)
    out["dia_semana"] = indice.dayofweek
    out["feriado_laborable"] = indice.isin(laborables).astype(int)
    nom = pd.Series(indice.map(lambda d: nombres.get(d, "")), index=indice).astype(str)
    out["carnaval"] = nom.str.contains("Carnaval").astype(int)
    out["turismo"] = nom.str.contains("Turismo").astype(int)
    out["vispera_cierre"] = [int(siguiente_lun_sab(d, 1) in cerrados) for d in indice]
    out["post_cierre"] = [int(siguiente_lun_sab(d, -1) in cerrados) for d in indice]
    out["verano"] = indice.month.isin(meses_verano).astype(int)
    return out.reset_index()


def calendario() -> None:
    """Fase 3: feriados, índice de días hábiles, variables y días sin entregas.

    Salidas: data/external/feriados_uy.csv, data/processed/calendario.csv (públicos)
    y reports/tables/dias_sin_entregas.csv. El índice va desde la primera entrega
    hasta el fin del período de config.yaml.
    """
    from vhp.config import cargar_config, ruta

    cfg = cargar_config()
    lineas = pd.read_parquet(ruta("interim", cfg) / "lineas.parquet", columns=["segmento", "fecha_entrega"])
    inicio, fin = lineas["fecha_entrega"].min(), pd.Timestamp(cfg["periodo"]["fin"])
    fer = tabla_feriados(inicio, fin)

    cal = variables_calendario(dias_habiles(inicio, fin, fer), fer, tuple(cfg["serie"]["meses_verano"]))
    cierres = cfg["serie"].get("cierres_segmento", {})
    for seg, fechas in cierres.items():  # exógena para el Total: ese día falta un segmento
        cal[f"cierre_{seg}"] = cal["fecha"].isin(pd.to_datetime(fechas)).astype(int)
    sin = dias_sin_entregas(lineas, pd.DatetimeIndex(cal["fecha"]), cierres)

    for clave in ["external", "processed", "tablas"]:
        ruta(clave, cfg).mkdir(parents=True, exist_ok=True)
    fer.to_csv(ruta("external", cfg) / "feriados_uy.csv", index=False)
    cal.to_csv(ruta("processed", cfg) / "calendario.csv", index=False)
    sin.to_csv(ruta("tablas", cfg) / "dias_sin_entregas.csv", index=False)

    print(f"Días hábiles: {len(cal)} ({cal.fecha.min().date()} a {cal.fecha.max().date()}) | "
          f"feriados laborables: {cal.feriado_laborable.sum()} | días de verano: {cal.verano.sum()} | días hábiles sin entregas: {len(sin)}")
    if len(sin):
        print(sin.to_string(index=False))
