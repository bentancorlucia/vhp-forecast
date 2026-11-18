# Comparación antes / después de simplificar

- **Antes**: commit `aec7c8a` (main, "Estado antes de simplificar"): `reports/tables/` y `reports/resultados.md` de ese commit.
- **Después**: rama `simplificar`, `reports/tables/` y `reports/resultados.md` actuales.
- ⚠ = cambio relativo > 5 % respecto del valor de antes. Para p-valores e IC, el % es sobre el número mostrado.
- Períodos: backtest walk-forward 08/06/2026–29/08/2026 (12 orígenes); datos 06/05/2025–31/08/2026; Meta semanal 05/01/2026–30/08/2026.

## 1. Pronóstico del total (backtest 08/06–29/08/2026, n = 70 días)

| Modelo (antes → después) | MASE antes → después | WAPE antes → después | Cobertura 80 % antes → después | ¿Cambia la conclusión? |
|---|---|---|---|---|
| LightGBM directo | 1,106 → 1,116 (+0,9 %) | 11,4 → 11,5 % (+0,9 %) | 72,9 → 80,0 % ⚠ (+9,8 %) | No: sigue primero. La cobertura ahora es la nominal (intervalo por cocientes empíricos, igual para todos los modelos). |
| Media móvil 4 semanas | 1,150 → 1,150 (0 %) | 11,8 → 11,8 % (0 %) | 87,1 → 81,4 % ⚠ (−6,6 %) | No |
| ETS (AutoETS ↔ ETS) | 1,177 → 1,221 (+3,7 %) | 12,2 → 12,6 % (+3,6 %) | 95,7 → 78,6 % ⚠ (−17,9 %) | No (sigue tercero); antes sobrecubría |
| SARIMA (AutoARIMA ↔ SARIMA) | 1,279 → 1,270 (−0,7 %) | 13,2 → 13,1 % (−0,6 %) | 85,7 → 80,0 % ⚠ (−6,7 %) | No |
| LSTM → MLP | 1,282 → 1,363 ⚠ (+6,3 %) | 13,2 → 14,1 % ⚠ (+6,4 %) | 74,3 → 75,7 % (+1,9 %) | No: la red sigue sin ganarle a LightGBM (ahora con más margen) |
| Naive estacional | 1,578 → 1,578 (0 %) | 16,3 → 16,3 % (0 %) | 81,4 → 75,7 % ⚠ (−7,0 %) | No |
| Naive | 3,976 → 4,077 (+2,6 %) | 40,9 → 41,9 % (+2,5 %) | 82,9 → 82,9 % (0 %) | No |
| LightGBM directo + clima | 1,203 → salió | 12,4 % → salió | 67,1 % → salió | No: la conclusión "el clima no mejora el total" queda en decisiones, sin tabla |
| LightGBM recursivo | 1,258 → salió | 12,9 % → salió | 62,9 % → salió | No |
| SARIMAX | 1,381 → salió | 14,2 % → salió | 77,1 % → salió | No |
| SARIMAX + clima | 1,379 → salió | 14,2 % → salió | 77,1 % → salió | No |
| Pinball / pinball rel. (todas) | columna presente → salió | | | No (ya no se reporta) |

| Número clave | Antes | Después | Cambio | ¿Cambia la conclusión? |
|---|---|---|---|---|
| Modelo ganador (menor MASE) | LightGBM directo | LightGBM directo | = | No |
| DM LightGBM vs media móvil 4 sem (p) | 0,488 | 0,554 ⚠ | +13,6 % | No: no se separan |
| DM LightGBM vs ETS (p) | 0,437 | 0,088 ⚠ | −79,9 % | Matiz: sigue no significativo al 5 %, pero ahora lo es al 10 % |
| DM LightGBM vs SARIMA (p) | no se calculaba | 0,041 | nuevo | Nuevo: LightGBM le gana a SARIMA al 5 % |
| DM mejores vs naive estacional (p) | ≤ 0,002 | ≤ 0,007 | | No: todos le ganan |
| Feriado laborable, total (EDA) | −27 % [−32; −20] | −30 % [−37; −22] ⚠ | +11 % | No (más negativo; ahora regresión con más controles) |

## 2. Efecto de eventos (contrafactual SARIMA + placebos, IC 95 %)

