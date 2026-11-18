"""Tests de la fase 1 (carga y limpieza).

Los tests con datos reales se saltean si no existe data/interim/lineas.parquet
(por ejemplo, en un clon público del repo sin los datos privados).
"""
import pandas as pd
import pytest

from vhp import load
from vhp.config import ruta

LINEAS = ruta("interim") / "lineas.parquet"
CALIDAD = ruta("tablas") / "calidad_datos.csv"
CONTROL = ruta("control") / "control_vs_tablero.csv"
hay_datos = pytest.mark.skipif(not LINEAS.exists(), reason="faltan datos privados (correr main.py prepare)")


def _crudo(filas):
    cols = list(load.COLUMNAS_USADAS) + ["Nombre", "Notas"]
    return pd.DataFrame(filas, columns=cols, dtype=str)


BASE = ["1", "3/8/2026", "000 000-001", None, "Vianda", "Pollo [XL]", "Arroz", None, "2", "415", "830", "Ana", None]


def test_duplicados_se_comparan_con_todas_las_columnas():
    # Fila 2 = copia exacta de la 1; fila 3 solo difiere en una columna que después se descarta (Notas)
    otra = BASE[:-1] + ["sin cebolla"]
    sin_dup, n = load.quitar_duplicados(_crudo([BASE, BASE, otra]))
    assert n == 1
    assert len(sin_dup) == 2


def test_limpiar_parsea_y_descarta_columnas_personales():
    df = load.limpiar(_crudo([BASE]), pd.Period("2026-08", "M"), "particulares", "x.xlsx")
    assert "Nombre" not in df and "Notas" not in df
    assert df["fecha_entrega"].iat[0] == pd.Timestamp("2026-08-03")  # d/m/aaaa
    assert df["telefono"].iat[0] == "000000001"
    assert bool(df["es_xl"].iat[0])
    assert df["importe"].iat[0] == 830


def test_meses_faltantes():
    tabla = pd.DataFrame({"mes": ["2026-01", "2026-01", "2026-03"], "segmento": ["empresas", "particulares", "empresas"]})
    meses = [pd.Period(m, "M") for m in tabla["mes"]]
    faltan = load.meses_faltantes(meses, ["particulares", "empresas"], tabla)
    assert faltan == ["2026-02 particulares", "2026-02 empresas", "2026-03 particulares"]


@hay_datos
def test_no_quedan_duplicados_exactos():
    t = pd.read_csv(CALIDAD)
    assert (t["filas_crudas"] - t["duplicados_exactos"] - t["domingos_descartados"] - t["posteriores_al_corte"]
            == t["filas_limpias"]).all()
    assert len(pd.read_parquet(LINEAS)) == t["filas_limpias"].sum()


@hay_datos
def test_validaciones_de_datos_reales():
    l = pd.read_parquet(LINEAS)
    assert l["fecha_entrega"].notna().all()
    assert (l["cantidad"] > 0).all()
    assert not (l["fecha_entrega"].dt.dayofweek == 6).any()  # sin domingos
    assert (l["fecha_entrega"].dt.to_period("M").astype(str) == l["mes_archivo"]).all()
    personales = {"Nombre", "Email", "Dirección de entrega", "Notas", "Sucursal", "Fecha de nacimiento"}
    assert not personales & set(l.columns)


@hay_datos
def test_control_contra_tablero_cubre_todas_las_semanas():
    """No fuerza igualdad: verifica que las diferencias estén reportadas para cada semana."""
    c = pd.read_csv(CONTROL)
    tablero = pd.read_csv(ruta("tablero_control"))
    assert len(c) == len(tablero)
    assert c["dif_pedidos_particulares"].notna().all()
    assert c["dif_clientes_nuevos_particulares"].notna().all()


def test_meses_faltantes_respeta_fin_de_segmento():
    tabla = pd.DataFrame({"mes": ["2026-08", "2026-08", "2026-09"], "segmento": ["empresas", "particulares", "particulares"]})
    meses = [pd.Period("2026-08", "M"), pd.Period("2026-09", "M")]
    assert load.meses_faltantes(meses, ["particulares", "empresas"], tabla) == ["2026-09 empresas"]
    assert load.meses_faltantes(meses, ["particulares", "empresas"], tabla, {"empresas": "2026-08-31"}) == []


@hay_datos
def test_no_hay_entregas_posteriores_al_corte():
    from vhp.config import cargar_config
    lineas = pd.read_parquet(LINEAS, columns=["fecha_entrega"])
    assert lineas["fecha_entrega"].max() <= pd.Timestamp(cargar_config()["periodo"]["fin"])
