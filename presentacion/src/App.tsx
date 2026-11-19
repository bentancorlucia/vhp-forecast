// Motor de la presentación: escenario 16:9 escalado, pasos, teclado, índice (O), notas (N),
// pantalla completa (F), URL #/n, vista del orador (?notas) e impresión (una por página).
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Diapositiva, NumCtx, PasoCtx, useDatos } from './components/marca';
import { DIAPOS } from './slides';
import type { Diapo } from './slides/tipos';

const TOTAL = DIAPOS.length;
const CANAL = 'vhp-presentacion';

/** Una diapositiva renderizada con su marco y su paso. */
export function Render({ i, paso, estatico }: { i: number; paso: number; estatico: boolean }) {
  const d: Diapo = DIAPOS[i];
  const C = d.Comp;
  return (
    <PasoCtx.Provider value={{ paso: estatico ? 99 : paso, estatico }}>
      <NumCtx.Provider value={{ numero: i + 1, total: TOTAL }}>
        {d.propia ? <C /> : (
          <Diapositiva seccion={d.seccion} titulo={d.tituloRico ?? d.titulo} numero={i + 1} total={TOTAL} etapa={d.etapa} sinTitulo={d.sinTitulo}><C /></Diapositiva>
        )}
      </NumCtx.Provider>
    </PasoCtx.Provider>
  );
}

function leerHash(): number {
  const m = window.location.hash.match(/^#\/(\d+)/);
  const n = m ? parseInt(m[1], 10) - 1 : 0;
  return Math.min(Math.max(n, 0), TOTAL - 1);
}

/** Escala para que 1600 × 900 entre en la ventana. */
function useEscala(ref: React.RefObject<HTMLElement>) {
  const [s, setS] = useState(0.5);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setS(Math.min(e.contentRect.width / 1600, e.contentRect.height / 900)));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return s;
}

/** Escala del escenario principal: ocupa toda la ventana. */
function useEscalaVentana() {
  const calc = () => Math.min(window.innerWidth / 1600, window.innerHeight / 900);
  const [s, setS] = useState(calc);
  useEffect(() => {
    const on = () => setS(calc());
    window.addEventListener('resize', on);
    on();
    return () => window.removeEventListener('resize', on);
  }, []);
  return s;
}

/** Estado compartido (diapositiva + paso) entre la presentación y la vista del orador. */
function useNavegacion() {
  const [pos, setPos] = useState<{ i: number; paso: number }>({ i: leerHash(), paso: 0 });
  // El canal se crea dentro del efecto: en desarrollo (StrictMode) React monta, desmonta y
  // vuelve a montar, y un canal creado afuera quedaba cerrado.
  const canal = useRef<BroadcastChannel | null>(null);
  const origen = useRef(false);

  useEffect(() => {
    if (!('BroadcastChannel' in window)) return;
    const c = new BroadcastChannel(CANAL);
    c.onmessage = (e) => { origen.current = true; setPos(e.data); };
    canal.current = c;
    return () => { c.close(); if (canal.current === c) canal.current = null; };
  }, []);
  useEffect(() => {
    const h = `#/${pos.i + 1}`;
    if (window.location.hash !== h) history.replaceState(null, '', `${window.location.search}${h}`);
    if (origen.current) { origen.current = false; return; }
    canal.current?.postMessage(pos);
  }, [pos]);
  useEffect(() => {
    const onHash = () => setPos((p) => (leerHash() === p.i ? p : { i: leerHash(), paso: 0 }));
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const siguiente = useCallback(() => setPos(({ i, paso }) => (paso < DIAPOS[i].pasos - 1 ? { i, paso: paso + 1 } : i < TOTAL - 1 ? { i: i + 1, paso: 0 } : { i, paso })), []);
  const anterior = useCallback(() => setPos(({ i, paso }) => (paso > 0 ? { i, paso: paso - 1 } : i > 0 ? { i: i - 1, paso: DIAPOS[i - 1].pasos - 1 } : { i, paso })), []);
  const ir = useCallback((i: number) => setPos({ i, paso: 0 }), []);
  return { pos, siguiente, anterior, ir };
}

function useTeclas(map: Record<string, () => void>) {
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const t = e.target as HTMLElement;
      if (t.closest('input, textarea, select') && e.key !== 'Escape') return;
      const f = map[e.key] ?? map[e.key.toLowerCase()];
      if (f) { e.preventDefault(); f(); }
    };
    window.addEventListener('keydown', on);
    return () => window.removeEventListener('keydown', on);
  }, [map]);
}