| Evento (período) | Antes | Después | Cambio punto | ¿Cambia la conclusión? |
|---|---|---|---|---|
| Agencia Meta, viandas particulares (02/02–28/03/2026) | +78,5 % [+18,1; +156,6], placebos 0/3 | +79,8 % [+17,8; +170,6] ⚠ (techo IC +9 %), 0/3 | +1,6 % | No: positivo, cota superior (confundido con verano) |
| Influencer, viandas particulares (15/04–28/04/2026) | +5,2 % [−19,7; +39,3], 2/8 | +4,6 % [−20,4; +36,6], 2/8 | −11,6 % ⚠ | No: sin efecto |
| Postres web, tasa postre (15/04–12/05/2026) | +0,127 [+0,117; +0,136], 0/7 | +0,126 [+0,117; +0,135], 0/7 | −0,1 % | No |
| Panes web, tasa pan (02/06–29/06/2026) | +0,014 [+0,011; +0,016], 1/8 | +0,015 [+0,013; +0,017], 2/8 | +6,5 % ⚠ | No: positivo y claro (p placebo 0,11 igual) |
| Suba de precio, viandas particulares (01/08–31/08/2026) | +9,0 % [−19,4; +45,3], 0/8 | +8,9 % [−19,3; +43,5], 0/8 | −0,5 % | No: sin efecto |
| Suba de precio sin 17/08 | +15,9 % [−14,3; +53,6] | salió | | No |
| Suba de precio, tasa extras (01/08–31/08/2026) | −0,020 [−0,063; +0,021], 1/8 | −0,024 [−0,068; +0,018], 1/8 | −20,7 % ⚠ (más negativo) | No: IC incluye 0 |

Los órdenes SARIMA cambiaron (antes AIC sobre otra grilla; ahora grilla chica sin constante), p. ej. agencia (2,0,2)(0,1,2)[6] → (1,0,1)(1,1,1)[6].

## 3. Gasto en Meta Ads (semanal, 05/01–30/08/2026)

| Número clave | Antes | Después | ¿Cambia la conclusión? |
|---|---|---|---|
| Efecto del gasto en clientes nuevos | Elasticidad ARIMAX (suma rezagos 0–1, gasto total) 0,21 [−0,01; +0,44], 33 sem. | Regresión log(clientes nuevos) ~ log(gasto total) + verano: −1,11 [−3,31; +1,08], p = 0,32, 34 sem.; corr(gasto, verano) = −0,999 ⚠ (cambia el signo) | No: en los dos casos el IC incluye 0 y el efecto no está identificado |
| Granger gasto campaña → clientes nuevos | 16 tests; 2 rezagos p = 0,002, 1 rezago p = 0,576 | Solo 1 rezago, fijado de antemano: F = 0,32, p = 0,576 (30 sem., 02/02–30/08) | No: sin causalidad; desaparece el p = 0,002 que había que explicar |
| CV del gasto de la campaña desde febrero | 2,2 % | 2,2 % | No |
| Conclusión | Efecto no identificado; variar el gasto a propósito | Igual | No |

## 4. Clima → mix de categorías (backtest 08/06–29/08/2026)

| Número clave | Antes | Después | Cambio | ¿Cambia la conclusión? |
|---|---|---|---|---|
| MASE categorías, método elegido (LightGBM × media 4 sem) | 1,018 (`mix_media_4sem_lgbm`) | 1,019 (`media_4sem`) | +0,03 % | No |
| WAPE categorías, método elegido | 20,3 % | 20,3 % | +0,1 % | No |
| Cobertura 80 % categorías, método elegido | 51,8 % | 79,9 % ⚠ | +54 % | Sí, mejora: antes el intervalo subcubría mucho; ahora calibrado con cocientes empíricos |
| MASE categorías multinomial / multinomial + clima | 1,056 / 1,057 | 1,056 / 1,057 | 0 % | No |
| MASE segmento (LightGBM) | 1,042 | 1,044 | +0,2 % | No |
| Cobertura 80 % segmento | 70,0 % | 82,1 % ⚠ | +17 % | Mejora (ahora cerca del nominal) |
| Bottom-up / MinT / top-down / lgbm_clima | 1,018 / 1,019 / 1,031 / 1,082 | salieron | | No: se decía "empata con BU y MinT" |
| Log loss media_4sem (empresas / particulares) | 1,6730 / 1,7604 | 1,6730 / 1,7604 | 0 % | No: el clima no mejora la participación |
| Carne vacuna calor − frío, empresas | −8,3 pp [−9,9; −6,5] | −8,3 pp [−9,9; −6,5] | 0 % | No |
| Carne vacuna calor − frío, particulares | −2,5 pp [−3,4; −1,6] | −2,5 pp [−3,4; −1,6] | 0 % | No |

