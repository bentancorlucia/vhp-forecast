// Método · cómo medimos (etapa 4, evaluate.py): fórmula, cómo se lee y un ejemplo real.
import { K, Paso, Periodo, useDatos } from '../components/marca';
import { Backtest } from '../charts/graficos';
import { fechaCorta, fechaLarga, num, pctFrac, pval } from '../lib/format';
import type { Diapo } from './tipos';
import type { ReactNode } from 'react';

const S = 'Método';

/** Línea de tiempo de las dos ventanas: 12 semanas cada una, se pisan una semana. */
function LineaVentanas() {
  const { total } = useDatos();
  const rb = total.robustez;
  const aFecha = (t: string) => { const [d, m, a] = t.split('/').map(Number); return Date.UTC(a, m - 1, d); };
  const [aIni, aFin] = rb.ventanas.anterior.split('–').map(aFecha);
  const [nIni, nFin] = rb.ventanas.nueva.split('–').map(aFecha);
  const DIA = 864e5, t0 = aIni - 7 * DIA, t1 = nFin + 9 * DIA;
  const W = 1408, X0 = 150, X1 = W - 10;
  const x = (t: number) => X0 + ((t - t0) / (t1 - t0)) * (X1 - X0);
  const semanas = (ini: number, fin: number) => Array.from({ length: Math.floor((fin - ini) / DIA / 7) + 1 }, (_, i) => ini + i * 7 * DIA);
  const filas = [
    { v: 'anterior' as const, nombre: 'Anterior', ini: aIni, fin: aFin, y: 80, fondo: 'var(--oro)' },
    { v: 'nueva' as const, nombre: 'Nueva', ini: nIni, fin: nFin, y: 240, fondo: 'var(--ambar)' },
  ];
  const H = 76;
  const meses = ['jun', 'jul', 'ago', 'sep', 'oct', 'nov'].map((m, i) => ({ m, t: Date.UTC(2026, 5 + i, 1) })).filter((m) => m.t > t0 && m.t < t1);
  return (
    <svg viewBox={`0 0 ${W} 380`} width="100%" style={{ display: 'block', overflow: 'visible' }} role="img" aria-label={`Ventana anterior ${rb.ventanas.anterior} y ventana nueva ${rb.ventanas.nueva}; se superponen ${rb.superposicion}`}>
      {/* semana en común */}
      <rect x={x(nIni) - 6} y={40} width={x(aFin + DIA) - x(nIni) + 12} height={300} rx={12} fill="var(--crema-osc)" />
      <text x={(x(nIni) + x(aFin + DIA)) / 2} y={28} textAnchor="middle" fontSize={17} fill="var(--tinta-70)" fontWeight={600}>1 semana en común</text>
      {filas.map((f) => (
        <g key={f.v}>
          <text x={0} y={f.y + H / 2 - 2} fontSize={30} fontWeight={700} fill="var(--tinta)" fontFamily="var(--f-titulo)">{f.nombre}</text>
          <text x={0} y={f.y + H / 2 + 24} fontSize={17} fill="var(--tinta-70)">{rb.ventanasCortas[f.v]}</text>
          {/* lo que el modelo ya vio */}
          <line x1={X0} x2={x(f.ini) - (f.v === 'nueva' ? 150 : 10)} y1={f.y + H / 2} y2={f.y + H / 2} stroke="var(--tinta-25)" strokeWidth={2} strokeDasharray="2 6" strokeLinecap="round" />
          {semanas(f.ini, f.fin).map((t, i) => (
            <rect key={i} x={x(t) + 2} y={f.y} width={x(t + 6 * DIA) - x(t) - 4} height={H} rx={8} fill={f.fondo} />
          ))}
          <text x={x(f.ini) + 2} y={f.y - 12} fontSize={17} fontWeight={600} fill="var(--tinta-70)">{semanas(f.ini, f.fin).length} semanas pronosticadas →</text>
        </g>
      ))}
      {/* eje de meses */}
      <line x1={X0} x2={X1} y1={358} y2={358} stroke="var(--tinta-12)" />
      {meses.map((m) => (
        <g key={m.m}>
          <line x1={x(m.t)} x2={x(m.t)} y1={352} y2={364} stroke="var(--tinta-25)" />
          <text x={x(m.t) + 6} y={380} fontSize={17} fill="var(--tinta-45)">{m.m}</text>
        </g>
      ))}
    </svg>
  );
}