const pantallaCompleta = () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen?.();
};

/** Todas las diapositivas, completas, una por página (para imprimir a PDF). */
function MazoImpresion() {
  return (
    <div className="mazo-impresion">
      {DIAPOS.map((d, i) => <div className="hoja" key={d.id}><Render i={i} paso={99} estatico /></div>)}
    </div>
  );
}

// ---------------------------------------------------------------- transiciones
const EASE = [0.22, 1, 0.36, 1];
/** Entre diapositivas: se desliza en la dirección en que se avanza, con un leve desenfoque. */
const VAR_DESLIZA = {
  entra: (d: number) => ({ x: d * 140, opacity: 0, filter: 'blur(8px)' }),
  centro: { x: 0, opacity: 1, filter: 'blur(0px)', transition: { duration: 0.65, ease: EASE } },
  sale: (d: number) => ({ x: -d * 140, opacity: 0, filter: 'blur(8px)', transition: { duration: 0.45, ease: EASE } }),
};
/** Al entrar a una sección: barrido ámbar que cubre la diapositiva anterior. */
const VAR_BARRIDO = {
  entra: (d: number) => ({ clipPath: d > 0 ? 'inset(0 0 0 100%)' : 'inset(0 100% 0 0)' }),
  centro: { clipPath: 'inset(0 0% 0 0%)', transition: { duration: 0.8, ease: EASE } },
  sale: { opacity: 0, transition: { duration: 0.4, delay: 0.1 } },
};

// ---------------------------------------------------------------- presentación
export function Presentacion() {
  const { pos, siguiente, anterior, ir } = useNavegacion();
  const [indice, setIndice] = useState(false);
  const [notas, setNotas] = useState(false);
  const [imprimiendo, setImprimiendo] = useState(false);
  const datos = useDatos();
  const s = useEscalaVentana();
  const reduce = useReducedMotion() ?? false;

  useEffect(() => {
    const antes = () => flushSync(() => setImprimiendo(true));
    const despues = () => setImprimiendo(false);
    window.addEventListener('beforeprint', antes);
    window.addEventListener('afterprint', despues);
    return () => { window.removeEventListener('beforeprint', antes); window.removeEventListener('afterprint', despues); };
  }, []);

  const teclas = useMemo(() => ({
    ArrowRight: siguiente, ' ': siguiente, PageDown: siguiente, Enter: siguiente,
    ArrowLeft: anterior, PageUp: anterior, Backspace: anterior,
    f: pantallaCompleta, o: () => setIndice((v) => !v), n: () => setNotas((v) => !v),
    Escape: () => { setIndice(false); setNotas(false); },
    Home: () => ir(0), End: () => ir(TOTAL - 1),
  }), [siguiente, anterior, ir]);
  useTeclas(teclas);

  const d = DIAPOS[pos.i];
  const prev = useRef(pos.i);
  const dir = pos.i >= prev.current ? 1 : -1;
  useEffect(() => { prev.current = pos.i; }, [pos.i]);
  return (
    <>
      <div className="escenario" onClick={(e) => { if (!(e.target as HTMLElement).closest('a,button,input,label')) siguiente(); }}>
        <div className="lienzo" style={{ transform: `scale(${s})` }}>
          <div className="lienzo-sombra" />
          <AnimatePresence initial={false} custom={dir}>
            <motion.div key={pos.i} style={{ position: 'absolute', inset: 0, zIndex: d.separador ? 2 : 1 }}
              custom={dir} variants={reduce ? undefined : (d.separador ? VAR_BARRIDO : VAR_DESLIZA)}
              initial={reduce ? false : 'entra'} animate="centro" exit={reduce ? undefined : 'sale'}>
              <Render i={pos.i} paso={pos.paso} estatico={false} />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
      <div className="progreso" style={{ width: `${((pos.i + (pos.paso + 1) / d.pasos) / TOTAL) * 100}%` }} />
      <div className="numero">{pos.i + 1} / {TOTAL}</div>
      {notas && (
        <div className="panel-notas" onClick={(e) => e.stopPropagation()}>
          <b>Notas · {d.titulo}</b><br />{d.notas(datos)}
        </div>
      )}
      {indice && <Indice actual={pos.i} ir={(i) => { ir(i); setIndice(false); }} />}
      {imprimiendo && <MazoImpresion />}
    </>
  );
}

