# %% [markdown]
# # Fase 1 — Calidad de los datos de pedidos
# Resultados de `src/vhp/load.py`. Período: entregas de mayo 2025 a agosto 2026.
# 
# Antes de correr: `python main.py prepare` (genera `data/interim/lineas.parquet`).

# %%
import sys
from pathlib import Path
RAIZ = Path.cwd().parent if Path.cwd().name == "analysis" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import pandas as pd
import matplotlib.pyplot as plt
from vhp import load
from vhp.config import ruta

pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 200)

lineas = pd.read_parquet(ruta("interim") / "lineas.parquet")
calidad = pd.read_csv(ruta("tablas") / "calidad_datos.csv")
control = pd.read_csv(ruta("control") / "control_vs_tablero.csv", parse_dates=["semana_ini"])
print(f"Líneas limpias: {len(lineas):,} | archivos: {len(calidad)}")

# %% [markdown]
# ## 1. Tabla de calidad por archivo

# %%
calidad

# %% [markdown]
# ## 2. Duplicados exactos eliminados
# Se comparan las 23 columnas originales, antes de descartar las personales.

# %%
print("Filas crudas:", calidad.filas_crudas.sum(), "| duplicados:", calidad.duplicados_exactos.sum(), "| limpias:", calidad.filas_limpias.sum())
calidad.loc[calidad.duplicados_exactos > 0, ["archivo", "filas_crudas", "duplicados_exactos", "filas_limpias"]]

# %% [markdown]
# ## 3. Validaciones
# Meses completos, entregas dentro del mes del archivo, fechas válidas y cantidades > 0.

# %%
problemas = load.validar(lineas, calidad)
print("Meses:", calidad.mes.min(), "a", calidad.mes.max(), "|", calidad.mes.nunique(), "meses ×", calidad.segmento.nunique(), "segmentos")
print("Problemas:", problemas or "ninguno")
calidad[["archivo", "fecha_min", "fecha_max", "fechas_invalidas", "entregas_fuera_de_mes", "cantidad_no_positiva"]]

# %% [markdown]
# ## 4. Entregas en domingo (el negocio cierra): se descartan

# %%
print("Líneas en domingo descartadas:", calidad.domingos_descartados.sum())
calidad.loc[calidad.domingos_descartados > 0, ["archivo", "domingos_descartados"]]

# %% [markdown]
# ## 5. Precios en empresas
# El CLAUDE.md suponía precios en 0: no es así.

# %%
lineas.groupby("segmento").agg(
    lineas=("precio_unitario", "size"),
    con_precio=("precio_unitario", lambda s: (s > 0).sum()),
    pct_precio_cero=("precio_unitario", lambda s: round(100 * (s == 0).mean(), 2)),
)

# %%
# % de líneas con precio 0 en empresas, por mes
calidad[calidad.segmento == "empresas"].plot(x="mes", y="pct_precio_cero", kind="bar", legend=False, figsize=(10, 3), title="Empresas: % de líneas con precio 0")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 6. Teléfonos vacíos

# %%
calidad.pivot(index="mes", columns="segmento", values="telefono_vacio")

# %% [markdown]
# ## 7. Control contra el Tablero (particulares, semanas lunes–domingo, 05/01–24/08/2026)
# Diferencia = pipeline − Tablero. Se reporta, no se fuerza.

# %%
cols = ["semana_ini", "pedidos_particulares_tablero", "pedidos_particulares_pipeline", "dif_pedidos_particulares",
        "clientes_nuevos_particulares_tablero", "clientes_nuevos_particulares_pipeline", "dif_clientes_nuevos_particulares"]
for k in ["pedidos_particulares", "clientes_nuevos_particulares"]:
    d = control[f"dif_{k}"]
    print(f"{k}: semanas iguales {(d == 0).sum()}/{len(d)} | diferencia total {d.sum()} | rango {d.min()} a {d.max()}")
control[cols]

# %%
fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
for a, k in zip(ax, ["pedidos_particulares", "clientes_nuevos_particulares"]):
    a.plot(control.semana_ini, control[f"{k}_tablero"], label="Tablero", lw=2)
    a.plot(control.semana_ini, control[f"{k}_pipeline"], label="Pipeline", ls="--")
    a.set_title(k.replace("_", " ")); a.legend()
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 8. Fase 2 — Datos públicos anonimizados (`data/processed/`)
# Cantidades × K (secreto), importes y gasto de Meta en índice base 100. Requiere `python main.py anonymize`.

# %%
diarias = pd.read_csv(ruta("processed") / "ventas_diarias.csv", parse_dates=["fecha"])
semanal = pd.read_csv(ruta("processed") / "particulares_semanal.csv", parse_dates=["semana_ini"])
meta = pd.read_csv(ruta("processed") / "meta_ads_semanal_indice.csv", parse_dates=["semana_ini"])
print(f"ventas_diarias: {len(diarias):,} filas | {diarias.fecha.min().date()} a {diarias.fecha.max().date()}")
diarias.head()

# %%
# Chequeo de privacidad: ninguna columna personal y ningún número largo
from vhp.anonymize import COLUMNAS_PROHIBIDAS
for nombre, df in [("ventas_diarias", diarias), ("particulares_semanal", semanal), ("meta_ads_semanal_indice", meta)]:
    print(nombre, "| columnas prohibidas:", set(df.columns) & COLUMNAS_PROHIBIDAS or "ninguna")

# %%
# Viandas por semana y segmento (unidades escaladas)
v = diarias[diarias.tipo_producto == "Vianda"]
sem = v.groupby([pd.Grouper(key="fecha", freq="W-SUN"), "segmento"]).unidades.sum().unstack()
sem.plot(figsize=(11, 4), title="Viandas por semana (unidades × K)")
plt.tight_layout(); plt.show()

# %%
# Meta Ads en índice (base 100 = gasto total medio semanal)
meta.plot(x="semana_ini", y=["gasto_meta_total", "gasto_campania_viandas"], figsize=(11, 3), title="Gasto en Meta (índice)")
plt.tight_layout(); plt.show()
meta
