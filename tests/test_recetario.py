"""Tests del paso de platos a ingredientes (recetario) con un recetario sintético."""
import numpy as np
import pandas as pd
import pytest

from vhp import recetario as rc


def _rec():
    platos = pd.DataFrame([
        # plato, porciones_lote, peso_porcion_g, salsa, ingrediente, clave, cantidad, unidad
        ("Pollo con salsa", 1, 300, 0, "Pechuga", "Pechuga (X)", 200.0, "g"),
        ("Pollo con salsa", 1, 300, 0, "Salsa Blanca", "Salsa Blanca", 100.0, "g"),
        ("Guiso", 10, 400, 0, "Carne", "Carne (X)", 2000.0, "g"),          # lote de 10
        ("Guiso XL", 1, 520, 0, "Carne", "Carne (X)", 300.0, "g"),
        ("Empanadas", 1, 0, 0, "Empanadas", "Empanadas (Y)", 4.0, "unidad"),
        ("Fideos", 1, 300, 0, "Spaghetti", "Spaghetti (Z)", 100.0, "g"),
        ("Fideos", 1, 300, 0, "Cerveza", "Cerveza", 10.0, "g"),            # sin match
    ], columns=["plato", "porciones_lote", "peso_porcion_g", "salsa_promedio_g", "ingrediente", "clave",
                "cantidad", "unidad"])
    bases = pd.DataFrame([
        # salsa blanca lleva otra base (roux): apertura recursiva; rinde 500 g reales
        ("Salsa Blanca", 600.0, 500.0, "Leche", "Leche (W)", 400.0, "g"),
        ("Salsa Blanca", 600.0, 500.0, "Roux", "Roux", 100.0, "g"),
        ("Roux", 100.0, 100.0, "Harina", "Harina (W)", 50.0, "g"),
        ("Roux", 100.0, 100.0, "Manteca", "Manteca (W)", 50.0, "g"),
        ("Pure", 1000.0, 1000.0, "Papa", "Papa (W)", 1000.0, "g"),
    ], columns=["preparacion", "rendimiento_teorico_g", "rendimiento_real_g", "ingrediente", "clave",
                "cantidad", "unidad"])
    ing = pd.DataFrame([
        ("pechuga", "Pechuga", "P1", 0.2, "Carnes"), ("carne", "Carne", "P1", 0.2, "Carnes"),
        ("leche", "Leche", "P2", 0.0, "Lacteos"), ("harina", "Harina", "P2", 0.02, "Secos"),
        ("manteca", "Manteca", "P2", 0.0, "Lacteos"), ("empanadas", "Empanadas", "P3", 0.0, "Porcionado"),
        ("spaghetti", "Spaghetti", "P2", -1.5, "Pastas"), ("papa", "Papa", "P4", 0.2, "Verdura"),
    ], columns=["ingrediente_clave", "producto", "proveedor", "merma", "familia"])
    return {"platos": platos, "bases": bases, "ing": ing}


def test_normaliza_acentos_y_mayusculas():
    assert rc.norm("  Puré  de Papas ") == "pure de papas"


def test_bases_se_abren_recursivo_y_por_rendimiento_real():
    rec = _rec()
    res = rc.Resolutor(rec)
    d = rc.explotar_plato("Pollo con salsa", rec, res).groupby("ingrediente")["cantidad"].sum()
    # 100 g de salsa / 500 g de rendimiento real = 0,2 del lote: 80 g leche y 20 g de roux (10 + 10)
    assert np.isclose(d["leche"], 80) and np.isclose(d["harina"], 10) and np.isclose(d["manteca"], 10)
    assert np.isclose(d["pechuga"], 200)


def test_lote_se_divide_por_porciones_y_xl():
    rec = _rec()
    res = rc.Resolutor(rec)
    assert np.isclose(rc.explotar_plato("Guiso", rec, res)["cantidad"].sum(), 200)  # 2000 / 10
    mapa = {"platos": {"Guiso": "Guiso", "Pollo con salsa": "Pollo con salsa"}}
    recetas = set(rec["platos"]["plato"])
    assert rc.receta_de("Guiso", True, mapa, recetas, 1.3) == ("Guiso XL", 1.0, "XL con receta propia")
    r, f, nota = rc.receta_de("Pollo con salsa", True, mapa, recetas, 1.3)
    assert r == "Pollo con salsa" and f == 1.3 and nota.startswith("supuesto")


