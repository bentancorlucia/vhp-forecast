# Comparación antes / después: empresas de septiembre a noviembre 2026

Antes = `main` al 18/11/2026 (empresas y Total hasta el 31/08/2026; backtest del Total 08/06–29/08/2026; backtest aparte de particulares 24/08–14/11/2026).
Después = rama `empresas-sep-nov` (los dos segmentos hasta el 14/11/2026; un solo backtest del Total 24/08–14/11/2026).
Fuente: `reports/resultados.md` y `reports/tables/*.csv` regenerados con `python main.py all` el 18/11/2026.
⚠ = se mueve más de 5 % (relativo) o cambia la conclusión.

## Datos

| Número | Antes | Después | |
|---|---|---|---|
| Días hábiles del Total | 407 (06/05/2025–31/08/2026) | 472 (06/05/2025–14/11/2026) | ⚠ +65 días |
| Días hábiles de empresas | 403 hasta 31/08/2026 | 468 hasta 14/11/2026 (sin el cierre del 24/05/2025) | ⚠ |
| Líneas nuevas de empresas (calidad_datos) | — | sep 10.839, oct 10.264, nov 6.092 limpias (4.351 posteriores al 14/11 descartadas); 0 duplicados, 0 domingos | |
| Control vs. Tablero (solo particulares) | sin cambios | 44 semanas (05/01–02/11/2026): pedidos iguales en 33, clientes nuevos iguales en 29 | El Tablero no tiene empresas: no controla los datos nuevos |

## EDA (días hábiles del período de cada columna)

| Número | Antes (hasta 31/08/2026) | Después (hasta 14/11/2026) | |
|---|---|---|---|
| ADF del Total en nivel, p | 0,66 | 0,59 | ⚠ (−11 %), misma conclusión: no estacionaria |
| Perfil semanal empresas: lunes / sábado | 1,079 / 0,250 | 1,072 / 0,252 | |
| Perfil semanal empresas: miércoles / viernes | 1,224 / 1,147 | 1,238 / 1,127 | |
| Perfil semanal particulares (lun / sáb) | 1,604 / 0,870 | 1,604 / 0,870 | igual |
| Feriado laborable, Total | −29,9 % [−37,3; −21,5] (11 días) | −29,1 % [−35,9; −21,6] (13 días) | |
| Feriado laborable, empresas | −45,9 % [−55,0; −35,0] | −45,4 % [−53,4; −36,0] | |
| Verano, Total | −25,2 % [−29,3; −20,9] | −25,0 % [−29,2; −20,6] | |
| Verano, empresas | −24,1 % [−30,0; −17,6] | −24,2 % [−30,2; −17,7] | |
| Tendencia, Total | +1,0 %/semana | +1,0 %/semana | |

## Pronóstico del total

| Modelo (MASE / WAPE / cobertura 80 %) | Antes (08/06–29/08/2026) | Después (24/08–14/11/2026) | |
|---|---|---|---|
| LightGBM directo | 1,116 / 11,5 % / 80 % | 0,846 / 8,9 % / 76 % | ⚠ sigue 1.º; cobertura 76 % |
| Media móvil 4 semanas | 1,150 / 11,8 % / 81 % (2.º) | 0,962 / 10,1 % / 83 % (4.º) | ⚠ baja dos lugares |
| ETS | 1,221 / 12,6 % / 79 % | 0,915 / 9,6 % / 85 % | ⚠ |
| SARIMA | 1,270 / 13,1 % / 80 % | 0,911 / 9,6 % / 82 % (2.º) | ⚠ sube a 2.º |
| MLP | 1,363 / 14,1 % / 76 % | 1,036 / 10,9 % / 77 % | ⚠ |
| Naive estacional | 1,578 / 16,3 % / 76 % | 1,172 / 12,3 % / 80 % | ⚠ |
| Naive | 4,077 / 41,9 % / 83 % | 3,430 / 36,0 % / 85 % | ⚠ |

Los MASE bajan en todos los modelos porque la ventana es otra (septiembre–noviembre, más estable que el invierno con el 17/08), no porque los modelos mejoren.

