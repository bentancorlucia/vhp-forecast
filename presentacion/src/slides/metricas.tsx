// Método · cómo medimos (etapa 4, evaluate.py): fórmula, cómo se lee y un ejemplo real.
import { Paso, Periodo, useDatos } from '../components/marca';
import { Backtest } from '../charts/graficos';
import { fechaCorta, fechaLarga, num, pctFrac, pval } from '../lib/format';
import type { Diapo } from './tipos';
import type { ReactNode } from 'react';

const S = 'Método';

function ErrorPron() {
  const { total, meta } = useDatos();
  const lg = total.metricas.find((m) => m.id === 'lgbm_directo')!;
  const ne = total.metricas.find((m) => m.id === 'naive_estacional')!;
  const comp = ['lgbm_directo', 'sarima', 'ets', 'mlp', 'naive_estacional'].map((id) => total.metricas.find((m) => m.id === id)!);
  const items = [
    { n: 0, nombre: 'MAE', sigla: 'Mean Absolute Error', a: lg.mae, b: ne.mae, k: 'mae' as const, f: (x: number) => num(x, 0), unidad: 'viandas', mide: <>Cuántas viandas le erramos <b>por día</b>.</> },
    { n: 1, nombre: 'WAPE', sigla: 'Weighted Absolute Percentage Error', a: lg.wape, b: ne.wape, k: 'wape' as const, f: (x: number) => `${num(x * 100, 1)} %`, unidad: '', mide: <>Ese error como <b>% de lo vendido</b>.</> },
    { n: 2, nombre: 'MASE', sigla: 'Mean Absolute Scaled Error', a: lg.mase, b: ne.mase, k: 'mase' as const, f: (x: number) => num(x, 2), unidad: '', mide: <>El error frente a <b>copiar la semana pasada</b>. Con esta elegimos.</>, hero: true },
  ];
  return (
    <div className="col" style={{ height: '100%', justifyContent: 'center', gap: 26 }}>
      <div className="grid3" style={{ gap: 32, alignItems: 'stretch' }}>
        {items.map((m) => {
          const tinta = m.hero ? 'var(--blanco)' : 'var(--tinta)';
          const suave = m.hero ? 'rgba(255,255,255,.72)' : 'var(--tinta-45)';
          const barra = (v: number, quien: string, fuerte: boolean) => (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 12, fontSize: 14, color: fuerte ? tinta : suave }}>
              <div>
                <div style={{ marginBottom: 3 }}>{quien}</div>
                <div style={{ height: 6, borderRadius: 6, width: `${(v / m.b) * 100}%`, background: fuerte ? (m.hero ? 'var(--blanco)' : 'var(--ambar)') : (m.hero ? 'rgba(255,255,255,.35)' : 'var(--tinta-12)') }} />
              </div>
              <b style={{ fontWeight: fuerte ? 700 : 500, alignSelf: 'end' }}>{m.f(v)}</b>
            </div>
          );
          return (
            <Paso n={m.n} key={m.nombre} style={{ height: '100%' }}>
              <div style={{ height: '100%', boxSizing: 'border-box', borderRadius: 28, padding: '34px 36px 32px', display: 'flex', flexDirection: 'column', color: tinta, background: m.hero ? 'var(--ambar)' : 'var(--blanco)', boxShadow: 'var(--sombra)' }}>
                <div style={{ fontSize: 16, fontWeight: 600, letterSpacing: '.18em', color: suave }}>{m.nombre}</div>
                <div style={{ fontSize: 14, marginTop: 4, color: suave }}>{m.sigla}</div>
                <div className="cifra" style={{ fontSize: 100, margin: '18px 0 6px' }}>{m.f(m.a)}</div>
                <div style={{ fontSize: 15, color: suave, minHeight: 18 }}>{m.unidad}</div>
                <p style={{ margin: '14px 0 26px', fontSize: 22, lineHeight: 1.35, color: tinta }}>{m.mide}</p>
                <div style={{ marginTop: 'auto', display: 'grid', gap: 9 }}>
                  {comp.map((c) => <div key={c.id}>{barra(c[m.k], c.nombre, c.id === lg.id)}</div>)}
                </div>
              </div>
            </Paso>
          );
        })}
      </div>
      <Paso n={2}><Periodo>todo el backtest, {meta.btPeriodo} · menor es mejor</Periodo></Paso>
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
    <svg viewBox={`0 0 ${W} 300`} width="100%" style={{ display: 'block', overflow: 'visible' }} role="img" aria-label="Residuos con patrón semanal frente a residuos sin patrón">
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
          <Resultado p={`p = ${pval(mm.p)}`} titulo="Empate: ninguno gana claro" periodo={`backtest ${meta.btPeriodo}`} regla={<>Con <b>p &lt; 0,05</b> la diferencia sería real. Acá se reparten casi mitad y mitad: la media móvil gana {mm.gana2} días y LightGBM {mm.gana1}, pero cuando pierde, pierde por más.<br /><span style={{ color: 'var(--tinta-45)' }}>Empate no es igualdad: 12 semanas no alcanzan para separarlos. Elegimos LightGBM por tener el menor error total.</span></>} />
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

