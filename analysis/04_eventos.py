# %% [markdown]
# # Fase 7 — Efecto de eventos (contrafactual + placebo)
# Lógica en `src/vhp/intervention.py`; fechas en `config/eventos.yaml` (confirmadas por Lucía).
# SARIMA (statsmodels, grilla por AIC) entrenado solo con datos previos a cada evento; 1000 caminos simulados del
# período posterior; efecto = observado − contrafactual, con intervalo 95 %.
# Viandas: efecto relativo (%); tasas por vianda: efecto absoluto. Datos públicos (× K).
#
# `python main.py eventos` regenera todo (unos 2 minutos).

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
# ## 1. Efectos

# %%
pd.read_csv(T / "eventos_efectos.csv", parse_dates=["desde", "hasta"]).round(3)

# %%
display(Image(FIG / "10_eventos.png"))

# %% [markdown]
# ## 2. Placebos (fechas falsas anteriores a cada evento)

# %%
pd.read_csv(T / "eventos_placebo.csv").round(3)
