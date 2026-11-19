import type { FC, ReactNode } from 'react';
import type { Datos } from '../lib/tipos';

export interface Diapo {
  id: string;
  seccion: string;
  titulo: string;
  /** Título con marcado (resaltes); si falta se usa `titulo`. */
  tituloRico?: ReactNode;
  /** Cantidad de pasos de revelado (1 = todo junto). */
  pasos: number;
  /** Notas del orador: 2–4 frases en voseo. */
  notas: (d: Datos) => string;
  Comp: FC;
  /** true = la diapositiva dibuja su propio marco (portada, cierre). */
  propia?: boolean;
  /** true = no muestra el título grande (se conserva la ruta de secciones). */
  sinTitulo?: boolean;
  /** Etapa del flujo de trabajo (1–6) que muestra la diapositiva. */
  etapa?: number;
  /** Separador de sección (transición con barrido). */
  separador?: boolean;
}