export const ERROR: Diapo = { id: 'error', seccion: S, etapa: 4, titulo: 'Métricas', pasos: 3, Comp: ErrorPron,
  notas: (d) => `El MAE es cuántas viandas le erramos por día; el WAPE, el mismo error como porcentaje de lo vendido, así no depende de K. El MASE divide por el error de copiar la semana pasada: es la métrica con la que elegimos. LightGBM queda en ${num(d.total.metricas.find((m) => m.id === 'lgbm_directo')!.mase, 3)} contra ${num(d.total.metricas.find((m) => m.id === 'naive_estacional')!.mase, 3)} del naive estacional.` };
export const INTERVALO: Diapo = { id: 'intervalo', seccion: S, etapa: 4, titulo: '¿Cuánto puede fallar? Intervalo 80 %', pasos: 3, Comp: Intervalo,
  notas: (d) => `Un pronóstico es un número, pero para comprar hace falta saber cuánto puede fallar. Miramos un día: el modelo dijo un número. En las últimas semanas, 8 de cada 10 días el real cayó dentro de cierto margen alrededor del pronóstico; técnicamente, los percentiles 10 y 90 del cociente real sobre pronóstico, sin suponer ninguna distribución. Aplicamos ese margen y sale el rango. Si es de 80 %, tiene que contener cerca del 80 % de los días reales: en el backtest cubrió el ${pctFrac(d.total.cobIC.k / d.total.cobIC.n, 0)}, ${d.total.cobIC.k} de ${d.total.cobIC.n} días, algo por debajo del 80 %. Con ${d.total.cobIC.n} días esa diferencia es compatible con el azar. Ese mismo margen es el que usa la compra.` };
export const DM_LJUNG: Diapo = { id: 'dm-ljung', seccion: S, etapa: 4, titulo: 'Diebold-Mariano y Ljung-Box', pasos: 4, Comp: DmLjung,
  notas: () => 'Dos chequeos. Diebold-Mariano: cada punto es un día del backtest; naranja si LightGBM erró menos, gris si erró menos la media móvil. Se reparten casi mitad y mitad, así que p = 0,11: no podemos decir que uno sea mejor. La prueba también pesa por cuánto gana cada uno: cuando LightGBM gana, suele ganar por más, pero no alcanza. Ljung-Box: mira lo que el modelo no explicó. Si eso repite una forma, por ejemplo todos los lunes, quedó un patrón sin usar. En ETS y SARIMA los p son grandes: los residuos son ruido, no queda nada que modelar. Se aplica a ETS y SARIMA porque esos modelos suponen que lo que sobra es ruido; LightGBM no tiene ese supuesto, y sus residuos dentro de la muestra saldrían limpios de mentira porque los árboles se ajustan mucho a lo que ya vieron.' };