function Ventanas() {
  const { meta } = useDatos();
  const ideas = [
    { n: 1, t: 'Qué es una ventana', d: <>{meta.nOrigenes} semanas seguidas que el modelo pronostica <b>sin haberlas visto</b>, entrenando cada sábado con todo lo anterior.</> },
    { n: 1, t: 'Por qué dos', d: <>Con una sola, el ganador puede ser <b>suerte de ese período</b>. Si un modelo es bueno, tiene que serlo en las dos.</> },
  ];
  return (
    <div className="col" style={{ height: '100%', gap: 0 }}>
      <Paso n={0}>
        <p className="pregunta" style={{ margin: '0 0 20px' }}>Probamos los modelos en <b>dos períodos distintos</b>, no en uno.</p>
      </Paso>
      <Paso n={0}><LineaVentanas /></Paso>
      <div className="grid2" style={{ gap: 48, marginTop: 'auto' }}>
        {ideas.map((x) => (
          <Paso n={x.n} key={x.t} className="dato">
            <span className="dato-t" style={{ marginTop: 0 }}>{x.t}</span>
            <span className="dato-d" style={{ fontSize: 19 }}>{x.d}</span>
          </Paso>
        ))}
      </div>
    </div>
  );
}

/** Colores de un diagrama según la tarjeta (blanca o ámbar). */
type Tono = { c: string; acc: string; suave: string; fondo: string };

// Ejemplo ilustrativo (no son datos): 6 días, real y pronóstico.
const EJ_REAL = [148, 112, 104, 96, 100, 70];
const EJ_PRON = [132, 118, 100, 108, 92, 74];
const EJ_DIAS = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];

/** MAE: cada tramo vertical es el error de un día; el MAE es su promedio. */
function DiagMae({ t }: { t: Tono }) {
  const y = (v: number) => 170 - (v - 60) * 1.45;
  const x = (i: number) => 40 + i * 64;
  return (
    <svg viewBox="0 0 400 210" width="100%" style={{ display: 'block', overflow: 'visible' }} role="img" aria-label="Errores diarios entre real y pronóstico">
      {EJ_REAL.map((r, i) => {
        const p = EJ_PRON[i];
        return (
          <g key={i}>
            <line x1={x(i)} x2={x(i)} y1={y(r)} y2={y(p)} stroke={t.acc} strokeWidth={6} strokeLinecap="round" />
            <circle cx={x(i)} cy={y(r)} r={8} fill={t.c} />
            <circle cx={x(i)} cy={y(p)} r={7} fill={t.fondo} stroke={t.c} strokeWidth={2.5} />
            <text x={x(i)} y={200} textAnchor="middle" fontSize={15} fill={t.suave}>{EJ_DIAS[i]}</text>
          </g>
        );
      })}
      <circle cx={232} cy={12} r={6} fill={t.c} /><text x={244} y={17} fontSize={14} fill={t.suave}>real</text>
      <circle cx={292} cy={12} r={5.5} fill={t.fondo} stroke={t.c} strokeWidth={2} /><text x={304} y={17} fontSize={14} fill={t.suave}>pronóstico</text>
    </svg>
  );
}

