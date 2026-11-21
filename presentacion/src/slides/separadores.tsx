// Separadores de sección: ámbar a pantalla completa con los temas que vienen.
import { Separador } from '../components/marca';
import type { Diapo } from './tipos';

const sep = (n: number, seccion: string, titulo: string, bajada: string, temas: string[], notas: string): Diapo => ({
  id: `sep-${n}`, seccion, titulo, pasos: 1, propia: true, separador: true, notas: () => notas,
  Comp: () => <Separador n={n} titulo={titulo} bajada={bajada} temas={temas} />,
});

export const SEP_HALLAZGOS = sep(1, 'Hallazgos', 'Hallazgos', 'Qué nos dijeron los pedidos, y qué no se puede afirmar.',
  ['Patrones', 'Clima y mix', 'Eventos', 'Meta Ads', 'Plan de compras'],
  'Ya tenemos las herramientas: ahora, qué encontramos.');
export const SEP_USO = sep(2, 'Cómo se usa', '¿Cómo se usa?', 'Del modelo a la compra del sábado.',
  ['La compra, en una cuenta', 'Su código', 'El colchón', 'El ritual del sábado', 'Qué mejoraría'],
  'Esta parte es la más práctica: qué haría el negocio con esto, cada semana.');
export const SEP_CIERRE = sep(3, 'Cierre', 'Cierre', 'Las decisiones que más pesaron, lo que no sabemos y la conclusión.',
  ['Decisiones clave', 'Limitaciones', 'Conclusión'],
  'Cerramos con las decisiones, las limitaciones y tres frases.');
