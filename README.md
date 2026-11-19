# Del pedido al plato

Pronóstico de la demanda de Viandas Hotel del Prado, efecto de eventos y de la pauta en Meta, y plan de compras.
Trabajo final de Series Temporales (UCU, 2026).

## Cómo correr

```bash
brew install libomp                     # macOS: lo necesita LightGBM
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py all            # todo, en orden (requiere los datos privados y .env)
.venv/bin/python -m pytest
```

Pasos sueltos: `python main.py <paso>`.

| Paso | Qué hace | Salida |
|---|---|---|
| `prepare` | Carga, limpieza, duplicados y validaciones (datos privados) | `data/interim/` |
| `anonymize` | Hash de teléfonos y empresas, escalado por K, índices | `data/processed/` |
| `calendar` | Feriados de Uruguay, días hábiles, variables de calendario | `data/processed/calendario.csv` |
| `clima` | Clima diario de Montevideo (Open-Meteo) | `data/external/` |
| `eda` | STL, ACF/PACF, ADF, perfiles, efectos de calendario, mix vs. temperatura | figuras 01–04 y 06 |
| `backtest` | 7 modelos (naive, naive estacional, media móvil, ETS, SARIMA, LightGBM directo, MLP), walk-forward de 12 semanas, sobre el Total y cada segmento (semanas 24/08–14/11/2026), más el control SARIMA con calendario (solo Total) | `backtest_total_*`, `backtest_particulares_*`, `backtest_empresas_*`, `backtest_total_sarima_cal.csv`, figura 07 |
| `mix` | Clima → mix de categorías: efecto de la temperatura, participación media de 4 semanas vs. multinomial | `mix_*`, figuras 08–09 |
| `eventos` | Contrafactuales SARIMA, placebos y efecto mínimo detectable (incluye el cambio de reparto de Meta del 05/09 y la baja de pauta de noviembre 2026) | `eventos_*`, figura 10 |
| `ads` | Meta Ads: variación del gasto y de los clics, regresiones log-log (gasto total, gasto de campaña, clics) y Granger con 1 rezago | `ads_*`, figura 11 |
| `plan` | Plan de compras: pronóstico + colchón (percentil de errores), costo simulado ponderado por la proporción de XL | `plan_*`, figura 12 |
| `compras` | Del plan a los ingredientes con el recetario (privado): kg por ingrediente y por proveedor | `reports_private/` (no se sube), `compras_*` (índice por familia) |
| `report` | Tablas clave con su período | `reports/resultados.md` |

Sin los datos privados, los pasos desde `eda` corren sobre `data/processed/`, y los tests que necesitan datos privados se saltean.

- **Resultados:** [`reports/resultados.md`](reports/resultados.md). Cada tabla dice de qué período es.
- **Decisiones y su porqué:** [`reports/decisiones.yaml`](reports/decisiones.yaml). Es la fuente única que usan el informe y resultados.md.
- **Análisis paso a paso:** `analysis/*.py`, con celdas `# %%` (se corren como notebook en VS Code).

## Resultados principales

Detalle y tablas en `reports/resultados.md`; el porqué de cada decisión en `reports/decisiones.yaml`.

- **Por qué LightGBM.** Menor error en el Total en dos ventanas (MASE 0,846, WAPE 8,9 %, 24/08–14/11/2026; también en 08/06–29/08/2026) y en empresas; en particulares ETS queda apenas primero (0,888 contra 0,922), sin diferencia significativa. Ni Diebold-Mariano ni el SARIMA con calendario lo superan, pero tampoco se separan de él (SARIMA con calendario: MASE 0,842, p = 0,95). En Diebold-Mariano la media móvil gana más días (37) que LightGBM (34), pero tiene más error total.
- **Segmentos.** Cada segmento se pronostica por separado y el plan de compras usa los segmentos. El Total se pronostica directo.
- **Intervalo 80 %.** Cubrió el 76 % (54 de 71 días; IC 95 % de Wilson 65–84 %, Total, 24/08–14/11/2026), algo por debajo del 80 %. Con 71 días esa diferencia es compatible con el azar.
- **MASE entre niveles.** El MASE de cada serie se escala con su propio naive estacional, así que no se compara entre niveles (categorías 0,901 contra segmento 0,989). El WAPE sí: 17,9 % contra 12,3 %.
- **Eventos.** Postres en la web: +0,126 postres por vianda, efecto claro (0 de 7 placebos). Panes en la web: efecto chico, a confirmar: 2 de 8 placebos también dieron significativos. La agencia de Meta (+80 %) es una cota superior: coincide con la vuelta del verano.
- **Compra.** Conviene comprar cerca de lo esperado. El factor de p = 50 (×1,06 en empresas y ×1,01 en particulares, semana 16–21/11/2026) solo corrige que el modelo se quedó corto más veces de las que se pasó; no es un margen de seguridad. Asegurarse el 90 % cuesta 38,9 contra 15,4 UYU por vianda (backtest 24/08–14/11/2026).