/** WAPE: una barra con todo lo vendido; adentro, la parte que erramos. Ejemplo ilustrativo (los 6 días del MAE). */
function DiagWape({ t }: { t: Tono }) {
  const err = EJ_REAL.reduce((a, r, i) => a + Math.abs(r - EJ_PRON[i]), 0);
  const tot = EJ_REAL.reduce((a, b) => a + b, 0);
  const pct = Math.round((err / tot) * 100);
  const X0 = 10, W = 380, w = Math.max(W * (err / tot), 8);
  return (
    <svg viewBox="0 0 400 210" width="100%" style={{ display: 'block', overflow: 'visible' }} role="img" aria-label={`De todo lo vendido, erramos un ${pct} %`}>
      <text x={X0} y={20} fontSize={16} fill={t.c} fontWeight={600}>todo lo vendido en la semana</text>
      <rect x={X0} y={32} width={W} height={44} rx={8} fill={t.suave} />
      <rect x={X0} y={32} width={w} height={44} rx={8} fill={t.acc} />
      <text x={X0 + W - 14} y={61} textAnchor="end" fontSize={18} fill={t.c} fontWeight={700}>100 %</text>
      <path d={`M ${X0 + w / 2} 80 L ${X0 + w / 2} 112 L ${X0 + w / 2 + 24} 112`} fill="none" stroke={t.acc} strokeWidth={2} />
      <text x={X0 + w / 2 + 32} y={118} fontSize={16} fill={t.c}>lo que erramos, sumando</text>
      <text x={X0 + w / 2 + 32} y={140} fontSize={16} fill={t.c}>los errores de cada día</text>
      <text x={X0} y={196} fontSize={16} fill={t.c}>WAPE = esa parte, en % <tspan fill={t.suave === 'var(--tinta-25)' ? 'var(--tinta-45)' : t.suave}>(acá, {pct} %)</tspan></text>
    </svg>
  );
}

/** MASE: la barra de copiar la semana pasada es la vara (vale 1); el modelo se mide contra ella. Ejemplo ilustrativo. */
function DiagMase({ t }: { t: Tono }) {
  const X0 = 10, uno = 300, m = X0 + (uno - X0) * 0.75;
  return (
    <svg viewBox="0 0 400 210" width="100%" style={{ display: 'block', overflow: 'visible' }} role="img" aria-label="El error del modelo medido con la vara del error de copiar la semana pasada">
      <text x={X0} y={20} fontSize={16} fill={t.c} fontWeight={600}>error de copiar la semana pasada, en el histórico</text>
      <rect x={X0} y={30} width={uno - X0} height={26} rx={6} fill={t.suave} />
      <text x={uno + 12} y={50} fontSize={20} fill={t.c} fontWeight={700}>= 1</text>
      <text x={X0} y={92} fontSize={16} fill={t.c} fontWeight={600}>error del modelo</text>
      <rect x={X0} y={102} width={m - X0} height={26} rx={6} fill={t.c} />
      <text x={uno + 12} y={122} fontSize={20} fill={t.c} fontWeight={700}>= 0,75</text>
      <line x1={uno} x2={uno} y1={58} y2={134} stroke={t.c} strokeWidth={2} strokeDasharray="4 5" />
      <text x={X0} y={170} fontSize={16} fill={t.c}><tspan fontWeight={700}>menos de 1:</tspan> erra menos que copiar en el histórico</text>
      <text x={X0} y={196} fontSize={16} fill={t.c}><tspan fontWeight={700}>más de 1:</tspan> erra más que copiar en el histórico</text>
    </svg>
  );
}

