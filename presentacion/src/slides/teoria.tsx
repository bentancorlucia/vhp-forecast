// Método · la teoría de series temporales, contada sobre los datos de Viandas y en el orden del flujo (etapas 2–5).
import type { FC, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Cifra, K, Paso, Periodo, useAnimar, useDatos, useVisto } from '../components/marca';

const MDiv = motion.div as unknown as FC<Record<string, unknown>>;
import { Correlograma, StlPaneles, WalkForward } from '../charts/graficos';
import { diaSemana, fechaCorta, fechaLarga, num, pctSigned, pval } from '../lib/format';
import type { Diapo } from './tipos';

const S = 'Método';

// ---------------------------------------------------------------- 5. componentes y STL
function Componentes() {
  const { meta, eda } = useDatos();
  const ten = eda.efectos['Total|tendencia (por semana)'];
  const ver = eda.efectos['Total|verano'];
  const Dato = ({ cifra, que, ic, color }: { cifra: string; que: ReactNode; ic: string; color: string }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <Cifra texto={cifra} tam={92} color={color} style={{ whiteSpace: 'nowrap' }} />
      <span style={{ fontSize: 22 }}>{que}</span>
      <span style={{ fontSize: 16, color: 'var(--tinta-45)' }}>IC 95 % {ic}</span>
    </div>
  );
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.9fr', gap: 56, height: '100%' }}>
      <div className="col" style={{ justifyContent: 'center', gap: 36 }}>
        <Paso n={0}>
          <p className="pregunta" style={{ margin: 0 }}>¿Crece? ¿Se repite cada semana?</p>
          <p style={{ fontSize: 19, margin: '12px 0 0', color: 'var(--tinta-70)' }}><b>STL</b> (<i>Seasonal-Trend decomposition with Loess</i>) parte la serie en tres curvas que, sumadas, la reconstruyen. Cada una se estima con regresiones locales.</p>
        </Paso>
        <Paso n={2}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 34, borderLeft: '5px solid var(--oro)', paddingLeft: 28 }}>
            <Dato cifra={pctSigned(ten.ef, 1)} que="de crecimiento por semana" ic={`[${pctSigned(ten.lo, 1)}; ${pctSigned(ten.hi, 1)}]`} color="var(--ambar)" />
            <Dato cifra={pctSigned(ver.ef, 0)} que="en enero, por el verano" ic={`[${pctSigned(ver.lo, 0)}; ${pctSigned(ver.hi, 0)}]`} color="var(--tinta)" />
            <Periodo>Regresión de log(y) con calendario, {meta.datosPeriodo}</Periodo>
          </div>
        </Paso>
      </div>
      <Paso n={1} style={{ position: 'relative', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <StlPaneles w={880} h={600} bajadas={['lo que se vendió', 'el nivel, sin el vaivén', 'el patrón de lunes a sábado', 'lo que queda: días raros']} />
        <Periodo>STL robusta, período {meta.periodo} (semana hábil), Total de viandas, {meta.datosPeriodo}</Periodo>
      </Paso>
    </div>
  );
}

// ---------------------------------------------------------------- 11. ML para series
/** Árbol mínimo: raíz, dos ramas, cuatro hojas. */
function Arbol({ x, op = 1 }: { x: number; op?: number }) {
  const n = [[x, 14], [x - 26, 54], [x + 26, 54], [x - 39, 94], [x - 13, 94], [x + 13, 94], [x + 39, 94]];
  const e = [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5], [2, 6]];
  return (
    <g opacity={op}>
      {e.map(([a, b]) => <line key={`${a}${b}`} x1={n[a][0]} y1={n[a][1]} x2={n[b][0]} y2={n[b][1]} stroke="var(--tinta-45)" strokeWidth={2} />)}
      {n.map(([cx, cy], i) => <circle key={i} cx={cx} cy={cy} r={i < 3 ? 8 : 6} fill={i < 3 ? 'var(--blanco)' : 'var(--oro)'} stroke="var(--tinta)" strokeWidth={i < 3 ? 2 : 0} />)}
    </g>
  );
}

