// Sección "¿Cómo se usa?": el ritual del sábado y hoja de ruta.
import { Fragment, type ReactNode } from 'react';
import * as d3 from 'd3';
import { Icono, Nota, Paso, Periodo, useDatos } from '../components/marca';
import { num, pct } from '../lib/format';
import { COD_MODELO, Cuenta } from './codigo';
import type { Diapo } from './tipos';

const S = 'Cómo se usa';

// ---------------------------------------------------------------- hilo de la sección: una categoría de ejemplo
// Las cuatro diapos siguen el mismo número: carne vacuna en empresas, la semana que viene.
type Plan = ReturnType<typeof useDatos>['plan'];
function ejemplo(plan: Plan, seg = 'empresas') {
  const filas = plan.semana.filter((x) => x.seg === seg);
  const total = d3.sum(filas, (x) => x.pron);
  const f = [...filas].sort((a, b) => b.pron - a.pron)[0];
  return { seg, cat: f.cat, total, part: f.pron / total, pron: f.pron, factor: f.plan / f.pron, compra: f.plan };
}
const factorSeg = (plan: Plan, seg: string) => ejemplo(plan, seg).factor;

// ---------------------------------------------------------------- 23 · la compra, en una cuenta
function ModeloFinal() {
  const { meta, total, mix, plan } = useDatos();
  const ej = ejemplo(plan);
  const lg = total.metricas.find((m) => m.id === 'lgbm_directo')!;
  const cat = mix.unidades.find((x) => x.nivel === 'categoria' && x.id === 'media_4sem')!;
  const factores = [
    { v: num(ej.total), t: 'Pronóstico', s: `Viandas de ${ej.seg} en la semana, con LightGBM.`, m: `MASE ${num(lg.mase, 2)}` },
    { v: pct(ej.part * 100, 1), t: 'Participación', s: `Parte de ${ej.cat} en las últimas 4 semanas.`, m: `MASE por categoría ${num(cat.mase, 2)}` },
    { v: num(ej.factor, 2), t: 'Colchón', s: 'Factor que sale de los errores recientes.', m: `p = ${plan.pElegido}` },
  ];
  // alto = el de las cifras (88 px), así el signo queda centrado con los números
  // el ancho de cada bloque lo fija su cifra (el texto no lo estira), así cada signo queda a igual distancia de las dos cifras
  const TXT = { fontSize: 19, margin: 0, lineHeight: 1.4, width: 0, minWidth: '100%' };
  const op = (c: string) => <span style={{ height: 88, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 64, lineHeight: 1, color: 'var(--tinta-25)' }}>{c}</span>;
  return (
    <div className="col" style={{ justifyContent: 'center', gap: 70, height: '100%' }}>
      <Paso n={0}>
        <p className="pregunta" style={{ margin: 0, maxWidth: 1100 }}>Cada sábado, la compra de cada categoría sale de <b>multiplicar tres números</b>. Por ejemplo, {ej.cat} en {ej.seg}, semana {meta.semanaPlan}:</p>
      </Paso>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, auto)', justifyContent: 'space-between', alignItems: 'start' }}>
        {factores.map((f, i) => (
          <Fragment key={f.t}>
            {i > 0 && <Paso n={i + 1}>{op('×')}</Paso>}
            <Paso n={i + 1} className="col" style={{ gap: 6 }}>
              <span className="cifra" style={{ fontSize: 88, lineHeight: 1 }}>{f.v}</span>
              <h3 style={{ fontSize: 28, margin: '10px 0 0' }}>{f.t}</h3>
              <p style={TXT}>{f.s}</p>
              <span style={{ ...TXT, fontSize: 16, color: 'var(--tinta-70)', marginTop: 6 }}>{f.m}</span>
            </Paso>
          </Fragment>
        ))}
        <Paso n={4}>{op('=')}</Paso>
        <Paso n={4} className="col" style={{ gap: 6 }}>
          <span className="cifra" style={{ fontSize: 88, lineHeight: 1, color: 'var(--ambar)' }}>{num(ej.compra)}</span>
          <h3 style={{ fontSize: 28, margin: '10px 0 0', color: 'var(--ambar)' }}>Compra</h3>
          <p style={TXT}>Porciones para entregar de lunes a sábado.</p>
        </Paso>
      </div>
      <Paso n={4}>
        <Periodo>Porciones × K · métricas del backtest {meta.btPeriodo} · el clima y Meta quedaron afuera</Periodo>
      </Paso>
    </div>
  );
}