function ErrorPron() {
  const { total } = useDatos();
  const maseNaive = total.metricas.find((m) => m.id === 'naive_estacional')!.mase;
  const items = [
    { n: 0, nombre: 'MAE', sigla: 'Mean Absolute Error', f: '\\frac{1}{n}\\sum |y_t-\\hat y_t|', Diag: DiagMae, mide: <>Cuántas viandas (× K) le erramos <b>por día</b>, en promedio.</> },
    { n: 1, nombre: 'WAPE', sigla: 'Weighted Absolute Percentage Error', f: '\\frac{\\sum |y_t-\\hat y_t|}{\\sum y_t}', Diag: DiagWape, mide: <>Ese error como <b>% de lo vendido</b>: no depende de K.</> },
    { n: 2, nombre: 'MASE', sigla: 'Mean Absolute Scaled Error', f: '\\frac{\\text{MAE}_{\\text{modelo}}}{\\text{MAE}_{\\text{copiar semana pasada}}}', Diag: DiagMase, mide: <>1 = el error que tuvo <b>copiar la semana pasada en el histórico</b>. Por eso, en el backtest, el propio naive da {num(maseNaive, 2)}. Con esta elegimos.</>, hero: true },
  ];
  return (
    <div className="col" style={{ height: '100%', justifyContent: 'center', gap: 26 }}>
      <div className="grid3" style={{ gap: 32, alignItems: 'stretch' }}>
        {items.map((m) => {
          const tinta = m.hero ? 'var(--blanco)' : 'var(--tinta)';
          const suave = m.hero ? 'rgba(255,255,255,.72)' : 'var(--tinta-45)';
          const tono: Tono = m.hero
            ? { c: 'var(--blanco)', acc: 'var(--blanco)', suave: 'rgba(255,255,255,.4)', fondo: 'var(--ambar)' }
            : { c: 'var(--tinta)', acc: 'var(--ambar)', suave: 'var(--tinta-25)', fondo: 'var(--blanco)' };
          return (
            <Paso n={m.n} key={m.nombre} style={{ height: '100%' }}>
              <div style={{ height: '100%', boxSizing: 'border-box', borderRadius: 28, padding: '34px 36px 32px', display: 'flex', flexDirection: 'column', color: tinta, background: m.hero ? 'var(--ambar)' : 'var(--blanco)', boxShadow: 'var(--sombra)' }}>
                <div style={{ fontFamily: 'var(--f-titulo)', fontSize: 64, fontWeight: 650, lineHeight: 1, color: tinta }}>{m.nombre}</div>
                <div style={{ fontSize: 15, marginTop: 8, color: suave }}>{m.sigla}</div>
                <div style={{ fontSize: 30, margin: '22px 0 0', minHeight: 70, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><K t={m.f} /></div>
                <p style={{ margin: '14px 0 22px', fontSize: 22, lineHeight: 1.35, color: tinta }}>{m.mide}</p>
                <div style={{ marginTop: 'auto' }}><m.Diag t={tono} /></div>
              </div>
            </Paso>
          );
        })}
      </div>
      <Paso n={2}>
        <Periodo>En las tres, menor es mejor</Periodo>
      </Paso>
    </div>
  );
}

function Intervalo() {
  const { total, meta } = useDatos();
  const s = total.ejemplo.semana;
  const d0 = s.dias[0];
  const pLo = Math.round((1 - d0.lo / d0.yhat) * 100), pHi = Math.round((d0.hi / d0.yhat - 1) * 100);
  const items = [
    { cifra: `−${pLo} / +${pHi} %`, s: <>Margen alrededor del pronóstico: lo que el modelo <b>se equivocó</b> en las {meta.semanasIntervalo} semanas previas.</> },
    { cifra: '80 %', s: <><b>Lo que promete:</b> el real tiene que quedar dentro de la franja 8 de cada 10 días.</> },
    { cifra: pctFrac(total.cobIC.k / total.cobIC.n, 0), s: <><b>Lo que pasó:</b> en {total.cobIC.k} de los {total.cobIC.n} días quedó adentro, algo por debajo del 80 %. Con {total.cobIC.n} días esa diferencia es compatible con el azar (IC 95 %: {pctFrac(total.cobIC.lo, 0)}–{pctFrac(total.cobIC.hi, 0)}).</> },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 56, height: '100%', alignItems: 'center' }}>
      <div className="col" style={{ gap: 14 }}>
        <div className="leyenda"><span><i style={{ background: 'var(--tinta)' }} />real</span><span><i style={{ background: 'var(--ambar)' }} />pronóstico</span><span><i style={{ background: 'var(--crema-osc)', height: 14 }} />rango 80 %</span></div>
        <Backtest w={990} h={520} soloSemana />
        <Periodo>LightGBM, semana {fechaCorta(s.dias[0].f)}–{fechaLarga(s.dias[s.dias.length - 1].f)} · viandas × K · ○ = cayó afuera</Periodo>
      </div>
      <div className="col" style={{ gap: 40 }}>
        {items.map((x, i) => (
          <Paso n={i} key={i}>
            <div className="cifra" style={{ fontSize: 58, lineHeight: 1, color: i === 2 ? 'var(--ambar)' : 'var(--tinta)', whiteSpace: 'nowrap' }}>{x.cifra}</div>
            <p style={{ margin: '8px 0 0', fontSize: 19, lineHeight: 1.4, color: 'var(--tinta-70)' }}>{x.s}</p>
          </Paso>
        ))}
      </div>
    </div>
  );
}

/** Generador pseudoaleatorio fijo (mismo dibujo en cada render). */
function azar(semilla: number) {
  let x = semilla;
  return () => { x = (x * 16807) % 2147483647; return x / 2147483647 - 0.5; };
}

