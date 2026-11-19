import { APERTURA } from './apertura';
import { CANDIDATOS, COMPONENTES, ESTRUCTURA, ML, WALK } from './teoria';
import { DM_LJUNG, ERROR, INTERVALO } from './metricas';
import { DATASET, FLUJO } from './flujo';
import { CIERRE, HALLAZGOS } from './hallazgos';
import { USO } from './uso';
import { SEP_CIERRE, SEP_HALLAZGOS, SEP_USO } from './separadores';
import type { Diapo } from './tipos';

const [PORTADA, NEGOCIO, DATOS] = APERTURA;

/** Etapa del flujo (main.py) de cada diapositiva de resultados: la tira de arriba a la derecha. */
const ETAPA: Record<string, number> = {
  patrones: 2, ranking: 4, dm: 4, 'por-que-lgbm': 4, backtest: 4,
  clima: 5, eventos: 5, 'meta-ads': 5,
  plan: 6, ingredientes: 6, 'modelo-final': 6, 'cod-modelo': 6, colchon: 6, sabado: 6,
};
const conEtapa = (ds: Diapo[]) => ds.map((d) => (ETAPA[d.id] && !d.etapa ? { ...d, etapa: ETAPA[d.id] } : d));

/** Diapos de resultados del modelo que van al final de Método, antes de Hallazgos. */
const METODO_FINAL = ['por-que-lgbm', 'backtest'];


/**
 * Orden: la pregunta → el flujo de trabajo → cada etapa del código con su teoría y su métrica,
 * contada sobre los datos de Viandas → hallazgos → cómo se usa → cierre.
 */
export const DIAPOS: Diapo[] = [
  PORTADA,
  NEGOCIO,
  FLUJO,
  // 1 · Datos
  DATASET,
  // 2 · Explorar
  DATOS,
  COMPONENTES,
  ESTRUCTURA,
  // 3 · Modelar
  CANDIDATOS,
  ML,
  // 4 · Validar y medir
  WALK,
  ERROR,
  INTERVALO,
  DM_LJUNG,
  ...conEtapa(HALLAZGOS.filter((d) => METODO_FINAL.includes(d.id))),
  // 5–6 · Explicar y decidir
  SEP_HALLAZGOS,
  ...conEtapa(HALLAZGOS.filter((d) => !METODO_FINAL.includes(d.id))),
  SEP_USO,
  ...conEtapa(USO),
  SEP_CIERRE,
  ...CIERRE,
];