function Indice({ actual, ir }: { actual: number; ir: (i: number) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(300);
  useLayoutEffect(() => {
    const el = ref.current?.querySelector('.mini-marco');
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return (
    <div className="indice" ref={ref} onClick={(e) => e.stopPropagation()}>
      <h2>Índice · {TOTAL} diapositivas <span className="chica">(O para cerrar)</span></h2>
      <div className="indice-grid">
        {DIAPOS.map((d, i) => (
          <button key={d.id} className={`mini ${i === actual ? 'actual' : ''}`} onClick={() => ir(i)}>
            <div className="mini-marco"><div style={{ transform: `scale(${w / 1600})` }}><Render i={i} paso={99} estatico /></div></div>
            <span className="mini-tit">{i + 1}. {d.titulo}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- vista del orador (?notas)
export function VistaNotas() {
  const { pos, siguiente, anterior, ir } = useNavegacion();
  const datos = useDatos();
  const refA = useRef<HTMLDivElement>(null);
  const refB = useRef<HTMLDivElement>(null);
  const sA = useEscala(refA);
  const sB = useEscala(refB);
  const [t0] = useState(() => Date.now());
  const [ahora, setAhora] = useState(Date.now());
  useEffect(() => { const id = setInterval(() => setAhora(Date.now()), 1000); return () => clearInterval(id); }, []);
  const teclas = useMemo(() => ({ ArrowRight: siguiente, ' ': siguiente, ArrowLeft: anterior, Home: () => ir(0) }), [siguiente, anterior, ir]);
  useTeclas(teclas);
  const seg = Math.floor((ahora - t0) / 1000);
  const d = DIAPOS[pos.i];
  return (
    <div className="vista-notas">
      <div className="barra">
        <span className="reloj">{String(Math.floor(seg / 60)).padStart(2, '0')}:{String(seg % 60).padStart(2, '0')}</span>
        <span style={{ fontSize: 22 }}>{pos.i + 1} / {TOTAL} · paso {pos.paso + 1} de {d.pasos}</span>
      </div>
      <div className="col" style={{ minHeight: 0 }}>
        <div className="marco" ref={refA} style={{ aspectRatio: '16 / 9' }}>
          <div style={{ transform: `scale(${sA})` }}><Render i={pos.i} paso={pos.paso} estatico={false} /></div>
        </div>
      </div>
      <div className="col" style={{ minHeight: 0 }}>
        <div className="texto"><b style={{ color: 'var(--ambar)' }}>{d.titulo}</b><br />{d.notas(datos)}</div>
        {pos.i < TOTAL - 1 && (
          <>
            <span className="chica">Siguiente: {DIAPOS[pos.i + 1].titulo}</span>
            <div className="marco" ref={refB} style={{ aspectRatio: '16 / 9' }}>
              <div style={{ transform: `scale(${sB})` }}><Render i={pos.i + 1} paso={99} estatico /></div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- ?imprimir: el mazo completo en pantalla
export function VistaImprimir() {
  useEffect(() => { document.body.classList.add('modo-imprimir'); }, []);
  return <MazoImpresion />;
}
