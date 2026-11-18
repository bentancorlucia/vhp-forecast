# %% [markdown]
# # De platos a ingredientes (recetario)
# Lógica en `src/vhp/recetario.py`; mapeo plato vendido → receta en `config/recetas_map.yaml`.
# Cadena (solo multiplicaciones): plan por segmento × categoría (fase 9, porciones reales)
# → reparto entre platos (últimas 4 semanas, normal y XL) → gramos por ingrediente según la
# receta, abriendo las preparaciones base de forma recursiva → ÷ (1 − merma) → kg por
# ingrediente y por proveedor. Guarniciones: 250 g por vianda en los platos con acompañamiento.
#
# Recetas, gramos, mermas y proveedores son información comercial: la lista completa queda en
# `reports_private/` (ignorado por git). Al repo sube solo el índice por familia.
#
# `python main.py compras` regenera todo (necesita los datos privados y `python main.py plan`).

# %%
import sys
from pathlib import Path
RAIZ = Path.cwd().parent if Path.cwd().name == "analysis" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import pandas as pd
from vhp.config import ruta

pd.set_option("display.width", 200)
T, PRIV = ruta("tablas"), RAIZ / "reports_private"

# %% [markdown]
# ## 1. Resumen público e índice por familia

# %%
display(pd.read_csv(T / "compras_resumen.csv").T)
pd.read_csv(T / "compras_familia_indice.csv")

# %% [markdown]
# ## 2. Privado: platos sin receta y control de viandas repartidas

# %%
if PRIV.exists():
    display(pd.read_csv(PRIV / "platos_sin_receta.csv").head(15))
    display(pd.read_csv(PRIV / "control_compras.csv"))

# %% [markdown]
# ## 3. Privado: lista de compras por proveedor (kg o unidades)

# %%
if PRIV.exists():
    prov = sorted(PRIV.glob("lista_compras_proveedor_*.csv"))[-1]
    display(pd.read_csv(prov))