def _cadena(columnas=("pronostico",)):
    rec = _rec()
    res = rc.Resolutor(rec)
    mapa = {"platos": {"Pollo con salsa": "Pollo con salsa", "Guiso": "Guiso", "Empanadas": "Empanadas",
                       "Fideos": "Fideos", "Plato nuevo": rc.SIN_RECETA}}
    plan = pd.DataFrame({"segmento": "s", "categoria": ["a", "b"], "pronostico": [100.0, 50.0]})
    reparto = pd.DataFrame({"segmento": "s", "categoria": ["a", "a", "a", "b", "b"],
                            "plato": ["Pollo con salsa", "Guiso", "Plato nuevo", "Empanadas", "Fideos"],
                            "es_xl": [False, True, False, False, False],
                            "participacion": [0.5, 0.3, 0.2, 0.6, 0.4]})
    up = rc.unidades_por_plato(plan, list(columnas), reparto)
    rep_g = pd.DataFrame({"segmento": ["s"], "base": ["Pure"], "participacion": [1.0]})
    acomp = pd.DataFrame({"segmento": ["s"], "plato": ["Guiso"], "con_acompaniamiento": [True]})
    out = rc.lista_compras(up, list(columnas), rec, res, mapa, rep_g, acomp, 250, 1.3)
    lista, avisos = rc.con_merma(out["detalle"], list(columnas), rec["ing"])
    return rec, plan, up, out, lista, avisos + out["avisos"]


def test_todas_las_viandas_se_reparten_y_las_sin_receta_se_reportan():
    _, plan, up, out, _, _ = _cadena()
    assert np.isclose(up["pronostico"].sum(), plan["pronostico"].sum())
    u = out["unidades"]
    assert np.isclose(u.loc[u["receta"] == rc.SIN_RECETA, "pronostico"].sum(), 20)  # 100 × 0,2


def test_kg_igual_a_unidades_por_gramos_sobre_merma():
    rec, _, up, _, lista, avisos = _cadena()
    kg = lista.set_index("ingrediente")["pronostico"]
    # pechuga: 50 viandas × 200 g ÷ (1 − 0,2)
    assert np.isclose(kg["pechuga"], 50 * 200 / 0.8 / 1000)
    # carne: 30 viandas XL con receta propia (300 g) ÷ 0,8
    assert np.isclose(kg["carne"], 30 * 300 / 0.8 / 1000)
    # papa (guarnición del guiso, XL × 1,3): 30 × 1,3 × 250 g ÷ 0,8
    assert np.isclose(kg["papa"], 30 * 1.3 * 250 / 0.8 / 1000)
    # empanadas en unidades: 30 viandas × 4
    fila = lista[lista["ingrediente"] == "empanadas"].iloc[0]
    assert fila["unidad"] == "unidad" and np.isclose(fila["pronostico"], 120)
    # spaghetti: merma negativa → peso seco sin dividir, y se avisa
    assert np.isclose(kg["spaghetti"], 20 * 100 / 1000)
    assert any("Merma negativa" in a for a in avisos)
    assert any("Cerveza" in a for a in avisos)


def test_ciclo_de_bases_falla():
    rec = _rec()
    rec["bases"] = pd.concat([rec["bases"], pd.DataFrame([("Roux", 100.0, 100.0, "Salsa Blanca", "x", 10.0, "g")],
                                                          columns=rec["bases"].columns)])
    with pytest.raises(RecursionError):
        rc.explotar_plato("Pollo con salsa", rec, rc.Resolutor(rec))


def test_guarniciones_se_separan_por_unidad():
    s = pd.Series(["Puré de papas, Puré de papas", None, "Arroz"])
    assert list(rc.separar_guarniciones(s)) == ["Puré de papas", "Puré de papas", "Arroz"]


def test_mapa_del_repo_cubre_los_platos_y_apunta_a_recetas():
    """recetas_map.yaml: todo destino es SIN_RECETA o un nombre de receta (si hay recetario)."""
    mapa = rc.cargar_mapa()
    assert mapa["platos"]
    from vhp.config import ruta
    if not (ruta("recetario") / "recetas_platos.csv").exists():
        pytest.skip("sin recetario privado")
    recetas = set(rc.cargar_recetario()["platos"]["plato"])
    malos = [p for p, r in mapa["platos"].items() if r != rc.SIN_RECETA and r not in recetas]
    assert not malos
