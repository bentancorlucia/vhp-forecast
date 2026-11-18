# Datos nuevos (18/11/2026): antes y después

Rama `datos-nuevos` (desde `simplificar`). Plan en `../prompt-datos-nuevos.md`. "Antes" = tablas de `reports/tables/` al empezar (datos hasta el 31/08/2026); "después" = `python main.py all` con particulares hasta el 14/11/2026, Meta y control hasta el 08/11/2026 y el recetario. ⚠ = se movió más de 5 % o cambió la conclusión.

**Sin cambios (26 números):** todo lo que solo usa datos hasta agosto: MASE, Diebold-Mariano y Ljung-Box del Total (backtest 08/06–29/08/2026), efectos de calendario del Total y de empresas, mix de categorías (backtest 08/06–29/08/2026), efecto del clima en empresas y los eventos agencia, influencer, postres y panes.

| Número | Antes | Después | Cambio | | Período antes | Período después |
|---|---|---|---|---|---|---|
| MASE particulares ets (nuevo) | — | 0,888 | nuevo |  | — | 24/08–14/11/2026 |
| MASE particulares lgbm_directo (nuevo) | — | 0,922 | nuevo |  | — | 24/08–14/11/2026 |
| MASE particulares sarima (nuevo) | — | 0,972 | nuevo |  | — | 24/08–14/11/2026 |
| MASE particulares mlp (nuevo) | — | 0,987 | nuevo |  | — | 24/08–14/11/2026 |
| MASE particulares media_movil_4sem (nuevo) | — | 1,030 | nuevo |  | — | 24/08–14/11/2026 |
| MASE particulares naive_estacional (nuevo) | — | 1,246 | nuevo |  | — | 24/08–14/11/2026 |
| MASE particulares naive (nuevo) | — | 2,185 | nuevo |  | — | 24/08–14/11/2026 |
| EDA Particulares tendencia (por semana) (%) | 0,930 | 0,919 | −1,2 % |  | 06/05/2025–31/08/2026 | Particulares hasta 14/11/2026; Total/Empresas igual |
| EDA Particulares feriado_laborable (%) | −18,861 | −18,462 | +2,1 % |  | 06/05/2025–31/08/2026 | Particulares hasta 14/11/2026; Total/Empresas igual |
| EDA Particulares vispera_cierre (%) | −26,027 | −25,678 | +1,3 % |  | 06/05/2025–31/08/2026 | Particulares hasta 14/11/2026; Total/Empresas igual |
| EDA Particulares post_cierre (%) | −18,322 | −18,472 | −0,8 % |  | 06/05/2025–31/08/2026 | Particulares hasta 14/11/2026; Total/Empresas igual |
| EDA Particulares verano (%) | −25,215 | −25,145 | +0,3 % |  | 06/05/2025–31/08/2026 | Particulares hasta 14/11/2026; Total/Empresas igual |
| Mix calor−frío carne vacuna particulares (pp) | −2,472 | −2,711 | −9,7 % | ⚠ | 06/05/2025–31/08/2026 | particulares hasta 14/11/2026 |
| Evento suba_precio / viandas_particulares (%) | 8,941 | 11,800 | +32,0 % | ⚠ | 01/08–31/08/2026 | 01/08–25/09/2026 |
| Evento suba_precio / tasa_extras_particulares (por vianda) | −0,024 | −0,023 | +3,3 % |  | 01/08–31/08/2026 | 01/08–25/09/2026 |
| Evento suba_precio_13sem / viandas_particulares (%) | — | 11,375 | nuevo |  | — | 01/08–30/10/2026 |
| Evento meta_reparto / clientes_nuevos_particulares (%) | — | −7,148 | nuevo |  | — | 05/09–30/10/2026 |
| Evento baja_pauta / clientes_nuevos_particulares (%) | — | −8,151 | nuevo |  | — | 02/11–14/11/2026 |
| Evento baja_pauta / pedidos_recurrentes_particulares (%) | — | −2,135 | nuevo |  | — | 02/11–14/11/2026 |
| CV gasto campaña (%) | 2,160 | 2,835 | +31,2 % | ⚠ | 02/02–30/08/2026 | 02/02–08/11/2026 |
| Elasticidad gasto total | −1,113 | 0,043 | +103,8 % | ⚠ | 05/01–30/08/2026 (34 sem) | 05/01–08/11/2026 (44 sem) |
| p elasticidad gasto total | 0,321 | 0,940 | +193,2 % | ⚠ | 34 sem | 44 sem |
| Elasticidad clics (nuevo) | — | 0,267 | nuevo |  | — | 02/02–08/11/2026 |
| Granger gasto campaña p | 0,576 | 0,303 | −47,4 % | ⚠ | 30 sem | 40 sem |
| Granger clics p (nuevo) | — | 0,034 | nuevo |  | — | 40 sem |
| Plan UYU por vianda (p elegido) | 20,287 | 16,512 | −18,6 % | ⚠ | costos fijos | ponderado por XL |
| Plan cobertura p elegido | 0,464 | 0,429 | −7,7 % | ⚠ |  |  |
| Sensibilidad faltante $300: p | 55,000 | 60,000 | +9,1 % | ⚠ |  |  |

