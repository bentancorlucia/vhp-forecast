# %% [markdown]
# # Fase 8 — Gasto en Meta Ads y clientes nuevos de particulares (semanal)
# Lógica en `src/vhp/ads.py`. Semanas lunes a domingo, 05/01/2026–30/08/2026 (34).
# Gasto en índice base 100 y conteos × K: las elasticidades (log-log) no dependen de K.
# Es correlación, no causa. `python main.py ads` regenera todo (segundos).

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
# ## 1. ¿Cuánto varía el gasto?

# %%
pd.read_csv(T / "ads_variacion_gasto.csv").round(3)

# %% [markdown]
# ## 2. Regresión log(clientes nuevos) ~ log(gasto total) + verano
# Gasto total para incluir el escalón enero → febrero; `corr_x_control` muestra que ese
# escalón está casi perfectamente confundido con el verano.

# %%
pd.read_csv(T / "ads_regresion.csv").round(3)

# %% [markdown]
# ## 3. Granger con 1 rezago (fijado antes de mirar el resultado)

# %%
pd.read_csv(T / "ads_granger.csv").round(3)

# %%
display(Image(FIG / "11_meta_ads.png"))