## Presentación (`presentacion/`)

Presentación web tipo diapositivas para la defensa (Vite + React + TypeScript). Todos los números salen de `presentacion/public/data/presentacion.json`, que se genera desde los archivos públicos del repo y se contrasta con `reports/resultados.md`.

```bash
cd presentacion
npm install
npm run datos     # regenera el JSON con el .venv del repo (no lee datos privados)
npm run dev       # para presentar
npm run build     # sitio estático en dist/
```

Teclas: → / espacio para avanzar, ← para volver, F pantalla completa, O índice, N notas. `?notas` abre la vista del orador y `?imprimir` todas las diapositivas para PDF. Más detalle en [`presentacion/README.md`](presentacion/README.md).

## Datos públicos (`data/processed/`)

| Archivo | Contenido |
|---|---|
| `ventas_diarias.csv` | Unidades por fecha de entrega × segmento × tipo de producto × categoría de plato, e índice de importe |
| `calendario.csv` | Días hábiles (lunes a sábado sin feriados no laborables) y variables de calendario |
| `particulares_semanal.csv` | Pedidos y clientes nuevos de particulares por semana (lunes a domingo) |
| `meta_ads_semanal_indice.csv` | Gasto, impresiones, clics y alcance de Meta por semana, en índice |
| `particulares_diario.csv` | Clientes nuevos y pedidos de clientes que ya compraron, particulares, por día |
| `xl_semanal.csv` | Proporción de viandas XL por segmento y semana (cociente: no depende de K) |

### Anonimización

- No se publica ningún dato personal: ni nombres, teléfonos, direcciones, empresas o notas, ni sus hashes. Solo agregados.
- No se publica el detalle por plato, solo por categoría: con celdas muy chicas se podría estimar la constante de escalado.
- **Cantidades** multiplicadas por una constante secreta `K` y redondeadas.
- **Importes y gasto de Meta** como índice base 100. Las columnas de gasto comparten la base, así que se pueden comparar entre sí.

### Por qué el escalado no cambia los resultados

Si la serie real es `y` y la publicada es `K·y`, el pronóstico de cualquier modelo lineal en el nivel también queda multiplicado por `K`. Entonces:

- **MASE** = MAE del modelo / MAE del naive estacional: `K` aparece arriba y abajo y se cancela.
- **WAPE** = Σ|y − ŷ| / Σ|y|: también se cancela.
- **Cobertura del intervalo 80 %** y participaciones: son proporciones, no dependen de `K`.

Las métricas absolutas (MAE) quedan multiplicadas por `K`. Por eso en el informe se comparan modelos con métricas relativas.

**Redondeo:** se usa el método del mayor resto dentro de cada fecha × segmento × tipo de producto. El total diario de cada segmento y tipo queda en `round(K × real)`, con un error de ±0,5. Cada categoría difiere de `K × real` en menos de 1 unidad, y por eso puede haber filas con 0 unidades.

## Limitaciones de los datos

- **Noviembre cortado en la última semana completa (14/11/2026).** Empresas de septiembre a noviembre sale del export de Excel: la pantalla de Resumen comercial las muestra en 0.
- **Recetario:** 26 platos vendidos (13,7 % de las viandas de las últimas 12 semanas, 22/08–14/11/2026, los dos segmentos) no tienen receta en el Costo del recetario y quedan fuera de la lista de compras. Las XL sin receta propia se estiman como la normal × 1,30.

- Faltan los pedidos por WhatsApp, teléfono o carga manual.
- **Lunes 17/08/2026, particulares:** la cantidad de pedidos coincide con el Tablero del negocio, pero casi no tienen líneas de producto (mediana de 1 vianda por pedido, contra ~7 un lunes normal). Parece un export incompleto. Se dejó como está. Desde que empresas llega a noviembre queda fuera de las semanas pronosticadas (24/08–14/11/2026), pero sigue en el entrenamiento.
- **Serie corta:** hay un solo enero, así que el verano y la entrada de la agencia de Meta (02/02/2026) se confunden.
- **Clima observado:** en el backtest se usa el clima observado; en producción habría que usar el pronóstico del tiempo.
- **Meta Ads:** desde febrero el gasto casi no varía, así que su efecto no está identificado. Los clics sí varían, pero dependen de qué anuncios elige la agencia (correlación, no causa). La baja de pauta de noviembre 2026 tiene solo 2 semanas posteriores. No hay origen del pedido (UTM): la atribución por anuncio queda fuera.
- **Costos estimados:** los costos de sobrante ($200 normal, $260 XL) y faltante ($150 / $155) son estimaciones. El plan muestra la sensibilidad a otros valores.