## Qué cambia de conclusión

- **Meta, gasto:** la elasticidad del gasto total pasa de −1,11 (p = 0,32) a +0,04 (p = 0,94): cambió el signo, pero en los dos casos no es significativa → la conclusión ("no identificado") se mantiene. El CV del gasto de la campaña sube de 2,2 % a 2,8 % por la baja de noviembre, que todavía es chica (−8 % en la semana del 02/11).
- **Meta, clics (nuevo):** elasticidad +0,27 [+0,04; +0,49], p = 0,02, y Granger clics → clientes nuevos p = 0,034. Es la primera señal de Meta, pero es correlación (los clics dependen de qué anuncios elige la agencia).
- **Suba de precio:** con 8 semanas el efecto pasa de +9 % a +12 % (IC con cero, 0 de 4 placebos). Sigue preliminar: con ventanas de 8 semanas o más entran como mucho 4 placebos.
- **Plan:** p = 45 igual. El costo por vianda baja de 20,3 a 16,5 UYU, pero es otra ventana (particulares 24/08–14/11) y otros costos (ponderados por XL): no es una mejora del método. La sensibilidad con faltante $300 pasa de p 55 a 60.
- **Particulares (nuevo):** ETS queda primero (0,888) y LightGBM segundo (0,922), sin diferencia significativa (DM p = 0,54).

## Diapositivas de `../prompt-web-presentacion.md` que cambian

| # | Diapositiva | Qué cambia |
|---|---|---|
| 3 | Los datos | Período: particulares hasta el 14/11/2026; empresas y Total hasta el 31/08/2026 (no hay exports de empresas sep–nov). |
| 19 | Patrones | Efectos de calendario de particulares con datos hasta noviembre (cambios < 3 %). |
| 20–22 | Ranking, Diebold-Mariano, backtest en el tiempo | Agregar el backtest de particulares 24/08–14/11/2026 (ETS ≈ LightGBM) o una nota; el del Total no cambia. |
| 23 | Clima → mix | Particulares carne vacuna −2,7 pp (antes −2,5). |
| 24 | Eventos | Suba de precio con 8 semanas: +12 % [−23; +64], sigue preliminar. Agregar baja de pauta (preliminar, sin efecto detectable: EMD ±45 %). |
| 25 | Meta Ads | 44 semanas, nueva elasticidad del gasto y los clics; recomendación igual. |
| **nueva** | **Meta: clics y el cambio del 05/09** | Clics vs. clientes nuevos (elasticidad +0,27, Granger p = 0,034) y el cambio de reparto del 05/09 (−7 % [−50; +265], sin efecto). Correlación, no causa. |
| 26 | Plan de compras | Costos ponderados por XL, p = 45, plan de la semana 16/11–21/11/2026 (empresas con datos de agosto). |
| **nueva** | **De platos a ingredientes** | La cadena plan → platos → receta → merma → kg por proveedor; índice por familia; 9,5 % de viandas sin receta. Sin números de recetas ni proveedores. |
| 27 | Decisiones clave | Agregar: empresas termina en agosto, corte en la última semana completa, XL × 1,30. |
| 28 | Limitaciones y trabajo futuro | Agregar: sin empresas sep–nov, sin UTM (atribución por anuncio), platos sin receta, baja de pauta con 2 semanas. |
