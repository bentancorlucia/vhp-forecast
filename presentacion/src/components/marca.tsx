// Piezas de marca: Diapositiva, Paso, Sello, Cifra, Flecha, Polaroid, Formula, Codigo, Nota, Periodo, Icono.
import { createContext, useContext, useEffect, useMemo, useState, type CSSProperties, type FC, type ReactNode } from 'react';
import { animate, motion, useReducedMotion } from 'framer-motion';
import katex from 'katex';
import type { Datos } from '../lib/tipos';

// Con TS 5.6 + framer-motion 11 los tipos de motion.* chocan con los de React (pathLength, style); el comportamiento es el mismo.
const MDiv = motion.div as unknown as FC<Record<string, unknown>>;
const MPath = motion.path as unknown as FC<Record<string, unknown>>;
export const CURVA = [0.22, 1, 0.36, 1] as const;

export const DatosCtx = createContext<Datos | null>(null);
export const useDatos = () => {
  const d = useContext(DatosCtx);
  if (!d) throw new Error('Sin datos');
  return d;
};

/** Secciones en orden (para el indicador de arriba a la derecha). */
export const SECCIONES: { id: string; corto: string }[] = [
  { id: 'Apertura', corto: 'Inicio' },
  { id: 'Método', corto: 'Método' },
  { id: 'Hallazgos', corto: 'Hallazgos' },
  { id: 'Cómo se usa', corto: 'Uso' },
  { id: 'Cierre', corto: 'Cierre' },
];

/** Paso actual dentro de la diapositiva. `estatico` = mostrar todo sin animar (índice, impresión, notas). */
export const PasoCtx = createContext<{ paso: number; estatico: boolean }>({ paso: 99, estatico: true });
export const usePaso = () => useContext(PasoCtx);

/** Número de diapositiva y total (para las que dibujan su propio marco). */
export const NumCtx = createContext({ numero: 0, total: 0 });

/** true si hay que animar (ni estático ni movimiento reducido). */
export function useAnimar() {
  const { estatico } = usePaso();
  const reduce = useReducedMotion() ?? false;
  return !estatico && !reduce;
}

/** Muestra su contenido a partir del paso `n` (0 = desde el principio). */
export function Paso({ n, children, className, style, x = 0, demora = 0 }: {
  n: number; children: ReactNode; className?: string; style?: CSSProperties; x?: number; demora?: number;
}) {
  const { paso } = usePaso();
  const animar = useAnimar();
  const visible = paso >= n;
  return (
    <MDiv
      className={className}
      style={{ ...style, visibility: visible ? 'visible' : 'hidden' }}
      initial={animar && visible ? { opacity: 0, y: 22, x, filter: 'blur(6px)' } : false}
      animate={visible ? { opacity: 1, y: 0, x: 0, filter: 'blur(0px)' } : { opacity: 0, y: animar ? 22 : 0, x: animar ? x : 0, filter: animar ? 'blur(6px)' : 'blur(0px)' }}
      transition={{ duration: animar ? 0.6 : 0, ease: CURVA, delay: animar && visible ? 0.12 + demora : 0 }}
    >
      {children}
    </MDiv>
  );
}

/** ¿El paso `n` ya se mostró? (para gráficos que cambian de estado). */
export const useVisto = (n: number) => usePaso().paso >= n;

export function Marca() {
  const d = useDatos();
  return d.meta.logo
    ? <img className="marca-logo" src="marca/logo-tinta.png" alt="Viandas Hotel del Prado" />
    : <span className="marca-texto">Viandas Hotel del Prado</span>;
}

function Ruta({ seccion }: { seccion?: string }) {
  const k = SECCIONES.findIndex((s) => s.id === seccion);
  return (
    <nav className="ruta" aria-label="Secciones">
      {SECCIONES.map((s, i) => <span key={s.id} className={i === k ? 'on' : i < k ? 'hecha' : ''}>{s.corto}</span>)}
    </nav>
  );
}