function Boosting() {
  const xs = [70, 230, 390];
  return (
    <svg viewBox="0 0 640 112" width="100%" style={{ display: 'block', overflow: 'visible' }}>
      {xs.map((x, i) => <Arbol key={x} x={x} op={1 - i * 0.22} />)}
      {[150, 310].map((x) => <text key={x} x={x} y={62} textAnchor="middle" fontSize={34} fill="var(--ambar)" fontWeight={300}>+</text>)}
      <text x={470} y={62} textAnchor="middle" fontSize={30} fill="var(--tinta-45)">…</text>
      <text x={520} y={64} fontSize={34} fill="var(--tinta)" fontFamily="var(--f-titulo)" fontWeight={600}>= ŷ</text>
    </svg>
  );
}

function Red() {
  const ent = [20, 60, 100], ocu = [8, 40, 72, 104], sal = 60;
  const X = [130, 330, 530];
  const etq = ['o', 'o−5', 'o−11'];
  return (
    <svg viewBox="0 0 640 112" width="100%" style={{ display: 'block', overflow: 'visible' }}>
      {ent.flatMap((a) => ocu.map((b) => <line key={`${a}-${b}`} x1={X[0]} y1={a} x2={X[1]} y2={b} stroke="var(--tinta-25)" strokeWidth={1.5} />))}
      {ocu.map((b) => <line key={`o${b}`} x1={X[1]} y1={b} x2={X[2]} y2={sal} stroke="var(--tinta-25)" strokeWidth={1.5} />)}
      {ent.map((y, i) => <g key={y}>
        <text x={X[0] - 22} y={y + 6} textAnchor="end" fontSize={17} fill="var(--tinta-70)" fontStyle="italic">y<tspan fontSize={12} dy={4}>{etq[i]}</tspan></text>
        <circle cx={X[0]} cy={y} r={9} fill="var(--blanco)" stroke="var(--tinta)" strokeWidth={2} />
      </g>)}
      {ocu.map((y) => <circle key={y} cx={X[1]} cy={y} r={9} fill="var(--crema-osc)" stroke="var(--oro)" strokeWidth={2} />)}
      <circle cx={X[2]} cy={sal} r={12} fill="var(--ambar)" />
      <text x={X[2] + 26} y={sal + 10} fontSize={34} fill="var(--tinta)" fontFamily="var(--f-titulo)" fontWeight={600}>ŷ</text>
    </svg>
  );
}

function Modelo({ titulo, sub, children, idea }: { titulo: string; sub: string; children: ReactNode; idea: ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14 }}>
        <h3 style={{ margin: 0, fontSize: 34 }}>{titulo}</h3>
        <span style={{ fontSize: 16, color: 'var(--tinta-45)', letterSpacing: '0.06em', textTransform: 'uppercase', fontWeight: 600 }}>{sub}</span>
      </div>
      {children}
      <p style={{ margin: 0, fontSize: 20, color: 'var(--tinta-70)' }}>{idea}</p>
    </div>
  );
}

