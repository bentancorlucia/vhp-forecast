# %% [markdown]
# # Fase 6 — Clima → mix de categorías
# Lógica en `src/vhp/jerarquico.py` y `src/vhp/models/mix.py`.
# Backtest: mismos 12 orígenes que la fase 5 (sábados 22/08–07/11/2026); semanas
# pronosticadas 24/08–14/11/2026. Datos públicos (unidades × K): comparar con MASE,
# WAPE, participaciones y log loss por vianda (no dependen de K).
#
# `python main.py mix` regenera todo. Estas celdas leen las tablas guardadas.

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
# ## 1. Efecto de la temperatura en el mix (todo el período, 06/05/2025–14/11/2026)
# Multinomial con día de la semana, verano, temperatura máxima y precipitación.
# Mix promedio si todos los días hubieran tenido frío (p10 de la temperatura máxima)
# vs. calor (p90). IC 95 % por bootstrap de bloques semanales.

# %%
pd.read_csv(T / "mix_efecto_temperatura.csv").round(2)

# %%
display(Image(FIG / "08_mix_efecto_temperatura.png"))

# %% [markdown]
# ## 2. ¿El clima mejora el pronóstico de las participaciones? (backtest 24/08–14/11/2026)

# %%
pd.read_csv(T / "mix_metricas_participacion.csv").round(4)

# %%
pd.read_csv(T / "mix_dm_participacion.csv").round(3)

# %%
display(Image(FIG / "09_mix_backtest_particulares.png"))

# %% [markdown]
# ## 3. Unidades por categoría = segmento (lgbm_directo) × participación (backtest 24/08–14/11/2026)
# Modelo = modelo de participaciones; en nivel segmento, lgbm_directo. Intervalo 80 %:
# ŷ × percentiles 10/90 de y/ŷ de la misma serie en los 12 orígenes previos.

# %%
pd.read_csv(T / "mix_metricas_unidades.csv").round(3)