## 5. Plan de compras (backtest 08/06–29/08/2026; sobrante $200, faltante $150)

| Número clave | Antes | Después | Cambio | ¿Cambia la conclusión? |
|---|---|---|---|---|
| Regla del cuantil | τ* = 150/350 = 0,429 teórico, con cuantiles LightGBM recalibrados por conformal (12 sem.) | p de menor costo simulado sobre cocientes real/pronóstico (12 sem.) | método distinto | No: los dos compran un poco menos que la mediana |
| Cuantil / percentil elegido | 0,429 | 0,45 | +5,0 % (justo en el umbral) | No |
| Costo semanal en el elegido (UYU por vianda demandada) | 20,33 | 20,29 | −0,2 % | No |
| Cobertura / sobrante / faltante semanal en el elegido | 47,6 % / 5,2 % / 6,7 % | 46,4 % / 5,4 % / 6,4 % | −2,5 % / +3,9 % / −4,4 % | No |
| Costo diario en τ* | 35,36 | salió (solo compra semanal) | | Se pierde la cota diaria |
| Semanal servicio 80 %: costo (cobertura) | 30,93 (80,4 %) | 30,11 (79,2 %) | −2,7 % | No |
| Semanal servicio 90 %: costo (cobertura) | 50,11 (88,1 %) | 46,08 (85,1 %) | −8,0 % ⚠ | No |
| Semanal servicio 95 %: costo (cobertura) | 69,84 (94,6 %) | 62,69 (92,3 %) | −10,2 % ⚠ | No (cubre un poco menos de lo nominal) |
| Naive estacional semanal en el elegido | 23,98 | 24,21 | +1,0 % | No: LightGBM sigue siendo más barato |
| Plan semana 31/08–05/09/2026, suma de porciones × K (elegido / p80 / p90 / p95) | 5895 / 6815 / 7512 / 7923 | 5959 / 6830 / 7452 / 7772 | +1,1 % / +0,2 % / −0,8 % / −1,9 % | No |
| Diagnóstico de cuantiles crudos, ventana conformal, plan por segmento diario | tablas presentes | salieron | | No |

Sensibilidad al costo de faltante (compra semanal, LightGBM):

| Costo faltante | Antes: τ, costo (cobertura) | Después: p, costo (cobertura) | Cambio costo | ¿Cambia la conclusión? |
|---|---|---|---|---|
| $150 | 0,429, 20,33 (47,6 %) | 45, 20,29 (46,4 %) | −0,2 % | No |
| $300 | 0,60, 28,41 (62,5 %) | 55 ⚠ (−8 %), 27,96 (58,9 % ⚠, −5,7 %) | −1,6 % | No: el p sube con el costo de faltante |
| $600 | 0,75, 37,61 (77,4 %) | 75, 37,46 (75,6 %) | −0,4 % | No |

## 6. Líneas de código (`.py`, `wc -l`)

| Carpeta | Antes (`aec7c8a`) | Después (`simplificar`) | Cambio |
|---|---|---|---|
| src | 3954 | 2957 | −997 (−25 %) |
| analysis | 438 | 433 | −5 (−1 %) |
| tests | 638 | 624 | −14 (−2 %) |
| main.py | 37 | 37 | 0 |
| **Total** | **5067** | **4051** | **−1016 (−20 %)** |

## Resumen

Ninguna conclusión de negocio cambia: LightGBM directo sigue ganando sin separarse de la media móvil; la red (LSTM → MLP) sigue sin ganarle; el clima mueve el mix pero no mejora el pronóstico; el efecto de la agencia sigue siendo una cota superior; el efecto de Meta sigue sin estar identificado; el plan sigue comprando apenas por debajo de la mediana, a ≈ 20,3 UYU por vianda en compra semanal. Lo que más se movió son las coberturas del 80 %: ahora todas están cerca del nominal porque el intervalo es el mismo método para todos. También cambian el p de DM LightGBM vs ETS (0,44 → 0,09) y el signo de la elasticidad de Meta (con IC que incluye 0 en los dos casos).
