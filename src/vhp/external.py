"""Datos externos públicos: feriados de Uruguay (y clima, en la fase 4).

Los feriados salen de la librería `holidays`. Hay dos categorías:
- `public`: feriados no laborables (1/1, 1/5, 18/7, 25/8, 25/12). El negocio CIERRA.
- `bank`: feriados laborables (Carnaval, Turismo, 6/1, 19/4, 18/5, 19/6, 12/10, 2/11).
  El negocio ABRE (verificado en fase 3: hubo entregas en todos los del período).
"""
from __future__ import annotations

import holidays
import pandas as pd


def feriados(anios: list[int], pais: str = "UY") -> pd.DataFrame:
    """Tabla de feriados con columnas fecha, nombre, tipo ('no_laborable' o 'laborable').

    Si una fecha está en las dos categorías, manda 'no_laborable'.
    """
    pub = holidays.country_holidays(pais, years=anios, categories=("public",))
    todos = holidays.country_holidays(pais, years=anios, categories=("public", "bank"))
    filas = [{"fecha": pd.Timestamp(d), "nombre": n, "tipo": "no_laborable" if d in pub else "laborable"}
             for d, n in sorted(todos.items())]
    return pd.DataFrame(filas)


URL_OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"


def descargar_clima(inicio, fin, latitud: float, longitud: float, variables: list[str],
                    zona_horaria: str) -> pd.DataFrame:
    """Clima diario observado de Open-Meteo (Historical Weather API).

    Es dato OBSERVADO, no pronóstico: en producción iría el pronóstico del tiempo.
    Devuelve fecha + una columna por variable.
    """
    import requests

    params = {"latitude": latitud, "longitude": longitud,
              "start_date": pd.Timestamp(inicio).strftime("%Y-%m-%d"),
              "end_date": pd.Timestamp(fin).strftime("%Y-%m-%d"),
              "daily": ",".join(variables), "timezone": zona_horaria}
    r = requests.get(URL_OPEN_METEO, params=params, timeout=60)
    r.raise_for_status()
    d = r.json()["daily"]
    out = pd.DataFrame(d).rename(columns={"time": "fecha"})
    out["fecha"] = pd.to_datetime(out["fecha"])
    faltan = out[variables].isna().sum()
    if faltan.any():
        raise ValueError(f"Open-Meteo devolvió vacíos: {faltan[faltan > 0].to_dict()}")
    return out


def clima() -> None:
    """Baja el clima del período de config.yaml a data/external/clima_montevideo.csv."""
    from vhp.config import cargar_config, ruta

    cfg = cargar_config()
    c = cfg["clima"]
    df = descargar_clima(cfg["periodo"]["inicio"], cfg["periodo"]["fin"], c["latitud"], c["longitud"],
                         c["variables"], c["zona_horaria"])
    destino = ruta("external", cfg) / "clima_montevideo.csv"
    df.to_csv(destino, index=False)
    print(f"Clima: {len(df)} días ({df.fecha.min().date()} a {df.fecha.max().date()}) → {destino.name}")