// ---------------------------------------------------------------- 25 · el tercer factor: el colchón
function CurvaCosto() {
  const { plan } = useDatos();
  const c = plan.curva.filter((x) => x.metodo === 'lgbm');
  const W = 640, H = 330, m = { t: 36, r: 16, b: 40, l: 16 };
  const x = d3.scaleLinear().domain(d3.extent(c, (d) => d.p) as [number, number]).range([m.l, W - m.r]);
  const y = d3.scaleLinear().domain([d3.min(c, (d) => d.costo)! * 0.85, d3.max(c, (d) => d.costo)!]).range([H - m.b, m.t]);
  const linea = d3.line<(typeof c)[number]>().x((d) => x(d.p)).y((d) => y(d.costo)).curve(d3.curveMonotoneX)(c)!;
  const e = c.find((d) => d.p === plan.pElegido)!;
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Costo por vianda según p">
      <line x1={m.l} x2={W - m.r} y1={H - m.b} y2={H - m.b} stroke="var(--tinta-25)" />
      {c.filter((d) => d.p % 10 === 0).map((d) => <text key={d.p} x={x(d.p)} y={H - m.b + 24} textAnchor="middle" fontSize={15} fill="var(--tinta-70)">{d.p}</text>)}
      <path d={linea} fill="none" stroke="var(--tinta)" strokeWidth={3} />
      <circle cx={x(e.p)} cy={y(e.costo)} r={9} fill="var(--ambar)" stroke="var(--blanco)" strokeWidth={3} />
      <text x={x(e.p)} y={y(e.costo) - 22} textAnchor="middle" fontSize={17} fontWeight={700} fill="var(--ambar)">p = {e.p} · {num(e.costo, 1)} UYU</text>
      <text x={m.l} y={m.t - 16} fontSize={15} fill="var(--tinta-70)">costo por vianda según p · poco colchón falta, mucho sobra</text>
    </svg>
  );
}