/** Línea de tiempo mínima: 12 días hasta el sábado de origen (rezagos) y los 6 a pronosticar. */
function Rezagos({ pasado, futuro, origen }: { pasado: number[]; futuro: number[]; origen: string }) {
  const max = Math.max(...pasado, ...futuro);
  const alto = (v: number) => (v / max) * 66;
  const B = 86, W = 24, P = 34, X0 = 448;
  const marca: Record<number, string> = { 0: 'o', 5: 'o−5', 11: 'o−11' };
  return (
    <svg viewBox="0 0 660 128" width="100%" style={{ display: 'block', overflow: 'visible' }}>
      {pasado.map((v, j) => {
        const k = pasado.length - 1 - j, x = 10 + j * P, m = marca[k];
        return <g key={j}>
          <rect x={x} y={B - alto(v)} width={W} height={alto(v)} rx={3} fill={m ? 'var(--tinta)' : 'var(--tinta-25)'} />
          {m && <text x={x + W / 2} y={B + 24} textAnchor="middle" fontSize={17} fill="var(--tinta)" fontStyle="italic">y<tspan fontSize={12} dy={4}>{m}</tspan></text>}
        </g>;
      })}
      <line x1={X0 - 15} x2={X0 - 15} y1={4} y2={B + 6} stroke="var(--tinta-45)" strokeWidth={1.5} strokeDasharray="3 4" />
      <text x={X0 - 22} y={12} textAnchor="end" fontSize={14} fill="var(--tinta-70)" fontWeight={600}>{origen}</text>
      {futuro.map((v, j) => {
        const x = X0 + j * P;
        return <g key={j}>
          <rect x={x} y={B - alto(v)} width={W} height={alto(v)} rx={3} fill="var(--crema-osc)" stroke="var(--ambar)" strokeWidth={1.5} />
          <text x={x + W / 2} y={B + 24} textAnchor="middle" fontSize={15} fill="var(--ambar)" fontWeight={700}>{j + 1}</text>
        </g>;
      })}
      <text x={X0 + 2.5 * P + W / 2} y={12} textAnchor="middle" fontSize={14} fill="var(--ambar)" fontWeight={600}>a pronosticar (h)</text>
    </svg>
  );
}