/** Quién erró menos cada día: calendario de puntos (columnas = semanas, filas = lun–sáb). Datos reales del backtest. */
function DiferenciaDiaria({ a, b }: { a: { f: string; y: number; m: number }[]; b: { f: string; y: number; m: number }[] }) {
  const mb = new Map(b.map((r) => [r.f, Math.abs(r.y - r.m)]));
  const dias = a.filter((r) => mb.has(r.f)).map((r) => ({ f: r.f, gana: Math.abs(r.y - r.m) < mb.get(r.f)! }));
  const t0 = Date.parse(dias.reduce((m, d) => (d.f < m ? d.f : m), dias[0].f) + 'T12:00:00Z');
  const pos = (f: string) => {
    const t = Date.parse(f + 'T12:00:00Z');
    return { sem: Math.floor((t - t0) / 864e5 / 7), dow: (new Date(t).getUTCDay() + 6) % 7 };
  };
  const nSem = Math.max(...dias.map((d) => pos(d.f).sem)) + 1;
  const lg = dias.filter((d) => d.gana).length, mm = dias.length - lg;
  const P = 38, X0 = 34, Y0 = 16;
  const XT = X0 + nSem * P + 50;
  return (
    <svg viewBox="0 0 836 260" width="100%" style={{ display: 'block', overflow: 'visible' }} role="img" aria-label={`LightGBM erró menos ${lg} días y la media móvil ${mm} días`}>
      {['lun', 'mar', 'mié', 'jue', 'vie', 'sáb'].map((t, i) => (
        <text key={t} x={0} y={Y0 + i * P + 6} fontSize={15} fill="var(--tinta-45)">{t}</text>
      ))}
      {dias.map((d) => {
        const p = pos(d.f);
        return <circle key={d.f} cx={X0 + 14 + p.sem * P} cy={Y0 + p.dow * P} r={13} fill={d.gana ? 'var(--ambar)' : 'var(--tinta-25)'} />;
      })}
      <text x={X0} y={Y0 + 6 * P + 10} fontSize={15} fill="var(--tinta-45)">cada punto es un día · cada columna, una semana →</text>
      <text x={XT} y={70} fontSize={64} fill="var(--ambar)" fontFamily="var(--f-titulo)" fontWeight={650}>{lg}</text>
      <text x={XT} y={98} fontSize={18} fill="var(--tinta)">días ganó <tspan fontWeight={700}>LightGBM</tspan></text>
      <text x={XT} y={180} fontSize={64} fill="var(--tinta-45)" fontFamily="var(--f-titulo)" fontWeight={650}>{mm}</text>
      <text x={XT} y={208} fontSize={18} fill="var(--tinta)">días ganó la <tspan fontWeight={700}>media móvil</tspan></text>
    </svg>
  );
}

/** Dos tiras de residuos: una con forma que se repite cada semana y otra sin forma (ruido). Ilustrativo. */
function TirasResiduos() {
  const r = azar(7), q = azar(31);
  const forma = [1, 0.35, -0.2, -0.55, -0.4, 0.1];
  const con = Array.from({ length: 24 }, (_, i) => forma[i % 6] * 0.8 + r() * 0.35);
  const sin = Array.from({ length: 24 }, () => q() * 1.5);
  const W = 836, paso = 640 / 24;
  const tira = (vals: number[], y0: number, color: (i: number) => string) => vals.map((v, i) => (
    <rect key={i} x={196 + i * paso} width={paso * 0.6} rx={2} y={v > 0 ? y0 - v * 60 : y0} height={Math.max(1.5, Math.abs(v * 60))} fill={color(i)} />
  ));
  return (
    <svg viewBox={`0 0 ${W} 380`} width="100%" style={{ display: 'block', overflow: 'visible' }} role="img" aria-label="Residuos con patrón semanal frente a residuos sin patrón">
      <text x={0} y={76} fontSize={21} fill="var(--tinta-70)" fontWeight={600}>Con patrón ✗</text>
      <text x={0} y={102} fontSize={17} fill="var(--tinta-70)">se repite cada lunes</text>
      <line x1={192} x2={W} y1={84} y2={84} stroke="var(--tinta-25)" />
      {tira(con, 84, (i) => (i % 6 === 0 ? 'var(--tinta-70)' : 'var(--tinta-25)'))}
      {[0, 6, 12, 18].map((k) => <text key={k} x={196 + k * paso + paso * 0.3} y={8} textAnchor="middle" fontSize={15} fill="var(--tinta-70)">lun</text>)}

      <text x={0} y={226} fontSize={21} fill="var(--ambar)" fontWeight={700}>Ruido ✓</text>
      <text x={0} y={252} fontSize={17} fill="var(--tinta-70)">así quedaron ETS<tspan x={0} dy={20}>y SARIMA</tspan></text>
      <line x1={192} x2={W} y1={232} y2={232} stroke="var(--tinta-25)" />
      {tira(sin, 232, () => 'var(--ambar)')}
    </svg>
  );
}