function Colchon() {
  const { plan, meta } = useDatos();
  const pE = plan.pElegido;
  const ej = ejemplo(plan);
  const col = (n: number, kicker: string, titulo: string, hijos: ReactNode) => (
    <Paso n={n} className="col" style={{ gap: 14 }}>
      <span style={{ fontSize: 16, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ambar)', fontWeight: 700 }}>{kicker}</span>
      <h3 style={{ fontSize: 32, margin: 0 }}>{titulo}</h3>
      {hijos}
    </Paso>
  );
  return (
    <div className="col" style={{ gap: 40, height: '100%' }}>
      <Paso n={0}><Cuenta activos={[2]} /></Paso>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1px 1fr', gap: 56, alignItems: 'start' }}>
        {col(1, 'Backtest · últimas 12 semanas', `Elegir p`, <>
          <p style={{ fontSize: 19, margin: 0, lineHeight: 1.45 }}>En las semanas pasadas se prueba cada p: compra = pronóstico × percentil p de <i>real ÷ pronóstico</i> de las {meta.semanasIntervalo} semanas previas. Cada vianda que sobra cuesta ${meta.costos.sobrante}; cada una que falta, ${meta.costos.faltante}.</p>
          <CurvaCosto />
        </>)}
        <Paso n={2}><div style={{ width: 1, height: 480, background: 'var(--tinta-12)' }} /></Paso>
        {col(2, 'La semana que viene', `Aplicar p = ${pE}`, <>
          <p style={{ fontSize: 19, margin: 0, lineHeight: 1.45 }}>El factor es el percentil {pE} de <i>real ÷ pronóstico</i> en las últimas {meta.semanasIntervalo} semanas, con las {meta.nCategorias} categorías del segmento juntas.</p>
          <div style={{ display: 'flex', gap: 56, marginTop: 18 }}>
            {['empresas', 'particulares'].map((s) => (
              <div key={s}>
                <span className="cifra" style={{ fontSize: 80, lineHeight: 1 }}>×{num(factorSeg(plan, s), 2)}</span>
                <div style={{ fontSize: 18, color: 'var(--tinta-70)', marginTop: 6 }}>{s}, esta semana</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 19, margin: '18px 0 0', lineHeight: 1.45 }}><b>Cada sábado se rehacen las dos cosas.</b> p cambia poco, porque 11 de las 12 semanas se repiten (hasta el 18/11 era {plan.pAntes}); el factor sí cambia con los errores nuevos. En {ej.cat}: {num(ej.pron)} × {num(ej.factor, 2)} ≈ {num(ej.compra)}.</p>
        </>)}
      </div>
    </div>
  );
}

/** Borde de ticket: dientes de sierra arriba y abajo (clip-path; la sombra va en el contenedor). */
const DIENTES = (() => {
  const n = 32, h = 10, x = (i: number) => `${((i / n) * 100).toFixed(3)}%`;
  const arriba = Array.from({ length: n + 1 }, (_, i) => `${x(i)} ${i % 2 ? 0 : h}px`);
  const abajo = Array.from({ length: n + 1 }, (_, i) => `${x(n - i)} calc(100% - ${(n - i) % 2 ? 0 : h}px)`);
  return `polygon(${[...arriba, ...abajo].join(', ')})`;
})();

// ---------------------------------------------------------------- 26 · cada sábado, en la práctica
function Sabado() {
  const { plan, meta } = useDatos();
  const ej = ejemplo(plan);
  const filas = meta.categorias.map((c) => ({
    cat: c,
    p: plan.semana.find((x) => x.seg === 'particulares' && x.cat === c)?.plan ?? 0,
    e: plan.semana.find((x) => x.seg === 'empresas' && x.cat === c)?.plan ?? 0,
  })).sort((a, b) => b.p + b.e - (a.p + a.e));
  const total = d3.sum(filas, (f) => f.p + f.e);
  const pasos = [
    { ic: 'archivo', t: 'Bajar el export', s: <>Los pedidos de la semana van a <code>data/raw_private/</code>.</> },
    { ic: 'terminal', t: 'Correr un comando', s: <><code>python main.py all</code> reentrena y arma la compra.</> },
    { ic: 'carrito', t: 'Comprar', s: <>Una cantidad por segmento y categoría. El sábado siguiente, otra vez.</> },
  ];
  const celda = { width: 60, textAlign: 'right' as const };
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 520px', gap: 80, height: '100%', alignItems: 'center' }}>
      <div className="col" style={{ gap: 40 }}>
        {pasos.map((p, i) => (
          <Paso key={p.t} n={i} x={-20}>
            <div style={{ display: 'grid', gridTemplateColumns: '60px 1fr', gap: 24, alignItems: 'center' }}>
              <div style={{ width: 60, height: 60, borderRadius: 30, background: i === 2 ? 'var(--ambar)' : 'var(--crema-osc)', display: 'grid', placeItems: 'center' }}>
                <Icono n={p.ic} tam={28} color={i === 2 ? 'var(--blanco)' : 'var(--tinta)'} />
              </div>
              <div>
                <h3 style={{ fontSize: 30, margin: '0 0 4px' }}>{p.t}</h3>
                <p style={{ fontSize: 20, margin: 0 }}>{p.s}</p>
              </div>
            </div>
          </Paso>
        ))}
      </div>
      <Paso n={2} style={{ display: 'flex', justifyContent: 'center', position: 'relative' }}>
        <div className="comanda-sombra">
        <div className="comanda" style={{ clipPath: DIENTES }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <h4>Compra de la semana</h4>
            <span style={{ fontSize: 15, color: 'var(--tinta-70)' }}>p = {plan.pElegido}</span>
          </div>
          <div style={{ fontSize: 16, color: 'var(--tinta-70)', marginTop: 4 }}>{meta.semanaPlan} · porciones × K</div>
          <div className="linea" />
          <div className="fila" style={{ fontSize: 14, color: 'var(--tinta-70)' }}><span>categoría</span><span style={{ display: 'flex', gap: 18 }}><span style={celda}>part.</span><span style={celda}>emp.</span></span></div>
          {filas.map((f) => (
            <div className="fila" key={f.cat}><span>{f.cat}</span><span style={{ display: 'flex', gap: 18 }}><span style={celda}>{num(f.p)}</span>
              <span style={{ ...celda, ...(f.cat === ej.cat ? { background: 'var(--ambar)', color: 'var(--blanco)', borderRadius: 4, fontWeight: 700, padding: '0 4px', margin: '0 -4px' } : {}) }}>{num(f.e)}</span></span></div>
          ))}
          <div className="linea" />
          <div className="fila"><span style={{ fontWeight: 700 }}>Total</span><b>{num(total)}</b></div>
        </div>
        </div>
        <Nota style={{ right: -20, top: -30, transform: 'rotate(6deg)' }}>el {num(ej.compra)} de la cuenta</Nota>
      </Paso>
    </div>
  );
}

// ---------------------------------------------------------------- hoja de ruta: tres ideas que mejorarían el pronóstico
function HojaDeRuta() {
  const ideas = [
    { ic: 'reloj', t: 'Pedidos ya confirmados', s: 'Con la hora de cada pedido, usar lo que ya entró en la semana para corregir el pronóstico.' },
    { ic: 'calendario', t: 'Más historia', s: 'Con más años de datos, el modelo puede aprender el ciclo anual: verano, vacaciones y fin de año.' },
    { ic: 'megafono', t: 'Medir Meta', s: 'Alternar semanas con más y menos pauta para saber si mueve las ventas.' },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 56, height: '100%', alignContent: 'center' }}>
      {ideas.map((c, i) => (
        <Paso key={c.t} n={i} style={{ borderTop: '4px solid var(--ambar)', paddingTop: 28 }}>
          <Icono n={c.ic} tam={44} color="var(--ambar)" />
          <h2 style={{ fontSize: 46, margin: '18px 0 16px' }}>{c.t}</h2>
          <p style={{ fontSize: 25, margin: 0 }}>{c.s}</p>
        </Paso>
      ))}
    </div>
  );
}