function MachineLearning() {
  const { meta, serie } = useDatos();
  // Igual que lgbm._rasgos_lags: origen = último sábado con 6 días por delante; todo / nivel (media de los 6 días hasta el origen).
  const tot = serie.filter((s) => s.e != null).map((s) => ({ f: s.f, y: s.p + s.e! })); // Total (días con los dos segmentos)
  const H = meta.horizonte;
  const o = tot.length - 1 - H;
  const media = (i: number, j: number) => tot.slice(i, j + 1).reduce((acc, d) => acc + d.y, 0) / (j - i + 1);
  const nivel = media(o - H + 1, o);
  const lag = (k: number) => tot[o - k].y / nivel;
  const base = { l0: lag(0), l5: lag(5), l11: lag(11), mm: media(o - 2 * H + 1, o - H) / nivel };
  const filas = Array.from({ length: H }, (_, i) => ({ h: i + 1, f: tot[o + i + 1].f, y: tot[o + i + 1].y / nivel }));
  const obj = { background: 'var(--crema-osc)' };
  const fijo = { color: 'var(--tinta-45)' };
  return (
    <div className="grid2" style={{ gap: 96 }}>
      <div className="col" style={{ justifyContent: 'center', gap: 22 }}>
        <Paso n={0}>
          <p className="pregunta" style={{ margin: 0, fontSize: '26px' }}>Un <b>rezago</b> es lo vendido <i>k</i> días hábiles antes del sábado: <K t="y_{o-k}" />.</p>
          <div style={{ marginTop: 18 }}><Rezagos pasado={tot.slice(o - 11, o + 1).map((d) => d.y)} futuro={tot.slice(o + 1, o + 1 + H).map((d) => d.y)} origen={`${diaSemana(tot[o].f).slice(0, 3)} ${fechaCorta(tot[o].f)}`} /></div>
        </Paso>
        <Paso n={0}>
          <p style={{ margin: '0 0 8px', fontSize: 20, color: 'var(--tinta-80)' }}>Una <b>fila por día a pronosticar</b>, siempre con los rezagos del sábado:</p>
          <table className="tabla">
            <thead><tr>
              <th style={{ color: 'var(--ambar)' }}><K t="h" /></th><th>día</th>
              <th className="n"><K t="y_{o}" /></th><th className="n"><K t="y_{o-5}" /></th><th className="n"><K t="y_{o-11}" /></th><th className="n">sem. ant.</th>
              <th className="n" style={{ ...obj, color: 'var(--tinta)', borderRadius: '8px 8px 0 0' }}><K t="y_{o+h}" /></th>
            </tr></thead>
            <tbody>{filas.map((r, i) => (
              <tr key={r.f}>
                <td style={{ color: 'var(--ambar)', fontWeight: 700 }}>{r.h}</td>
                <td>{diaSemana(r.f).slice(0, 3)} {fechaCorta(r.f)}</td>
                {[base.l0, base.l5, base.l11, base.mm].map((v, j) => <td key={j} className="n" style={i ? fijo : { color: 'var(--tinta-80)' }}>{num(v, 2)}</td>)}
                <td className="n" style={obj}><b>{num(r.y, 2)}</b></td>
              </tr>
            ))}</tbody>
          </table>
          <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <Periodo>¿Por qué el sábado? Es el último dato al planificar la semana: el martes todavía no se conoce, y no se usan pronósticos como datos</Periodo>
            <Periodo>Todo va dividido por el nivel (media de esa semana): saca la tendencia, que los árboles no saben extrapolar</Periodo>
          </div>
        </Paso>
      </div>
      <div className="col" style={{ justifyContent: 'center', gap: 64 }}>
        <Paso n={1}>
          <Modelo titulo="LightGBM" sub="boosting" idea="cada árbol corrige lo que erraron los anteriores">
            <Boosting />
          </Modelo>
        </Paso>
        <Paso n={2}>
          <Modelo titulo="MLP" sub="red neuronal" idea="las mismas columnas entran a una red chica">
            <Red />
          </Modelo>
        </Paso>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- 12. walk-forward
/** Sello de goma: aparece grande, cae y queda estampado sobre el post-it. */
function SelloGoma({ texto }: { texto: string }) {
  const animar = useAnimar();
  return (
    <MDiv
      className="sello-goma"
      initial={animar ? { scale: 2.6, opacity: 0, rotate: -4 } : false}
      animate={{ scale: 1, opacity: 1, rotate: -9 }}
      transition={animar ? { delay: 0.9, type: 'spring', stiffness: 420, damping: 18, mass: 0.9 } : { duration: 0 }}
    >
      <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden>
        <filter id="tinta-sello">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={7} result="ruido" />
          <feColorMatrix in="ruido" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.6 1.55" result="huecos" />
          <feComposite in="SourceGraphic" in2="huecos" operator="in" result="gastado" />
          <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves={2} seed={3} result="borde" />
          <feDisplacementMap in="gastado" in2="borde" scale={3} />
        </filter>
      </svg>
      <span>{texto}</span>
    </MDiv>
  );
}

function Validacion() {
  const { meta } = useDatos();
  const visto = useVisto(2);
  const animar = useAnimar();
  return (
    <div className="grid-6-4" style={{ alignItems: 'center' }}>
      <div className="col" style={{ gap: 28 }}>
        <Paso n={0}><p className="pregunta" style={{ margin: 0 }}>Validar como se va a usar: <b>cada sábado</b>, entrenar con todo lo anterior y pronosticar la semana siguiente.</p></Paso>
        <Paso n={1}><WalkForward w={860} h={500} /><Periodo>{meta.nOrigenes} orígenes · semanas pronosticadas {meta.btPeriodo}</Periodo></Paso>
      </div>
      <div className="col" style={{ justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
        <Paso n={2}>
          <MDiv
            className="postit"
            animate={visto && animar ? { scale: [1, 1, 0.97, 1.01, 1], rotate: [2, 2, 1.2, 2.2, 2] } : { rotate: 2 }}
            transition={{ duration: 0.5, delay: 0.95, times: [0, 0.02, 0.25, 0.6, 1] }}
          >
            <span className="postit-cinta" aria-hidden />
            <p>Si el modelo ve algo del futuro, el error sale <b>más chico de lo real</b>.</p>
            {visto && <SelloGoma texto="Data leakage" />}
          </MDiv>
        </Paso>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- ADF + ACF: qué SARIMA pide la serie
function Estructura() {
  const { meta, eda } = useDatos();
  const [nivel, dif] = eda.estacionariedad;
  const r6 = eda.autocorr.nivel.acf[meta.periodo];
  const s = meta.periodo;
  const Cab = ({ n, children }: { n: number; children: ReactNode }) => (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 14 }}>
      <span style={{ fontFamily: 'var(--f-titulo)', fontSize: 30, fontWeight: 600, color: 'var(--ambar)' }}>{n}</span>
      <span style={{ fontSize: 26 }}>{children}</span>
    </div>
  );
  const Cifra2 = ({ v, que, ver, color = 'var(--tinta)' }: { v: string; que: string; ver?: string; color?: string }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontFamily: 'var(--f-titulo)', fontSize: 56, fontWeight: 600, lineHeight: 1, whiteSpace: 'nowrap', color }}>{v}</span>
      <span style={{ fontSize: 15, color: 'var(--tinta-70)', letterSpacing: '0.06em', textTransform: 'uppercase', fontWeight: 600, whiteSpace: 'nowrap' }}>{que}</span>
      {ver && <span style={{ fontSize: 17, fontWeight: 700, color }}>{ver}</span>}
    </div>
  );
  const Texto = ({ children }: { children: ReactNode }) => <p style={{ margin: 0, fontSize: 19, lineHeight: 1.45, color: 'var(--tinta-80)' }}>{children}</p>;
  const grafico = (serie: 'nivel' | 'dif', eje: string) => (
    <Correlograma w={672} h={325} tipo="acf" serie={serie} titulo={eje} min={-0.38} ejeX={eje} simple />
  );
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'space-between' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64 }}>
        <Paso n={0}>
          <div className="col" style={{ gap: 18 }}>
            <Cab n={1}>¿Se <b>repite</b> cada semana?</Cab>
            {grafico('nivel', 'k = días hábiles atrás')}
            <div style={{ display: 'flex', gap: 32, alignItems: 'center' }}>
              <Cifra2 v={num(r6, 2)} que={`ACF a ${s} días`} />
              <Texto><b>ACF</b>: cuánto se parece cada día al de <i>k</i> días antes (1 = igual, 0 = nada). Salta cada {s}: <b>el lunes se parece al lunes anterior</b>. Dentro de la franja <span style={{ display: 'inline-block', width: 22, height: 12, background: 'var(--crema-osc)', borderRadius: 3, verticalAlign: 'middle' }} /> es azar.</Texto>
            </div>
          </div>
        </Paso>
        <Paso n={1}>
          <div className="col" style={{ gap: 18 }}>
            <Cab n={2}>¿Su nivel es <b>estable</b>?</Cab>
            {grafico('dif', 'k = días hábiles atrás, restando la semana anterior')}
            <div style={{ display: 'flex', gap: 32, alignItems: 'center' }}>
              <Cifra2 v={num(nivel.p, 2)} que="ventas tal cual" ver="no estable" />
              <Cifra2 v={pval(dif.p).replace(/\s/g, '')} que="restando la semana" ver="estable" color="var(--ambar)" />
              <Texto><b>p del test ADF</b>: ¿el nivel se mantiene estable? Si p &gt; 0,05, <b>no</b>.</Texto>
            </div>
          </div>
        </Paso>
      </div>
      <Paso n={2}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 28, background: 'var(--crema-osc)', borderRadius: 14, padding: '18px 28px' }}>
          <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--tinta-70)', whiteSpace: 'nowrap' }}>La serie pide</span>
          <span style={{ fontSize: 28, whiteSpace: 'nowrap' }}><K t={`\\text{SARIMA}\\,(p,0,q)(P,1,Q)_{${s}}`} /></span>
          <span style={{ fontSize: 18, color: 'var(--tinta-80)', lineHeight: 1.5 }}>
            <b>6</b>: se repite cada {s} días <span style={{ color: 'var(--tinta-45)' }}>·</span> <b>1</b>: hay que restar la semana anterior para que sea estable <span style={{ color: 'var(--tinta-45)' }}>·</span> <b>Q</b>: el pico negativo en {s} pide corregir con el error de la semana pasada.
          </span>
        </div>
      </Paso>
    </div>
  );
}

