"""Tests de la fase 4: agregación semanal y efectos de calendario del EDA."""
import numpy as np
import pandas as pd

from vhp import eda


def test_semanal_rotula_en_lunes_y_descarta_semanas_incompletas():
    idx = pd.DatetimeIndex(["2026-08-24", "2026-08-26", "2026-08-27", "2026-08-28", "2026-08-29", "2026-08-31"])
    s = eda.semanal(pd.Series([10, 20, 30, 40, 50, 999], index=idx))
    assert list(s.index) == [pd.Timestamp("2026-08-24")]  # lunes; la del 31/08 (1 día) queda afuera
    assert s.iat[0] == 30  # media por día hábil, no suma


def test_efectos_calendario_recupera_verano_y_feriado():
    idx = pd.bdate_range("2025-05-05", "2026-08-29", freq="C", weekmask="Mon Tue Wed Thu Fri Sat")
    cal = pd.DataFrame({"dia_semana": idx.dayofweek, "feriado_laborable": 0, "vispera_cierre": 0, "post_cierre": 0,
                        "verano": (idx.month == 1).astype(int)}, index=idx)
    cal.iloc[::40, cal.columns.get_loc("feriado_laborable")] = 1
    cal.iloc[5::60, cal.columns.get_loc("vispera_cierre")] = 1  # sin efecto, para que la matriz tenga rango completo
    cal.iloc[7::60, cal.columns.get_loc("post_cierre")] = 1
    t = np.arange(len(idx)) / 6
    y = 100 * 1.01 ** t * np.where(cal.verano == 1, 0.7, 1) * np.where(cal.feriado_laborable == 1, 0.8, 1)
    ancho = pd.DataFrame({c: y for c in eda.SERIES_PRINCIPALES}, index=idx)
    ef = eda.efectos_calendario(ancho, cal).query("serie == 'Total'").set_index("variable")["efecto_pct"]
    assert round(ef["verano"]) == -30 and round(ef["feriado_laborable"]) == -20
    assert round(ef["tendencia (por semana)"]) == 1