| Test | Antes | Después | |
|---|---|---|---|
| DM lgbm vs. 2.º | media móvil p = 0,55 | SARIMA p = 0,46 | ⚠ cambia el rival; misma conclusión (no se separan) |
| DM lgbm vs. ETS | p = 0,088 | p = 0,447 | ⚠ más lejos de separarse |
| DM mejores vs. naive estacional | p ≤ 0,007 | p ≤ 0,018 | ⚠ sigue < 0,05 |
| Ljung-Box (ETS y SARIMA, rezagos 6 y 12) | p 0,59–0,87 | p 0,07–0,79 | ⚠ el mínimo baja, sigue > 0,05 |
| SARIMA al último origen | (2,0,2)(1,1,1)[6] | (2,0,2)(1,1,1)[6] | igual |
| Backtest de particulares aparte | ETS 0,888, lgbm 0,922, DM p = 0,54 | se sacó (un solo backtest) | |

**Modelo elegido:** se mantiene LightGBM directo; sigue siendo el de menor MASE.

## Clima → mix (todo el período; backtest de cada columna)

| Número | Antes | Después | |
|---|---|---|---|
| Carne vacuna calor − frío, empresas | −8,3 pp [−9,9; −6,5] | −7,2 pp [−9,0; −5,4] | ⚠ (−13 %), IC sin cero |
| Carne vacuna calor − frío, particulares | −2,7 pp | −2,5 pp | ⚠ (−7 %) |
| Log loss empresas: media_4sem / multinomial + clima | 1,6730 / 1,6746 | 1,6792 / 1,6817 | media_4sem sigue mejor |
| Log loss particulares: media_4sem / multinomial + clima / multinomial | 1,7604 / 1,7617 / 1,7618 | 1,7502 / 1,7485 / 1,7486 | ⚠ el multinomial queda apenas mejor (−0,1 %); con o sin clima da lo mismo: el clima no agrega |
| Categorías MASE: media_4sem / multinomial | 1,019 / 1,056 | 0,901 / 0,907 | ⚠ la diferencia se achica |
| Cobertura 80 % categorías (media_4sem) | 79,9 % | 78,5 % | |

## Plan de compras

| Número | Antes | Después | |
|---|---|---|---|
| Backtest empresas | 08/06–29/08/2026 | 24/08–14/11/2026 | |
| p elegido | 45 | 50 | ⚠ (p = 45 cuesta 15,50 contra 15,41: casi empate) |
| Costo por vianda (p elegido) | 16,5 UYU | 15,4 UYU | ⚠ (−7 %) |
| Con costos fijos | p = 50 | p = 50 | |
| Empresas, p elegido: cobertura / costo | 45,2 % / 19,1 UYU | 38,1 % / 15,9 UYU | ⚠ |
| Particulares, p elegido: cobertura / costo | 40,5 % / 15,0 UYU | 42,9 % / 15,1 UYU | ⚠ cobertura +6 % |
| Sensibilidad faltante $150 / $300 / $600 → p | 45 / 60 / 75 | 50 / 60 / 75 | |
| Proporción XL empresas | 17,1 % | 16,5 % | |
| Plan empresas 16/11–21/11/2026 | [SUPUESTO] último dato del 29/08 | datos hasta el 14/11/2026 | ⚠ ya no es supuesto; pronóstico de carne vacuna 837 → 998 (× K) |

## Recetario (semana 16/11–21/11/2026)

| Número | Antes | Después | |
|---|---|---|---|
| Ingredientes / proveedores | 115 / 21 | 112 / 21 | |
| Platos sin receta (12 semanas) | 26, 9,5 % de las viandas | 26, 13,7 % de las viandas | ⚠ (empresas ahora usa sus semanas recientes, con más platos sin receta) |
| % sin receta del pronóstico de la semana | 11,9 % | 12,4 % | |
| kg plan / kg pronóstico | p45 ×0,991, p80 ×1,110, p90 ×1,202, p95 ×1,271 | p50 ×1,029, p80 ×1,135, p90 ×1,203, p95 ×1,277 | cambia porque p pasó de 45 a 50 |

## Lo que no cambia

- Eventos y Meta Ads son de particulares: `eventos_efectos.csv`, `eventos_placebo.csv`, `ads_regresion.csv`, `ads_granger.csv` y `ads_variacion_gasto.csv` son idénticos byte a byte.
- Plan de particulares: mismo pronóstico; la compra cambia solo por p (45 → 50).

## Otros cambios
- Plato nuevo de empresas: `Hamburguesa al pan` → carne vacuna [SUPUESTO] y SIN_RECETA.
- El lunes 17/08/2026 (export incompleto) queda fuera de las semanas pronosticadas; sigue en el entrenamiento.