function DmLjung() {
  const { total, meta } = useDatos();
  const mm = total.dmLgbm.find((x) => x.m2 === 'media_movil_4sem')!;
  const pmin = Math.min(...total.ljungBox.filter((x) => !x.modelo.startsWith('sarimax')).map((x) => x.p)); // ETS y SARIMA
  const ceja = { fontSize: 15, fontWeight: 700, letterSpacing: '.16em', textTransform: 'uppercase' as const, color: 'var(--ambar)', marginBottom: 6 };
  const sub = { margin: 0, fontSize: 21, lineHeight: 1.4, color: 'var(--tinta-70)' };
  const Resultado = ({ p, titulo, regla, periodo }: { p: string; titulo: string; regla: ReactNode; periodo: string }) => (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 18 }}>
        <span className="cifra" style={{ fontSize: 64, color: 'var(--ambar)', whiteSpace: 'nowrap' }}>{p}</span>
        <span style={{ fontSize: 26, fontWeight: 700 }}>{titulo}</span>
      </div>
      <p style={{ margin: '12px 0 0', fontSize: 19, lineHeight: 1.4, color: 'var(--tinta-70)' }}>{regla}</p>
      <Periodo>{periodo}</Periodo>
    </div>
  );
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1px 1fr', gap: 64, height: '100%' }}>
      <div className="col" style={{ gap: 28 }}>
        <Paso n={0}>
          <div style={ceja}>Diebold-Mariano</div>
          <h2 style={{ margin: '0 0 6px' }}>¿Un modelo es mejor que otro?</h2>
          <p style={sub}>Compara el error de <b>LightGBM</b> contra el de la <b>media móvil</b> de 4 semanas, día a día. Si uno erra menos casi siempre, es mejor de verdad; si se reparten los días, puede ser suerte.</p>
        </Paso>
        <Paso n={0}><DiferenciaDiaria a={total.pred.lgbm_directo} b={total.pred.media_movil_4sem} /></Paso>
        <Paso n={1} style={{ marginTop: 'auto' }}>
          <Resultado p={`p = ${pval(mm.p)}`} titulo="Empate: ninguno gana claro" periodo={`backtest ${meta.btPeriodo}`} regla={<>Con <b>p &lt; 0,05</b> la diferencia sería real. Acá se reparten casi mitad y mitad: la media móvil gana {mm.gana2} días y LightGBM {mm.gana1}, pero cuando la media móvil pierde, pierde por más: error total {num(mm.err2)} contra {num(mm.err1)}.<br /><span style={{ color: 'var(--tinta-45)' }}>Empate no es igualdad: 12 semanas no alcanzan para separarlos. Si las pruebas no separan a los modelos, ¿cómo elegimos?</span></>} />
        </Paso>
      </div>
      <div style={{ background: 'var(--tinta-12)' }} />
      <div className="col" style={{ gap: 28 }}>
        <Paso n={2}>
          <div style={ceja}>Ljung-Box</div>
          <h2 style={{ margin: '0 0 6px' }}>¿Quedó algo sin aprender?</h2>
          <p style={sub}>Compara los <b>residuos</b> de <b>ETS</b> y <b>SARIMA</b> (real menos pronóstico) contra <b>ruido puro</b>. Si repiten una forma, como salir de más todos los lunes, hay un patrón que el modelo no aprendió.</p>
        </Paso>
        <Paso n={2}><TirasResiduos /></Paso>
        <Paso n={3} style={{ marginTop: 'auto' }}>
          <Resultado p={`p ≥ ${num(pmin, 2)}`} titulo="ETS y SARIMA, limpios" periodo="residuos del ajuste con datos hasta el 07/11/2026" regla={<>Acá conviene un p <b>grande</b> (&gt; 0,05): los residuos son ruido. No queda nada por modelar.<br /><span style={{ color: 'var(--tinta-45)' }}>Se aplica a ETS y SARIMA porque suponen residuos de ruido; LightGBM no lo supone.</span></>} />
        </Paso>
      </div>
    </div>
  );
}