export function Diapositiva({ seccion, titulo, children, className = '', sinTitulo }: {
  seccion?: string; titulo?: ReactNode; children: ReactNode; numero: number; total: number; className?: string; etapa?: number; sinTitulo?: boolean;
}) {
  const animar = useAnimar();
  return (
    <section className={`diapo ${className}`}>
      {titulo && (
        <header className="diapo-cab" style={sinTitulo ? { minHeight: 0, marginBottom: 0 } : undefined}>
          {!sinTitulo && <MDiv initial={animar ? { opacity: 0, y: 16 } : false} animate={{ opacity: 1, y: 0 }} transition={{ duration: animar ? 0.7 : 0, ease: CURVA }}>
            <h1>{titulo}</h1>
          </MDiv>}
          <div className="cab-der" style={sinTitulo ? { marginLeft: 'auto' } : undefined}><Ruta seccion={seccion} /></div>
        </header>
      )}
      <div className="cuerpo">{children}</div>
    </section>
  );
}

/** Separador de sección: ámbar a pantalla completa, numeral gigante y los temas que vienen. */
export function Separador({ n, titulo, bajada }: { n: number; titulo: string; bajada: string; temas?: string[] }) {
  const animar = useAnimar();
  return (
    <section className="diapo separador">
      <MDiv className="numeral" initial={animar ? { opacity: 0, y: 120, rotate: -6 } : false} animate={{ opacity: 0.32, y: 0, rotate: 0 }} transition={{ duration: animar ? 1.1 : 0, ease: CURVA }}>{n}</MDiv>
      <MDiv initial={animar ? { opacity: 0, y: 40 } : false} animate={{ opacity: 1, y: 0 }} transition={{ duration: animar ? 0.8 : 0, ease: CURVA, delay: animar ? 0.25 : 0 }}>
        <h1>{titulo}</h1>
        <p className="bajada">{bajada}</p>
      </MDiv>
    </section>
  );
}

/** Período en letra chica, obligatorio al lado de cada número. */
export const Periodo = ({ children }: { children: ReactNode }) => <span className="periodo">{children}</span>;

/**
 * Texto con números que cuentan desde 0 hasta su valor (el primer número del texto).
 * Respeta el formato rioplatense: «1,116», «−30 %», «p = 45».
 */
