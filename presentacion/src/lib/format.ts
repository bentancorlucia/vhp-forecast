// Formato numérico y de fechas en español rioplatense (coma decimal).

const cache = new Map<string, Intl.NumberFormat>();
function fmt(min: number, max: number) {
  const k = `${min}-${max}`;
  let f = cache.get(k);
  if (!f) {
    f = new Intl.NumberFormat('es-UY', { minimumFractionDigits: min, maximumFractionDigits: max });
    cache.set(k, f);
  }
  return f;
}

/** Número con `d` decimales fijos. */
export const num = (x: number | null | undefined, d = 0) =>
  x == null || Number.isNaN(x) ? '—' : fmt(d, d).format(x);

/** Número con signo explícito (+ / −). */
export const signed = (x: number, d = 1) => (x > 0 ? '+' : x < 0 ? '−' : '') + num(Math.abs(x), d);

/** Fracción (0–1) como porcentaje. */
export const pctFrac = (x: number, d = 1) => `${num(x * 100, d)} %`;
/** Valor ya en porcentaje. */
export const pct = (x: number, d = 1) => `${num(x, d)} %`;
export const pctSigned = (x: number, d = 1) => `${signed(x, d)} %`;

/** p-valor legible. */
export const pval = (p: number | null) =>
  p == null ? '—' : p < 0.001 ? '< 0,001' : num(p, p < 0.01 ? 3 : 2);

/** 'AAAA-MM-DD' → Date local (sin corrimientos de huso). */
export const toDate = (s: string) => {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
};
const two = (n: number) => String(n).padStart(2, '0');
export const fechaLarga = (s: string) => {
  const [y, m, d] = s.split('-');
  return `${d}/${m}/${y}`;
};
export const fechaCorta = (s: string) => {
  const [, m, d] = s.split('-');
  return `${d}/${m}`;
};
export const dateToCorta = (d: Date) => `${two(d.getDate())}/${two(d.getMonth() + 1)}`;

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
export const mesAnio = (d: Date) => `${MESES[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`;
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
export const diaSemana = (s: string) => DIAS[toDate(s).getDay()];

/** Período 'dd/mm/aaaa–dd/mm/aaaa' a partir de una lista de fechas ISO. */
export const periodo = (fechas: string[]) => {
  if (!fechas.length) return '—';
  let a = fechas[0], b = fechas[0];
  for (const f of fechas) { if (f < a) a = f; if (f > b) b = f; }
  return `${fechaLarga(a)}–${fechaLarga(b)}`;
};

/** «p = 0,49» o «p < 0,001». */
export const peq = (p: number | null) => (p != null && p < 0.001 ? 'p < 0,001' : `p = ${pval(p)}`);
