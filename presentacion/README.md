# Del pedido al plato — presentación

Presentación web (tipo diapositivas) para la defensa del trabajo final. Vite + React + TypeScript + framer-motion + d3 + KaTeX.

## Uso
```bash
npm install
npm run datos     # lee el repo (solo archivos públicos) → public/data/presentacion.json, y chequea contra resultados.md
npm run dev       # para presentar
npm run build     # dist/ estático
```

| Tecla | Acción |
|---|---|
| → / espacio / clic | siguiente paso |
| ← | paso anterior |
| F | pantalla completa |
| O | índice de diapositivas |
| N | notas del orador |

- `?notas` abre la vista del orador (diapositiva actual, siguiente, notas y reloj), sincronizada con la otra ventana.
- `?imprimir` muestra todas las diapositivas completas; Ctrl/Cmd + P desde cualquier vista imprime una por página (16:9).
- La URL guarda la diapositiva (`#/12`).

## Estructura
- 31 diapositivas, 103 pasos (clics). Orden en `slides/index.ts`: la pregunta → el flujo de trabajo (las 6 etapas de `main.py`) → cada etapa con su teoría y su métrica, contada sobre los datos de Viandas → hallazgos → cómo se usa → cierre.
- Arriba a la derecha, la tira de etapa (1 Datos → 6 Decidir) dice de qué módulo sale cada diapositiva (`etapa` en `slides/tipos.ts`).
- `dataset` en el JSON: columnas del export (de `load.py`), feriados, clima, semanas de Meta y cantidad de tests, todo leído de archivos públicos.

## Datos
- Ningún número está escrito a mano en los componentes: todo sale de `presentacion.json`.
- `scripts/exportar_datos.py` se niega a leer `raw_private`, `interim`, `control`, `.env` y `calidad_datos.csv`, y termina con error si algún número clave no coincide con `reports/resultados.md`.
- Las diapositivas «En código» muestran funciones reales de `../src/vhp/`: el script las extrae con `ast` (sin docstrings), así nunca se desfasan del repo.
- El simulador del colchón recalcula el costo como (sobrante × % sobrante + faltante × % faltante) / 100 con la curva del backtest. El plan pondera los costos por la proporción de XL, así que el simulador (costos de la vianda normal) es una aproximación; la diapositiva lo dice.
- STL y ACF/PACF se recalculan desde `data/processed/` (mismo método que `src/vhp/eda.py`) para dibujarlos con la paleta de la marca.
- Logo: si copiás `logo-tinta.png` a `public/marca/` y volvés a correr `npm run datos`, aparece en la portada y en cada diapositiva.