export const USO: Diapo[] = [
  { id: 'modelo-final', seccion: S, titulo: 'La compra, en una cuenta', pasos: 5, Comp: ModeloFinal,
    notas: (d) => `Variables de LightGBM, por si preguntan: ${d.meta.variablesModelo}. ` + 'Todo el modelo final cabe en una cuenta. Sigamos un ejemplo: carne vacuna en empresas para la semana que viene. LightGBM pronostica el total de empresas en la semana. Ese total se reparte con la participación que tuvo carne vacuna en las últimas cuatro semanas. Y se multiplica por el colchón, un factor que sale de los errores recientes. Las próximas dos diapos abren estos factores: primero el código de los dos primeros, después el colchón.' },
  COD_MODELO,
  { id: 'colchon', seccion: S, titulo: 'El tercer factor: el colchón', pasos: 3, Comp: Colchon,
    notas: (d) => `El colchón tiene dos partes. Primero, en el backtest de las últimas doce semanas, elegimos qué percentil usar: para cada p armamos la compra con los errores de las doce semanas previas, la comparamos con lo que realmente se vendió y medimos el costo de lo que sobra y lo que falta. La curva tiene forma de U: con poco colchón falta, con mucho sobra. El mínimo está en p = ${d.plan.pElegido}. Después calculamos el factor como el percentil ${d.plan.pElegido} de los errores de las últimas doce semanas y lo aplicamos al pronóstico. Las dos cosas se rehacen cada sábado: p cambia poco, porque la ventana se corre una sola semana (hasta el 18 de noviembre era ${d.plan.pAntes}); el factor sí cambia semana a semana.` },
  { id: 'sabado', seccion: S, titulo: 'Cada sábado, en la práctica', pasos: 3, Comp: Sabado,
    notas: () => 'En la práctica son tres pasos: bajar el export, correr un comando y comprar. La comanda es la compra real para la semana que viene; el número resaltado es el mismo de la cuenta del principio.' },
  { id: 'hoja-de-ruta', seccion: S, titulo: 'Qué mejoraría los resultados', pasos: 3, Comp: HojaDeRuta,
    notas: () => 'Tres ideas que mejorarían el pronóstico. Una: con la hora de cada pedido, usar lo que ya se confirmó en la semana. Dos: con más años de datos, el modelo puede aprender el ciclo anual, como el verano, las vacaciones y fin de año; hoy hay apenas un año y medio. Tres: alternar semanas con más y menos pauta en Meta para medir si realmente mueve las ventas.' },
];