// ---------------------------------------------------------------- los candidatos: referencias, ETS, SARIMA
function Col({ n, paso, titulo, archivo, que, tex, pie, cifra, etiqueta, destacada }: {
  n: string; paso: number; titulo: string; archivo: string; que: ReactNode; tex: string; pie: ReactNode; cifra: string; etiqueta: string; destacada?: boolean;
}) {
  // La cifra se monta recién cuando su paso se ve: así cuenta una vez, a la vista.
  const visto = useVisto(paso);
  return (
  <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '0 40px', borderLeft: n === '01' ? 'none' : '1px solid var(--tinta-12)' }}>
    <span className="fr" style={{ fontSize: 20, color: 'var(--ambar)', fontWeight: 600 }}>{n}</span>
    <h3 style={{ margin: '6px 0 4px', fontSize: 38 }}>{titulo}</h3>
    <span className="mono" style={{ fontSize: 14, color: 'var(--tinta-45)' }}>{archivo}</span>
    <p style={{ fontSize: 19.5, lineHeight: 1.5, margin: '24px 0 0', minHeight: 146, color: 'var(--tinta-80)' }}>{que}</p>
    <div style={{ fontSize: 24, margin: '22px 0 0', minHeight: 70, display: 'flex', alignItems: 'center' }}><K t={tex} /></div>
    <p style={{ fontSize: 16, margin: '8px 0 0', color: 'var(--tinta-45)' }}>{pie}</p>
    <div style={{ marginTop: 'auto', display: 'flex', alignItems: 'baseline', gap: 14 }}>
      {visto
        ? <Cifra texto={cifra} tam={76} color={destacada ? 'var(--tinta)' : 'var(--ambar)'} />
        : <span className="cifra" style={{ fontSize: 76, visibility: 'hidden' }}>{cifra}</span>}
      <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--tinta-70)' }}>{etiqueta}</span>
    </div>
  </div>
  );
}

