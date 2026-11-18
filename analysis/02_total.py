# %% [markdown]
# # Fase 5 — Modelos del total y backtesting walk-forward
# Lógica en `src/vhp/pronostico.py`, `src/vhp/evaluate.py` y `src/vhp/models/`.
# Modelos: naive, naive estacional, media móvil 4 semanas, ETS, SARIMA, LightGBM directo y MLP.
# Backtest: 12 orígenes (sábados 06/06–22/08/2026), se pronostican los días hábiles
# de la semana siguiente; semanas pronosticadas 08/06–29/08/2026. Ventana expansiva.
# Intervalo 80 %: percentiles 10 y 90 de y/ŷ del propio modelo en los 12 orígenes previos
# (por eso el backtest corre también los sábados 14/03–30/05/2026, que no entran en las métricas).
# Datos públicos (unidades × K): comparar con MASE, WAPE y cobertura.
#
# `python main.py backtest` regenera todo (unos 3 minutos). Esta celda lee las tablas guardadas.

# %%
import sys
from pathlib import Path
RAIZ = Path.cwd().parent if Path.cwd().name == "analysis" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import pandas as pd
from IPython.display import Image, display
from vhp import evaluate as ev
from vhp.config import ruta

pd.set_option("display.width", 200)
T, FIG = ruta("tablas"), ruta("figuras")
res = pd.read_csv(T / "backtest_total_predicciones.csv", parse_dates=["origen", "fecha"])

# %% [markdown]
# ## 1. Métricas (backtest 08/06/2026–29/08/2026)

# %%
pd.read_csv(T / "backtest_total_metricas.csv").round(3)

# %% [markdown]
# ## 2. MASE por horizonte (1 = lunes … 6 = sábado)

# %%
pd.read_csv(T / "backtest_total_mase_por_h.csv", index_col=0).round(2)

# %% [markdown]
# ## 3. Diebold-Mariano y Ljung-Box

# %%
pd.read_csv(T / "backtest_total_dm.csv").round(3)

# %%
pd.read_csv(T / "backtest_total_ljung_box.csv").round(4)

# %% [markdown]
# ## 4. Pronóstico vs. real

# %%
display(Image(FIG / "07_backtest_total.png"))

# %% [markdown]
# ## 5. Sensibilidad: sin el lunes 17/08/2026 (anomalía de datos en particulares)

# %%
ev.metricas(res[res["fecha"] != "2026-08-17"]).round(3)