export function Cuenta({ texto, dur = 1.1 }: { texto: string; dur?: number }) {
  const animar = useAnimar();
  const m = texto.match(/([−-]?)(\d{1,3}(?:\.\d{3})*|\d+)(?:,(\d+))?/);
  const [v, setV] = useState(animar && m ? 0 : 1);
  // Sin bandera de "ya animado": en desarrollo React monta dos veces y la animación cancelada
  // en el primer montaje tiene que poder volver a arrancar (si no, queda en 0).
  useEffect(() => {
    if (!animar || !m) { setV(1); return; }
    setV(0);
    const c = animate(0, 1, { duration: dur, ease: [0.22, 1, 0.36, 1], onUpdate: (x: number) => setV(x) });
    return () => c.stop();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [animar, texto, dur]);
  if (!m || v >= 1) return <>{texto}</>;
  const dec = m[3]?.length ?? 0;
  const objetivo = parseFloat(m[2].replace(/\./g, '') + (dec ? '.' + m[3] : ''));
  const actual = new Intl.NumberFormat('es-UY', { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(objetivo * v);
  return <>{texto.slice(0, m.index!) + m[1] + actual + texto.slice(m.index! + m[0].length)}</>;
}

/** Cifra grande (Fraunces) que cuenta. */
export const Cifra = ({ texto, tam = 96, color = 'var(--tinta)', style }: { texto: string; tam?: number; color?: string; style?: CSSProperties }) => (
  <span className="cifra" style={{ fontSize: tam, color, ...style }}><Cuenta texto={texto} /></span>
);

/** Sello tipo estrella dentada para UN número clave por diapositiva. */
export function Sello({ valor, sub, tam = 210, rot = -8, style }: { valor: ReactNode; sub?: ReactNode; tam?: number; rot?: number; style?: CSSProperties }) {
  const animar = useAnimar();
  const puntos = useMemo(() => {
    const n = 26, R = 49, r0 = 43.5;
    return Array.from({ length: n * 2 }, (_, i) => {
      const a = (Math.PI * i) / n - Math.PI / 2;
      const rr = i % 2 === 0 ? R : r0;
      return `${50 + rr * Math.cos(a)},${50 + rr * Math.sin(a)}`;
    }).join(' ');
  }, []);
  return (
    <MDiv
      className="sello" style={{ width: tam, height: tam, ...style }}
      initial={animar ? { scale: 0.3, rotate: rot - 50, opacity: 0 } : false}
      animate={{ scale: 1, rotate: rot, opacity: 1 }}
      transition={animar ? { type: 'spring', stiffness: 220, damping: 14, delay: 0.15 } : { duration: 0 }}
    >
      <svg viewBox="0 0 100 100" aria-hidden>
        <polygon points={puntos} fill="var(--ambar)" stroke="var(--ambar)" strokeWidth="2.2" strokeLinejoin="round" />
      </svg>
      <div className="sello-txt">
        <span className="sello-num" style={{ fontSize: tam * 0.25 }}>{typeof valor === 'string' ? <Cuenta texto={valor} /> : valor}</span>
        {sub && <span className="sello-sub">{sub}</span>}
      </div>
    </MDiv>
  );
}

/** Flecha dibujada a mano (SVG) de (x1,y1) a (x2,y2), en coordenadas del contenedor posicionado. */
export function Flecha({ de, a, curva = 0.25, color = 'var(--ambar)', grosor = 3.5, demora = 0.3 }: {
  de: [number, number]; a: [number, number]; curva?: number; color?: string; grosor?: number; demora?: number;
}) {
  const animar = useAnimar();
  const [x1, y1] = de, [x2, y2] = a;
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, dx = x2 - x1, dy = y2 - y1;
  const cx = mx - dy * curva, cy = my + dx * curva;
  const ang = Math.atan2(y2 - cy, x2 - cx);
  const L = 18;
  const p1 = [x2 - L * Math.cos(ang - 0.45), y2 - L * Math.sin(ang - 0.45)];
  const p2 = [x2 - L * Math.cos(ang + 0.5), y2 - L * Math.sin(ang + 0.5)];
  const minX = Math.min(x1, x2, cx) - 30, minY = Math.min(y1, y2, cy) - 30;
  const w = Math.max(x1, x2, cx) - minX + 30, h = Math.max(y1, y2, cy) - minY + 30;
  return (
    <svg style={{ position: 'absolute', left: minX, top: minY, overflow: 'visible', pointerEvents: 'none' }} width={w} height={h} viewBox={`${minX} ${minY} ${w} ${h}`} aria-hidden>
      <MPath d={`M${x1},${y1} Q${cx},${cy} ${x2},${y2}`} fill="none" stroke={color} strokeWidth={grosor} strokeLinecap="round"
        initial={animar ? { pathLength: 0 } : false} animate={{ pathLength: 1 }} transition={{ duration: animar ? 0.7 : 0, delay: animar ? demora : 0, ease: 'easeInOut' }} />
      <MPath d={`M${p1[0]},${p1[1]} L${x2},${y2} L${p2[0]},${p2[1]}`} fill="none" stroke={color} strokeWidth={grosor} strokeLinecap="round" strokeLinejoin="round"
        initial={animar ? { opacity: 0 } : false} animate={{ opacity: 1 }} transition={{ delay: animar ? demora + 0.65 : 0, duration: animar ? 0.15 : 0 }} />
    </svg>
  );
}

/** Figura PNG del repo en marco polaroid. */
export function Polaroid({ src, pie, rot = -1.5, alto, style }: { src: string; pie?: string; rot?: number; alto?: number; style?: CSSProperties }) {
  return (
    <figure className="polaroid" style={{ transform: `rotate(${rot}deg)`, margin: 0, ...style }}>
      <img src={`figuras/${src}`} alt={pie ?? src} style={alto ? { height: alto } : undefined} />
      {pie && <figcaption>{pie}</figcaption>}
    </figure>
  );
}

/** Fórmula en KaTeX sobre fondo crema oscura. */
export function Formula({ tex, nota, display = true, style }: { tex: string; nota?: ReactNode; display?: boolean; style?: CSSProperties }) {
  const html = useMemo(() => katex.renderToString(tex, { displayMode: display, throwOnError: false, strict: false }), [tex, display]);
  return (
    <div className="formula" style={style}>
      <div dangerouslySetInnerHTML={{ __html: html }} />
      {nota && <div className="formula-nota">{nota}</div>}
    </div>
  );
}

/** KaTeX en línea, dentro de un párrafo. */
export function K({ t }: { t: string }) {
  const html = useMemo(() => katex.renderToString(t, { displayMode: false, throwOnError: false, strict: false }), [t]);
  return <span className="inline-k" dangerouslySetInnerHTML={{ __html: html }} />;
}

// ---------------------------------------------------------------- código Python resaltado con la paleta
const KW = new Set(['def', 'return', 'for', 'in', 'if', 'else', 'elif', 'not', 'and', 'or', 'is', 'None', 'True', 'False', 'lambda', 'with', 'try', 'except', 'import', 'from', 'as', 'class']);
type Tok = { t: string; c?: string };
function tokenizar(linea: string): Tok[] {
  const re = /(#.*$)|(f?"(?:[^"\\]|\\.)*"|f?'(?:[^'\\]|\\.)*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+)|(.)/g;
  const out: Tok[] = [];
  let m: RegExpExecArray | null;
  let prevDef = false;
  while ((m = re.exec(linea))) {
    if (m[1]) out.push({ t: m[1], c: 'com' });
    else if (m[2]) out.push({ t: m[2], c: 'str' });
    else if (m[3]) out.push({ t: m[3], c: 'num' });
    else if (m[4]) {
      const w = m[4];
      if (KW.has(w)) out.push({ t: w, c: 'kw' });
      else if (prevDef) out.push({ t: w, c: 'fn' });
      else out.push({ t: w });
      if (w === 'def') { prevDef = true; continue; }
    } else out.push({ t: m[0] });
    if (!m[5]) prevDef = false;
  }
  return out;
}
const COLOR_TOK: Record<string, CSSProperties> = {
  kw: { color: 'var(--tinta)', fontWeight: 700 },
  fn: { color: 'var(--ambar)', fontWeight: 700 },
  str: { color: '#a0721c' },
  num: { color: 'var(--ambar)' },
  com: { color: 'var(--tinta-45)', fontStyle: 'italic' },
};

/** Bloque de código real del repo. `marcas`: grupos de líneas (por texto) que se resaltan según el paso. */
export function Codigo({ archivo, codigo, marcas, ancho = 880, maxFs = 19, alto = 600 }: {
  archivo: string; codigo: string; marcas: { busca: string[]; desde: number }[]; ancho?: number; maxFs?: number; alto?: number;
}) {
  const { paso } = usePaso();
  const animar = useAnimar();
  const lineas = codigo.split('\n');
  const largo = Math.max(...lineas.map((l) => l.length));
  // tamaño de letra: que entre a lo ancho (líneas largas) y a lo alto (funciones largas)
  const fs = Math.max(12, Math.min(maxFs, (ancho - 90) / (largo * 0.6), (alto - 80) / (lineas.length * 1.6)));
  // la marca activa = la última cuyo paso ya llegó
  const activa = [...marcas].reverse().find((m) => paso >= m.desde && paso < 99);
  const marcada = (l: string) => !!activa && activa.busca.some((b) => l.includes(b));
  return (
    <div style={{ width: ancho, background: 'var(--blanco)', borderRadius: 18, boxShadow: 'var(--sombra)', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 20px', borderBottom: '1px solid var(--tinta-12)', fontSize: 15, color: 'var(--tinta-70)' }}>
        <span style={{ display: 'flex', gap: 6 }}>{['var(--ambar)', 'var(--oro)', 'var(--crema-osc)'].map((c) => <i key={c} style={{ width: 11, height: 11, borderRadius: 6, background: c, display: 'block' }} />)}</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", marginLeft: 6 }}>{archivo}</span>
      </div>
      <pre style={{ margin: 0, padding: '16px 0 18px', fontFamily: "'JetBrains Mono', monospace", fontSize: fs, lineHeight: 1.6, color: 'var(--tinta)' }}>
        {lineas.map((l, i) => {
          const on = marcada(l);
          return (
            <MDiv key={i} style={{ display: 'flex', paddingRight: 18 }}
              animate={{ backgroundColor: on ? 'rgba(234,154,2,0.16)' : 'rgba(234,154,2,0)', opacity: activa && !on ? 0.42 : 1 }}
              transition={{ duration: animar ? 0.35 : 0 }}>
              <span style={{ width: 52, flex: 'none', textAlign: 'right', paddingRight: 16, color: on ? 'var(--ambar)' : 'var(--tinta-25)', borderRight: `3px solid ${on ? 'var(--ambar)' : 'transparent'}`, marginRight: 14, userSelect: 'none' }}>{i + 1}</span>
              <code style={{ whiteSpace: 'pre' }}>{tokenizar(l).map((t, j) => <span key={j} style={t.c ? COLOR_TOK[t.c] : undefined}>{t.t}</span>)}{l === '' ? ' ' : ''}</code>
            </MDiv>
          );
        })}
      </pre>
    </div>
  );
}

/** Anotación manuscrita (Kalam). Máximo una por diapositiva. */
export const Nota = ({ children, style }: { children: ReactNode; style?: CSSProperties }) => (
  <div className="nota-mano" style={style}>{children}</div>
);

/** Íconos de línea en tinta. */
const ICONOS: Record<string, ReactNode> = {
  calendario: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></>,
  olla: <><path d="M4 10h16v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z" /><path d="M2 10h20M9 6c0-1 1-2 0-3M15 6c0-1 1-2 0-3" /></>,
  carrito: <><path d="M3 4h2l2.5 11h10L20 8H6.5" /><circle cx="9" cy="19" r="1.5" /><circle cx="17" cy="19" r="1.5" /></>,
  grafico: <><path d="M4 4v16h16" /><path d="M7 15l4-5 3 3 5-6" /></>,
  nube: <><path d="M7 18h10a4 4 0 0 0 0-8 6 6 0 0 0-11.5 1.5A3.3 3.3 0 0 0 7 18z" /></>,
  sol: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5" /></>,
  megafono: <><path d="M3 10v4h4l8 5V5L7 10z" /><path d="M18 9a4 4 0 0 1 0 6" /></>,
  balanza: <><path d="M12 3v18M5 21h14M5 7h14" /><path d="M5 7l-3 7h6zM19 7l-3 7h6z" /></>,
  lupa: <><circle cx="10" cy="10" r="6" /><path d="M15 15l6 6" /></>,
  candado: <><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></>,
  persona: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
  edificio: <><rect x="5" y="3" width="14" height="18" rx="1" /><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2" /></>,
  reloj: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  check: <><path d="M4 12l5 5L20 6" /></>,
  pregunta: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17h.01" /></>,
  terminal: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M7 9l3 3-3 3M12 15h5" /></>,
  archivo: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v4h4M9 13h6M9 17h6" /></>,
  postre: <><path d="M5 12h14l-2 8H7z" /><path d="M7 12a5 5 0 0 1 10 0M12 4v3" /></>,
  rayo: <><path d="M13 2L4 14h7l-1 8 9-12h-7z" /></>,
  ruta: <><circle cx="6" cy="18" r="2" /><circle cx="18" cy="6" r="2" /><path d="M8 18h6a4 4 0 0 0 0-8h-4a4 4 0 0 1 0-8h6" /></>,
};
export function Icono({ n, tam = 30, color = 'var(--tinta)' }: { n: keyof typeof ICONOS | string; tam?: number; color?: string }) {
  return (
    <svg width={tam} height={tam} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden style={{ flex: 'none' }}>
      {ICONOS[n]}
    </svg>
  );
}
