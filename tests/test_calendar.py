"""Tests de la fase 3: índice de días hábiles y variables de calendario."""
import pandas as pd
import pytest

from vhp import calendar as cal
from vhp.config import ruta

CALENDARIO = ruta("processed") / "calendario.csv"
LINEAS = ruta("interim") / "lineas.parquet"


def test_indice_sin_domingos_ni_feriados_no_laborables():
    fer = cal.tabla_feriados("2025-01-01", "2026-12-31")
    idx = cal.dias_habiles("2025-01-01", "2026-12-31", fer)
    assert not (idx.dayofweek == 6).any()
    assert not idx.isin(fer.loc[fer.tipo == "no_laborable", "fecha"]).any()
    # Los laborables (Carnaval 16/02/2026) sí son días hábiles
    assert pd.Timestamp("2026-02-16") in idx
    assert pd.Timestamp("2026-05-01") not in idx and pd.Timestamp("2026-08-25") not in idx


def test_vispera_y_post_cierre_saltan_el_domingo():
    fer = cal.tabla_feriados("2026-08-01", "2026-08-31")
    idx = cal.dias_habiles("2026-07-01", "2026-07-31", fer)
    v = cal.variables_calendario(idx, fer).set_index("fecha")
    # 18/07/2026 es sábado no laborable: víspera el viernes 17, post el lunes 20
    assert v.loc["2026-07-17", "vispera_cierre"] == 1
    assert v.loc["2026-07-20", "post_cierre"] == 1
    assert v[["vispera_cierre", "post_cierre"]].sum().tolist() == [1, 1]


def test_verano_es_enero():
    idx = cal.dias_habiles("2025-12-29", "2026-02-02")
    v = cal.variables_calendario(idx).set_index("fecha")["verano"]
    assert v["2025-12-31"] == 0 and v["2026-01-02"] == 1 and v["2026-01-31"] == 1 and v["2026-02-02"] == 0


@pytest.mark.skipif(not (CALENDARIO.exists() and LINEAS.exists()), reason="correr main.py prepare calendar")
def test_todas_las_entregas_caen_en_dias_habiles():
    idx = pd.DatetimeIndex(pd.read_csv(CALENDARIO, parse_dates=["fecha"])["fecha"])
    fechas = pd.read_parquet(LINEAS, columns=["fecha_entrega"])["fecha_entrega"].unique()
    assert pd.DatetimeIndex(fechas).isin(idx).all()