export const VENTANAS: Diapo = { id: 'ventanas', seccion: S, etapa: 4, titulo: 'Dos ventanas de prueba', pasos: 2, Comp: Ventanas,
  notas: (d) => `Una ventana son ${d.meta.nOrigenes} semanas seguidas que el modelo pronostica sin haberlas visto, reentrenando cada sábado. Usamos dos: ${d.total.robustez.ventanasCortas.anterior} y ${d.total.robustez.ventanasCortas.nueva}; comparten una semana. Con una sola ventana, el ganador puede ser suerte de ese período: si un modelo es bueno, tiene que serlo en las dos.` };
export const ERROR: Diapo = { id: 'error', seccion: S, etapa: 4, titulo: 'Métricas', pasos: 3, Comp: ErrorPron,
  notas: (d) => `El MAE es cuántas viandas le erramos por día, en promedio: cada tramo del diagrama es el error de un día. El WAPE pone todos los errores en fila y los compara con todo lo vendido: es el mismo error como porcentaje, así no depende de K. El MASE divide el error del modelo por el que tuvo copiar la semana pasada en el histórico, con los datos de entrenamiento: menos de 1 es errar menos que eso. Por eso, en el backtest, el propio naive estacional da ${num(d.total.metricas.find((m) => m.id === 'naive_estacional')!.mase, 2)}: el futuro fue más difícil que el histórico. Es la métrica con la que elegimos.` };
export const INTERVALO: Diapo = { id: 'intervalo', seccion: S, etapa: 4, titulo: '¿Cuánto puede fallar? Intervalo 80 %', pasos: 3, Comp: Intervalo,
  notas: (d) => `Un pronóstico es un número, pero para comprar hace falta saber cuánto puede fallar. Miramos un día: el modelo dijo un número. En las últimas semanas, 8 de cada 10 días el real cayó dentro de cierto margen alrededor del pronóstico; técnicamente, los percentiles 10 y 90 del cociente real sobre pronóstico, sin suponer ninguna distribución. Aplicamos ese margen y sale el rango. Si es de 80 %, tiene que contener cerca del 80 % de los días reales: en el backtest cubrió el ${pctFrac(d.total.cobIC.k / d.total.cobIC.n, 0)}, ${d.total.cobIC.k} de ${d.total.cobIC.n} días, algo por debajo del 80 %. Con ${d.total.cobIC.n} días esa diferencia es compatible con el azar. Ese mismo margen es el que usa la compra.` };
export const DM_LJUNG: Diapo = { id: 'dm-ljung', seccion: S, etapa: 4, titulo: 'Diebold-Mariano y Ljung-Box', pasos: 4, Comp: DmLjung,
  notas: () => 'Dos chequeos. Diebold-Mariano: cada punto es un día del backtest; naranja si LightGBM erró menos, gris si erró menos la media móvil. Se reparten casi mitad y mitad, así que p = 0,11: no podemos decir que uno sea mejor. La prueba también pesa por cuánto gana cada uno: cuando LightGBM gana, suele ganar por más, pero no alcanza. Entonces, si las pruebas no separan a los modelos, ¿cómo elegimos? Eso viene ahora. Ljung-Box: mira lo que el modelo no explicó. Si eso repite una forma, por ejemplo todos los lunes, quedó un patrón sin usar. En ETS y SARIMA los p son grandes: los residuos son ruido, no queda nada que modelar. Se aplica a ETS y SARIMA porque esos modelos suponen que lo que sobra es ruido; LightGBM no tiene ese supuesto, y sus residuos dentro de la muestra saldrían limpios de mentira porque los árboles se ajustan mucho a lo que ya vieron.' };