function Candidatos() {
  const { meta, total } = useDatos();
  const ej = total.ejemplo.modelos;
  const f = total.ejemplo.fecha;
  const s = meta.periodo;
  const mase = (id: string) => total.metricas.find((m) => m.id === id)?.mase;
  return (
    <div className="col" style={{ gap: 40, height: '100%' }}>
      <Paso n={0}><p className="pregunta" style={{ margin: 0, fontSize: 27 }}>El simple marca la vara: <b>si no le ganás, no sirve</b>.</p></Paso>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', flex: 1, minHeight: 0, margin: '0 -40px' }}>
        <Paso n={0} style={{ height: '100%' }}>
          <Col n="01" paso={0} titulo="Naive estacional" archivo="models/baselines.py" destacada
            que={<>Para pronosticar un lunes, <b>copia el lunes pasado</b>. No aprende nada: es el piso que cualquier modelo tiene que superar. Su variante promedia las últimas 4 semanas.</>}
            tex={`\\hat y_{t+h} = y_{t+h-${s}}`}
            pie={<>{diaSemana(f)} {fechaCorta(f)}: copia {num(ej.naive_estacional.yhat)}, real {num(ej.naive.y)}</>}
            cifra={num(mase('naive_estacional'), 3)} etiqueta="MASE · la vara" />
        </Paso>
        <Paso n={1} style={{ height: '100%' }}>
          <Col n="02" paso={1} titulo="ETS" archivo="models/ets.py"
            que={<>Lleva un <b>nivel</b>, una <b>tendencia</b> y un <b>patrón por día</b>, y los corrige con cada dato nuevo. <K t="\alpha" /> decide cuánto pesa lo último: alto, reacciona rápido; bajo, es más estable. Abajo, la ecuación del nivel (<K t="b" /> = tendencia amortiguada por <K t="\phi" />).</>}
            tex={`\\ell_t = \\alpha\\,(y_t - s_{t-${s}}) + (1-\\alpha)\\,(\\ell_{t-1} + \\phi\\, b_{t-1})`}
            pie="aditiva o multiplicativa, con o sin tendencia: la elige el AIC cada sábado"
            cifra={num(mase('ets'), 3)} etiqueta="MASE" />
        </Paso>
        <Paso n={2} style={{ height: '100%' }}>
          <Col n="03" paso={2} titulo="SARIMA" archivo="models/sarimax.py"
            que={<>Una regresión sobre su propio pasado: <b>valores</b> (AR) y <b>errores</b> (MA) de los días previos (<i>p, q</i>) y de la semana previa (<i>P, Q</i>). El <b>1</b> resta la semana anterior para que el nivel sea estable.<br /><b>+ calendario = SARIMAX</b> (lo probamos y lo descartamos).</>}
            tex={`(p,0,q)(P,1,Q)_{${s}}`}
            pie={<>36 combinaciones de p, q, P, Q: gana la de menor AIC<br />último sábado: <span className="mono">{total.sarimaUltimo}</span></>}
            cifra={num(mase('sarima'), 3)} etiqueta="MASE" />
        </Paso>
      </div>
      <Paso n={2}>
        <p style={{ margin: 0, fontSize: 17, color: 'var(--tinta-70)' }}>
          <Periodo>MASE: menor es mejor (se explica en Métricas)</Periodo>
        </p>
      </Paso>
    </div>
  );
}

