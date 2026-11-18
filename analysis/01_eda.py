# %% [markdown]
# # Fase 4 — Análisis exploratorio
# Lógica en `src/vhp/eda.py`; las figuras van a `reports/figures/` y las tablas a `reports/tables/`.
# Datos públicos de `data/processed/` (unidades × K: los niveles no son reales, los cocientes y tests sí).
# Período: entregas del 06/05/2025 al 14/11/2026, en días hábiles.
#
# Antes de correr: `python main.py calendar clima` (o `all`).

# %%
import sys
from pathlib import Path
RAIZ = Path.cwd().parent if Path.cwd().name == "analysis" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import pandas as pd
from IPython.display import Image, display
from vhp import eda
from vhp.config import ruta

pd.set_option("display.width", 200)
FIG = ruta("figuras")
r = eda.correr()

# %% [markdown]
# ## 1. Series diarias y semanales

# %%
display(Image(FIG / "01_series_diarias.png"))

# %% [markdown]
# ## 2. STL (período 6) y estacionariedad
# Fuerzas de tendencia y estacionalidad según FPP3 (§4.3). ADF: H0 raíz unitaria.

# %%
display(Image(FIG / "02_stl_total.png"))
print({k: round(v, 2) for k, v in r["fuerzas"].items()})
r["estacionariedad"]

# %%
display(Image(FIG / "03_acf_pacf.png"))

# %% [markdown]
# ## 3. Día de la semana y efectos de calendario
# Regresión lineal de log(y) con tendencia, día de la semana, feriados, cierres y verano (enero).

# %%
display(Image(FIG / "04_dia_semana.png"))
r["dia_semana"].round(2)

# %%
r["efectos"].round(3)

# %% [markdown]
# ## 4. Mix de categorías contra temperatura

# %%
display(Image(FIG / "06_mix_temperatura.png"))
r["mix_corr"].round(3)

# %%
r["mix_tercil"].round(1)

# %%
# Control de oferta (solo con datos privados): ¿cambia el menú con la temperatura?
r["oferta"]
