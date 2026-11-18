# %% [markdown]
# # Fase 9 — Plan de compras (gancho 4)
# Lógica en `src/vhp/decision.py`. Compra **semanal** (los 6 días) por segmento × categoría.
# Pronóstico: lgbm_directo por segmento × participación media de 4 semanas.
# Plan = pronóstico × percentil p del cociente real / pronóstico de las 12 semanas previas
# (se juntan las 7 categorías del segmento). Se prueban p = 40…95 y se elige el de menor
# costo simulado (sobrante $200, faltante $150 por vianda, `config.yaml`); 80/90/95 de referencia.
# Backtest: 12 orígenes, semanas 24/08–14/11/2026, los dos segmentos (se pronostican además las 12 semanas
# anteriores para tener errores previos). Referencia: naive estacional con el mismo colchón.
# Unidades × K: % de sobrante/faltante, coberturas y costo por vianda no dependen de K.
#
# `python main.py plan` regenera todo. Estas celdas leen las tablas guardadas.

# %%
import sys
from pathlib import Path
RAIZ = Path.cwd().parent if Path.cwd().name == "analysis" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import pandas as pd
from IPython.display import Image, display
from vhp.config import ruta

pd.set_option("display.width", 200)
T, FIG = ruta("tablas"), ruta("figuras")

# %% [markdown]
# ## 1. Costo simulado según el colchón (backtest 24/08–14/11/2026)

# %%
pd.read_csv(T / "plan_curva_costo.csv").round(3)

# %%
display(Image(FIG / "12_plan_compras.png"))

# %% [markdown]
# ## 2. p elegido y referencias 80/90/95

# %%
pd.read_csv(T / "plan_simulacion.csv").round(3)

# %% [markdown]
# ## 3. Sensibilidad al costo de faltante (se vuelve a elegir p con cada costo)

# %%
pd.read_csv(T / "plan_sensibilidad_costo.csv").round(3)

# %% [markdown]
# ## 4. Plan para la semana 16/11–21/11/2026 (porciones × K, una compra semanal)

# %%
pd.read_csv(T / "plan_semana_siguiente.csv")