export const COMPONENTES: Diapo = { id: 'componentes', seccion: S, etapa: 2, titulo: '¿Qué forma tiene la demanda?', pasos: 3, Comp: Componentes,
  notas: (d) => `Pensamos la serie como tendencia más estacionalidad más ruido. La estacionalidad tiene período ${d.meta.periodo} porque la semana hábil tiene ${d.meta.periodo} días. STL, en eda.py, lo separa: la tendencia crece, enero cae por el verano y el patrón semanal se agranda con el nivel.` };
export const ESTRUCTURA: Diapo = { id: 'estructura', seccion: S, etapa: 2, titulo: '¿Qué modelo pide la serie?', pasos: 3, Comp: Estructura,
  notas: (d) => `La ACF mide cuánto se parece la serie a sí misma k días atrás: los picos en ${d.meta.periodo}, ${2 * d.meta.periodo}, ${3 * d.meta.periodo} son la semana. El ADF dice que en nivel no es estacionaria y que con la diferencia estacional sí. Después de diferenciar queda un pico negativo en ${d.meta.periodo}. Conclusión: SARIMA con una diferencia estacional, ninguna normal, y un MA estacional.` };
export const CANDIDATOS: Diapo = { id: 'candidatos', seccion: S, etapa: 3, titulo: 'Los candidatos: de simple a complejo', pasos: 3, Comp: Candidatos,
  notas: () => 'Primero, modelos tontos: el naive estacional copia la semana pasada y es la vara. Mirá el ejemplo: para el lunes 24/08 el naive copia el lunes anterior, el 17/08, que es justo el día del export incompleto, y por eso le erra muchísimo. Después, ETS, que pesa más lo reciente, y SARIMA, con los órdenes que pidió la exploración, elegidos por AIC cada sábado. Todos tienen la misma interfaz en el código, así el backtest los compara igual.' };
export const ML: Diapo = { id: 'ml', seccion: S, etapa: 3, titulo: 'Machine learning: la serie como tabla', pasos: 3, Comp: MachineLearning,
  notas: () => 'Para usar los modelos de ML del curso, transformamos la serie en una tabla: cada fila es un día y las columnas son los valores de días anteriores. LightGBM suma árboles que corrigen los errores de los anteriores; el MLP, en PyTorch, es una red chica. Estrategia directa: desde cada sábado hay una fila por horizonte, con los rezagos de ese sábado; todo va dividido por el nivel de la semana porque los árboles no extrapolan la tendencia.' };
export const WALK: Diapo = { id: 'walk-forward', seccion: S, etapa: 4, titulo: 'Validar: Walk-Forward', pasos: 3, Comp: Validacion,
  notas: (d) => `Validamos como se va a usar: cada sábado se entrena con todo lo anterior y se pronostica la semana. Son ${d.meta.nOrigenes} sábados, del ${fechaLarga(d.meta.origenes[0])} en adelante. Lo importante es que nada del futuro se cuele: si pasa, el error sale artificialmente chico.` };
