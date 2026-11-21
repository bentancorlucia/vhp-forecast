// Gráficos de la presentación. Todos los valores vienen de presentacion.json.
import { useCallback, useMemo } from 'react';
import * as d3 from 'd3';
import { motion } from 'framer-motion';
import { useAnimar, useDatos, usePaso, useVisto } from '../components/marca';
import { diaSemana, fechaCorta, fechaLarga, mesAnio, num, pct, pctFrac, pval, signed, toDate } from '../lib/format';
import { C, GridY, Svg, Tip, masCercano, useHover } from './base';
import type { Evento, Pred } from '../lib/tipos';

const MPath = motion.path as unknown as React.FC<Record<string, unknown>>;

function Trazo({ d, stroke, w = 2.5, dash, delay = 0 }: { d: string; stroke: string; w?: number; dash?: string; delay?: number }) {
  const animar = useAnimar();
  return (
    <MPath d={d} fill="none" stroke={stroke} strokeWidth={w} strokeDasharray={dash} strokeLinejoin="round" strokeLinecap="round"
      initial={animar ? { pathLength: 0 } : false} animate={{ pathLength: 1 }} transition={{ duration: animar ? 1.2 : 0, delay: animar ? delay : 0, ease: 'easeInOut' }} />
  );
}

// ---------------------------------------------------------------- media móvil centrada simple (k días)
function mediaMovil(v: number[], k: number) {
  return v.map((_, i) => {
    const a = Math.max(0, i - Math.floor(k / 2)), b = Math.min(v.length, a + k);
    let s = 0;
    for (let j = a; j < b; j++) s += v[j];
    return s / (b - a);
  });
}

/** Igual que mediaMovil pero con huecos: null donde la serie no tiene dato. */
function mediaMovilN(v: (number | null)[], k: number): (number | null)[] {
  return v.map((x, i) => {
    if (x == null) return null;
    const a = Math.max(0, i - Math.floor(k / 2)), b = Math.min(v.length, a + k);
    const w = v.slice(a, b).filter((z): z is number => z != null);
    return w.reduce((s, z) => s + z, 0) / w.length;
  });
}

// ---------------------------------------------------------------- serie diaria por segmento: diario tenue + media semanal fuerte
export function SerieDiaria({ w, h }: { w: number; h: number; resaltar?: string }) {
  const { serie, meta } = useDatos();
  const m = { t: 20, r: 130, b: 34, l: 60 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const fechas = useMemo(() => serie.map((s) => toDate(s.f)), [serie]);
  const mmP = useMemo(() => mediaMovilN(serie.map((s) => s.p), meta.periodo), [serie, meta.periodo]);
  const mmE = useMemo(() => mediaMovilN(serie.map((s) => s.e), meta.periodo), [serie, meta.periodo]);
  const x = d3.scaleTime().domain(d3.extent(fechas) as [Date, Date]).range([0, iw]);
  const y = d3.scaleLinear().domain([0, d3.max(serie, (s) => Math.max(s.p, s.e ?? 0))! * 1.05]).range([ih, 0]).nice();
  const lin = (v: (number | null)[]) => d3.line<number | null>().defined((d) => d != null).x((_, i) => x(fechas[i])).y((d) => y(d ?? 0)).curve(d3.curveMonotoneX)(v)!;
  const nE = serie.map((s) => s.e != null).lastIndexOf(true);
  const xs = useMemo(() => fechas.map((f) => m.l + x(f)), [fechas, x, m.l]);
  const buscar = useCallback((px: number) => masCercano(xs, px), [xs]);
  const { ref, h: hi, onMove, onLeave } = useHover(buscar);
  const verano = serie.filter((s) => s.ver);
  const n = serie.length - 1;
  return (
    <Svg w={w} h={h} label="Viandas por día y segmento" svgRef={ref} onMove={onMove} onLeave={onLeave}>
      <g transform={`translate(${m.l},${m.t})`}>
        {verano.length > 0 && <rect x={x(toDate(verano[0].f))} width={x(toDate(verano[verano.length - 1].f)) - x(toDate(verano[0].f))} y={0} height={ih} fill={C.banda} rx={6} />}
        <GridY ticks={y.ticks(4)} y={y} x1={iw} fmt={(v) => num(v)} />
        <g className="eje">{x.ticks(d3.timeMonth.every(3)!).map((t) => <text key={+t} x={x(t)} y={ih + 26} textAnchor="middle">{mesAnio(t)}</text>)}</g>
        <path d={lin(serie.map((s) => s.e))} fill="none" stroke={C.t12} strokeWidth={1} />
        <path d={lin(serie.map((s) => s.p))} fill="none" stroke="rgba(234,154,2,0.22)" strokeWidth={1} />
        <Trazo d={lin(mmE)} stroke={C.t70} w={3} />
        <Trazo d={lin(mmP)} stroke={C.ambar} w={4} delay={0.25} />
        <text className="etq-b" x={iw + 12} y={y(mmP[n]!)} dy="0.32em" fill={C.ambar} style={{ fill: 'var(--ambar)' }}>particulares</text>
        <text className="etq-b" x={x(fechas[nE]) + 12} y={Math.max(y(mmE[nE]!), y(mmP[n]!) + 26)} dy="0.32em" style={{ fill: 'var(--tinta-70)' }}>empresas</text>
        {verano.length > 0 && <text x={(x(toDate(verano[0].f)) + x(toDate(verano[verano.length - 1].f))) / 2} y={22} textAnchor="middle" className="etq" style={{ fontSize: 12 }}>verano</text>}
      </g>
      {hi != null && (() => {
        const s = serie[hi];
        const px = xs[hi];
        return (
          <g>
            <line x1={px} x2={px} y1={m.t} y2={m.t + ih} stroke={C.t45} strokeDasharray="3 3" />
            <circle cx={px} cy={m.t + y(s.p)} r={5} fill={C.ambar} stroke={C.blanco} strokeWidth={2} />
            {s.e != null && <circle cx={px} cy={m.t + y(s.e)} r={5} fill={C.tinta} stroke={C.blanco} strokeWidth={2} />}
            <Tip x={px} y={m.t + 60} limite={w} lineas={[`${diaSemana(s.f)} ${fechaLarga(s.f)}`, `Particulares: ${num(s.p)}`, `Empresas: ${s.e == null ? 'sin dato' : num(s.e)}`, s.fer ? 'feriado laborable' : s.ver ? 'verano' : '']} />
          </g>
        );
      })()}
    </Svg>
  );
}

// ---------------------------------------------------------------- perfil semanal: dos líneas que se cruzan
export function PerfilSemanal({ w, h }: { w: number; h: number }) {
  const { eda } = useDatos();
  const ds = eda.diaSemana;
  const m = { t: 30, r: 150, b: 46, l: 56 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const x = d3.scalePoint<string>().domain(ds.map((d) => d.dia)).range([0, iw]).padding(0.25);
  const y = d3.scaleLinear().domain([0, d3.max(ds, (d) => Math.max(d.particulares, d.empresas))! * 1.12]).range([ih, 0]);
  const animar = useAnimar();
  const segs = [
    { k: 'empresas' as const, col: C.t70, nombre: 'empresas' },
    { k: 'particulares' as const, col: C.ambar, nombre: 'particulares' },
  ];
  const ult = ds[ds.length - 1];
  return (
    <Svg w={w} h={h} label="Perfil semanal por segmento">
      <g transform={`translate(${m.l},${m.t})`}>
        <GridY ticks={[0, 0.5, 1, 1.5]} y={y} x1={iw} fmt={(v) => num(v, 1)} />
        <line x1={0} x2={iw} y1={y(1)} y2={y(1)} stroke={C.t45} strokeDasharray="6 5" />
        <text className="etq" x={iw + 8} y={y(1)} dy="0.32em" fontSize={14}>media = 1</text>
        {ds.map((d) => <text key={d.dia} className="etq-b" x={x(d.dia)} y={ih + 32} textAnchor="middle">{d.dia}</text>)}
        {segs.map((s, j) => {
          const path = d3.line<(typeof ds)[number]>().x((d) => x(d.dia)!).y((d) => y(d[s.k])).curve(d3.curveMonotoneX)(ds)!;
          return (
            <g key={s.k}>
              <Trazo d={path} stroke={s.col} w={s.k === 'particulares' ? 5 : 4} delay={j * 0.3} />
              {ds.map((d, i) => (
                <motion.g key={d.dia} initial={animar ? { opacity: 0, scale: 0 } : false} animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: animar ? 0.3 + j * 0.3 + i * 0.09 : 0, duration: animar ? 0.3 : 0 }} style={{ transformOrigin: `${x(d.dia)}px ${y(d[s.k])}px` }}>
                  <circle cx={x(d.dia)} cy={y(d[s.k])} r={9} fill={C.blanco} stroke={s.col} strokeWidth={4} />
                  <text className="etq" x={x(d.dia)} y={y(d[s.k]) + (s.k === 'particulares' ? -18 : 28)} textAnchor="middle" fontSize={15}>{num(d[s.k], 2)}</text>
                </motion.g>
              ))}
              <text className="etq-fr" x={x(ult.dia)! + 22} y={y(ult[s.k])} dy="0.32em" fontSize={24} style={{ fill: s.col }}>{s.nombre}</text>
            </g>
          );
        })}
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- línea de la demanda (portada y cierre)
export function LineaDemanda({ w, h, grosor = 5 }: { w: number; h: number; grosor?: number }) {
  const { serie, meta } = useDatos();
  const tot = useMemo(() => mediaMovil(serie.filter((s) => s.e != null).map((s) => s.p + s.e!), meta.periodo), [serie, meta.periodo]);
  const x = d3.scaleLinear().domain([0, tot.length - 1]).range([0, w]);
  const y = d3.scaleLinear().domain([0, d3.max(tot)!]).range([h, 0]);
  const d = d3.line<number>().x((_, i) => x(i)).y((v) => y(v)).curve(d3.curveBasis)(tot)!;
  const area = d3.area<number>().x((_, i) => x(i)).y0(h).y1((v) => y(v)).curve(d3.curveBasis)(tot)!;
  const animar = useAnimar();
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden style={{ overflow: 'visible', display: 'block' }}>
      <motion.path d={area} fill={C.banda} initial={animar ? { opacity: 0 } : false} animate={{ opacity: 1 }} transition={{ duration: animar ? 1.2 : 0, delay: animar ? 1.4 : 0 }} />
      <MPath d={d} fill="none" stroke={C.ambar} strokeWidth={grosor} strokeLinecap="round"
        initial={animar ? { pathLength: 0 } : false} animate={{ pathLength: 1 }} transition={{ duration: animar ? 2.4 : 0, ease: [0.65, 0, 0.35, 1], delay: animar ? 0.3 : 0 }} />
    </svg>
  );
}

// ---------------------------------------------------------------- ranking de modelos
export function Ranking({ w, h }: { w: number; h: number }) {
  const { total } = useDatos();
  const ms = total.metricas;
  const m = { t: 34, r: 330, b: 40, l: 210 };
  const cW = 40, cC = 160;
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const y = d3.scaleBand().domain(ms.map((d) => d.id)).range([0, ih]).padding(0.28);
  const x = d3.scaleLinear().domain([0, Math.min(d3.max(ms, (d) => d.mase)!, 2.2)]).range([0, iw]);
  const animar = useAnimar();
  return (
    <Svg w={w} h={h} label="Ranking de modelos por MASE">
      <g transform={`translate(${m.l},${m.t})`}>
        <text className="etq" x={0} y={-12} fontWeight={700}>MASE</text>
        <text className="etq" x={iw + cW} y={-12} fontWeight={700}>WAPE</text>
        <text className="etq" x={iw + cC} y={-12} fontWeight={700}>Cobertura 80 %</text>
        {ms.map((d, i) => {
          const gana = i === 0;
          const largo = Math.min(x(d.mase), iw);
          return (
            <g key={d.id} transform={`translate(0,${y(d.id)})`}>
              <text className={gana ? 'etq-b' : 'etq'} x={-12} y={y.bandwidth() / 2} dy="0.32em" textAnchor="end">{d.nombre}</text>
              <motion.rect height={y.bandwidth()} rx={6} fill={gana ? C.ambar : C.t25}
                initial={animar ? { width: 0 } : false} animate={{ width: largo }} transition={{ duration: animar ? 0.6 : 0, delay: animar ? i * 0.07 : 0 }} />
              {d.mase > x.domain()[1]
                ? <text className="etq-b" x={largo - 10} y={y.bandwidth() / 2} dy="0.32em" textAnchor="end">{num(d.mase, 3)} →</text>
                : <text className={gana ? 'etq-b' : 'etq'} x={largo + 8} y={y.bandwidth() / 2} dy="0.32em">{num(d.mase, 3)}</text>}
              <text className="etq" x={iw + cW} y={y.bandwidth() / 2} dy="0.32em">{pctFrac(d.wape, 1)}</text>
              <text className="etq" x={iw + cC} y={y.bandwidth() / 2} dy="0.32em">{pctFrac(d.cob, 0)}</text>
            </g>
          );
        })}
        <line x1={x(1)} x2={x(1)} y1={-4} y2={ih} stroke={C.tinta} strokeDasharray="4 5" />
        <text className="etq" x={x(1)} y={ih + 26} textAnchor="middle" fontSize={15}>MASE = 1</text>
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- ranking agrupado por Diebold-Mariano
export function RankingEmpate({ w, h }: { w: number; h: number }) {
  const { total } = useDatos();
  const ms = total.metricas;
  const ref = ms[0];
  const pDm = new Map(total.dm.filter((d) => d.m1 === ref.id).map((d) => [d.m2, d.p]));
  const empata = ms.filter((d, i) => i === 0 || (pDm.get(d.id) ?? 0) >= 0.05);
  const pEmp = empata.slice(1).map((d) => pDm.get(d.id)!);
  const m = { t: 62, r: 0, b: 40, l: 190 };
  const ih = h - m.t - m.b, B = 340, bx = B + 86;
  const y = d3.scaleBand().domain(ms.map((d) => d.id)).range([0, ih]).padding(0.32);
  const x = d3.scaleLinear().domain([0, 1.25]).range([0, B]);
  const animar = useAnimar();
  const y0 = y(empata[0].id)! - 12, y1 = y(empata[empata.length - 1].id)! + y.bandwidth() + 12;
  return (
    <Svg w={w} h={h} label="Ranking de modelos por MASE, agrupado por Diebold-Mariano">
      <g transform={`translate(${m.l},${m.t})`}>
        <rect x={-m.l + 4} y={y0} width={w - 8} height={y1 - y0} rx={14} fill={C.banda} />
        <text className="etq" x={0} y={-16} fontWeight={700}>MASE</text>
        <text className="etq-b" x={bx - 12} y={-38} fontSize={17}>¿Mejor de verdad?</text>
        <text className="etq" x={bx - 12} y={-16} fontSize={14} fill={C.t70}>test de Diebold-Mariano</text>
        <line x1={x(1)} x2={x(1)} y1={-4} y2={ih + 4} stroke={C.t45} strokeDasharray="4 5" />
        <text className="etq" x={x(1)} y={ih + 28} textAnchor="middle" fontSize={15} fill={C.t70}>MASE = 1</text>
        {ms.map((d, i) => {
          const gana = i === 0;
          const largo = Math.min(x(d.mase), B);
          const cy = y.bandwidth() / 2;
          const p = pDm.get(d.id);
          return (
            <g key={d.id} transform={`translate(0,${y(d.id)})`}>
              <text className={gana ? 'etq-b' : 'etq'} x={-16} y={cy} dy="0.32em" textAnchor="end">{d.nombre}</text>
              <motion.rect height={y.bandwidth()} rx={6} fill={gana ? C.ambar : C.t25}
                initial={animar ? { width: 0 } : false} animate={{ width: largo }} transition={{ duration: animar ? 0.6 : 0, delay: animar ? i * 0.07 : 0 }} />
              {d.mase > x.domain()[1]
                ? <text className="etq-b" x={largo - 12} y={cy} dy="0.32em" textAnchor="end">{num(d.mase, 3)} →</text>
                : <text className={gana ? 'etq-b' : 'etq'} x={largo + 10} y={cy} dy="0.32em">{num(d.mase, 3)}</text>}
              {p !== undefined && p < 0.05 && <text className="etq" x={bx + 14} y={cy} dy="0.32em" fontSize={15}><tspan fontWeight={700}>sí, es mejor</tspan><tspan fill={C.t70}> · p = {pval(p)}</tspan></text>}
            </g>
          );
        })}
        <path d={`M${bx - 10},${y0 + 10} H${bx} V${y1 - 10} H${bx - 10}`} fill="none" stroke={C.ambar} strokeWidth={2.5} />
        <g transform={`translate(${bx + 14},${(y0 + y1) / 2})`}>
          <text className="etq-fr" y={-22} fontSize={30} style={{ fill: 'var(--ambar)' }}>no se sabe</text>
          <text className="etq" y={8} fontSize={15}>la diferencia</text>
          <text className="etq" y={28} fontSize={15}>puede ser azar</text>
          <text className="etq" y={52} fontSize={14} fill={C.t70}>p ≥ {pval(Math.min(...pEmp))}</text>
        </g>
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- Diebold-Mariano: p-valores contra LightGBM
export function DMBarras({ w, h }: { w: number; h: number }) {
  const { total } = useDatos();
  const filas = total.dm.filter((d) => d.m1 === 'lgbm_directo');
  const m = { t: 20, r: 70, b: 44, l: 220 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const y = d3.scaleBand().domain(filas.map((d) => d.m2)).range([0, ih]).padding(0.3);
  const x = d3.scaleLinear().domain([0, 0.6]).range([0, iw]);
  return (
    <Svg w={w} h={h} label="p-valores de Diebold-Mariano contra LightGBM">
      <g transform={`translate(${m.l},${m.t})`}>
        <rect x={0} width={x(0.05)} y={-6} height={ih + 6} fill={C.banda} />
        <g className="eje">{[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6].map((t) => <text key={t} x={x(t)} y={ih + 26} textAnchor="middle">{num(t, 1)}</text>)}</g>
        <line x1={x(0.05)} x2={x(0.05)} y1={-6} y2={ih} stroke={C.tinta} strokeDasharray="4 4" />
        <text className="etq" x={x(0.05) + 6} y={ih - 6} fontSize={15}>0,05</text>
        {filas.map((d) => {
          const sig = d.p < 0.05;
          return (
            <g key={d.m2} transform={`translate(0,${y(d.m2)})`}>
              <text className="etq" x={-12} y={y.bandwidth() / 2} dy="0.32em" textAnchor="end">vs. {d.n2}</text>
              <rect width={Math.max(x(d.p), 4)} height={y.bandwidth()} rx={5} fill={sig ? C.t45 : C.ambar} />
              <text className={sig ? 'etq' : 'etq-b'} x={Math.max(x(d.p), x(0.05)) + 8} y={y.bandwidth() / 2} dy="0.32em">p {d.p < 0.001 ? '< 0,001' : `= ${pval(d.p)}`}</text>
            </g>
          );
        })}
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- backtest en el tiempo con banda 80 %
export function Backtest({ w, h, modelo = 'lgbm_directo', soloSemana = false }: { w: number; h: number; modelo?: string; soloSemana?: boolean }) {
  const { total, meta } = useDatos();
  let pts: Pred[] = total.pred[modelo];
  if (soloSemana) pts = pts.filter((p) => p.o === pts[0].o);
  const m = { t: 16, r: 16, b: 38, l: 64 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const x = d3.scalePoint<number>().domain(pts.map((_, i) => i)).range([0, iw]).padding(0.3);
  const y = d3.scaleLinear().domain([0, d3.max(pts, (p) => Math.max(p.y, p.hi))! * 1.05]).range([ih, 0]).nice();
  const area = d3.area<Pred>().x((_, i) => x(i)!).y0((p) => y(p.lo)).y1((p) => y(p.hi)).curve(d3.curveMonotoneX)(pts)!;
  const lineaY = d3.line<Pred>().x((_, i) => x(i)!).y((p) => y(p.y))(pts)!;
  const lineaM = d3.line<Pred>().x((_, i) => x(i)!).y((p) => y(p.m))(pts)!;
  const xs = useMemo(() => pts.map((_, i) => m.l + x(i)!), [pts, x, m.l]);
  const buscar = useCallback((px: number) => masCercano(xs, px), [xs]);
  const { ref, h: hi, onMove, onLeave } = useHover(buscar);
  const cortes = pts.map((p, i) => (i > 0 && p.o !== pts[i - 1].o ? i : -1)).filter((i) => i > 0);
  const animar = useAnimar();
  return (
    <Svg w={w} h={h} label="Backtest: real contra pronóstico con intervalo 80 %" svgRef={ref} onMove={onMove} onLeave={onLeave}>
      <g transform={`translate(${m.l},${m.t})`}>
        <GridY ticks={y.ticks(5)} y={y} x1={iw} fmt={(v) => num(v)} />
        {cortes.map((i) => <line key={i} x1={(x(i)! + x(i - 1)!) / 2} x2={(x(i)! + x(i - 1)!) / 2} y1={0} y2={ih} stroke={C.t12} strokeWidth={1.5} />)}
        <motion.path d={area} fill={C.banda} initial={animar ? { opacity: 0 } : false} animate={{ opacity: 1 }} transition={{ duration: animar ? 0.6 : 0 }} />
        <Trazo d={lineaM} stroke={C.ambar} w={3} />
        <Trazo d={lineaY} stroke={C.tinta} w={2} delay={0.3} />
        {pts.map((p, i) => {
          const fuera = p.y < p.lo || p.y > p.hi;
          return <circle key={i} cx={x(i)} cy={y(p.y)} r={fuera ? 5 : 3} fill={fuera ? C.blanco : C.tinta} stroke={C.tinta} strokeWidth={fuera ? 2 : 0} />;
        })}
        {!soloSemana && pts.map((p, i) => p.f === meta.diaIncompleto ? (
          <g key="raro">
            <motion.circle cx={x(i)} cy={y(p.y)} r={16} fill="none" stroke={C.ambar} strokeWidth={3}
              initial={animar ? { scale: 0, opacity: 0 } : false} animate={{ scale: 1, opacity: 1 }} transition={{ delay: animar ? 1.4 : 0, type: 'spring' }} style={{ transformOrigin: `${x(i)}px ${y(p.y)}px` }} />
            <text x={x(i)!} y={y(p.y) + 52} textAnchor="middle" style={{ fontFamily: 'var(--f-mano)', fill: 'var(--ambar)', fontSize: 22 }}>{fechaCorta(p.f)}: export incompleto</text>
          </g>
        ) : null)}
        <g className="eje">
          {pts.map((p, i) => (soloSemana || [0, ...cortes].indexOf(i) % 2 === 0) ? (
            <text key={i} x={x(i)} y={ih + 26} textAnchor="middle">{fechaCorta(p.f)}</text>
          ) : null)}
        </g>
      </g>
      {hi != null && (() => {
        const p = pts[hi];
        const px = xs[hi];
        return (
          <g>
            <line x1={px} x2={px} y1={m.t} y2={m.t + ih} stroke={C.t45} />
            <Tip x={px} y={m.t + y(p.y)} limite={w} w={250} lineas={[`${fechaLarga(p.f)} (h = ${p.h})`, `Real: ${num(p.y)}`, `Pronóstico: ${num(p.m)}`, `Intervalo 80 %: ${num(p.lo)}–${num(p.hi)}`, `Origen: sáb. ${fechaCorta(p.o)}`]} />
          </g>
        );
      })()}
    </Svg>
  );
}

// ---------------------------------------------------------------- clima → mix (calor − frío, en pp)
export function MixTemperatura({ w, h, seg, resaltar }: { w: number; h: number; seg: string; resaltar: string }) {
  const { mix } = useDatos();
  const filas = mix.temperatura.filter((d) => d.seg === seg).sort((a, b) => a.d - b.d);
  const m = { t: 10, r: 60, b: 40, l: 230 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const y = d3.scaleBand().domain(filas.map((d) => d.cat)).range([0, ih]).padding(0.3);
  const lim = Math.ceil(d3.max(filas, (d) => Math.max(Math.abs(d.lo), Math.abs(d.hi)))!);
  const x = d3.scaleLinear().domain([-lim, lim]).range([0, iw]);
  return (
    <Svg w={w} h={h} label="Diferencia de participación calor contra frío">
      <g transform={`translate(${m.l},${m.t})`}>
        <g className="eje">{x.ticks(6).map((t) => <g key={t}><line x1={x(t)} x2={x(t)} y1={0} y2={ih} className="grid" /><text x={x(t)} y={ih + 26} textAnchor="middle">{signed(t, 0)}</text></g>)}</g>
        <line x1={x(0)} x2={x(0)} y1={0} y2={ih} stroke={C.tinta} />
        {filas.map((d) => {
          const on = d.cat === resaltar;
          const col = on ? C.ambar : C.t25;
          return (
            <g key={d.cat} transform={`translate(0,${y(d.cat)})`}>
              <text className={on ? 'etq-b' : 'etq'} x={-12} y={y.bandwidth() / 2} dy="0.32em" textAnchor="end">{d.cat}</text>
              <rect x={Math.min(x(0), x(d.d))} width={Math.abs(x(d.d) - x(0))} height={y.bandwidth()} rx={4} fill={col} />
              <line x1={x(d.lo)} x2={x(d.hi)} y1={y.bandwidth() / 2} y2={y.bandwidth() / 2} stroke={C.tinta} strokeWidth={2} />
              {[d.lo, d.hi].map((v, i) => <line key={i} x1={x(v)} x2={x(v)} y1={y.bandwidth() * 0.25} y2={y.bandwidth() * 0.75} stroke={C.tinta} strokeWidth={2} />)}
              <text className={on ? 'etq-b' : 'etq'} x={d.d < 0 ? x(Math.max(d.hi, 0)) + 10 : x(d.hi) + 10} y={y.bandwidth() / 2} dy="0.32em">{signed(d.d, 1)} pp</text>
            </g>
          );
        })}
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- eventos: efecto con IC 95 %
export function EventosForest({ w, h, unidad, resaltar, solo, emd = false }: { w: number; h: number; unidad: 'pct' | 'tasa'; resaltar: string[]; solo?: string[]; emd?: boolean }) {
  const { eventos } = useDatos();
  const filas: Evento[] = eventos.filter((e) => e.unidad === unidad && (!solo || solo.includes(e.evento)));
  const m = { t: 8, r: 90, b: 40, l: 260 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const y = d3.scaleBand().domain(filas.map((e) => e.evento + e.serie)).range([0, ih]).padding(0.35);
  const x = d3.scaleLinear().domain([Math.min(0, d3.min(filas, (e) => e.lo)!), d3.max(filas, (e) => e.hi)!]).range([0, iw]).nice();
  const f = (v: number) => (unidad === 'pct' ? `${signed(v, 0)} %` : signed(v, 3));
  return (
    <Svg w={w} h={h} label="Efecto de cada evento con su intervalo">
      <g transform={`translate(${m.l},${m.t})`}>
        <g className="eje">{x.ticks(5).map((t) => <g key={t}><line x1={x(t)} x2={x(t)} y1={0} y2={ih} className="grid" /><text x={x(t)} y={ih + 26} textAnchor="middle">{f(t)}</text></g>)}</g>
        <line x1={x(0)} x2={x(0)} y1={0} y2={ih} stroke={C.tinta} />
        {filas.map((e) => {
          const k = e.evento + e.serie;
          const on = resaltar.includes(e.evento);
          const col = on ? C.ambar : C.t45;
          const cy = y(k)! + y.bandwidth() / 2;
          return (
            <g key={k}>
              <text className={on ? 'etq-b' : 'etq'} x={-14} y={cy - 9} textAnchor="end">{e.nombre}</text>
              <text className="etq" x={-14} y={cy + 13} textAnchor="end" fontSize={14}>{e.serieNombre} · desde {fechaCorta(e.desde)}</text>
              <rect x={x(e.lo)} width={x(e.hi) - x(e.lo)} y={cy - 8} height={16} rx={8} fill={C.banda} />
              <line x1={x(e.lo)} x2={x(e.hi)} y1={cy} y2={cy} stroke={col} strokeWidth={3} />
              <circle cx={x(e.ef)} cy={cy} r={8} fill={col} />
              <text className={on ? 'etq-b' : 'etq'} x={x(e.hi) + 10} y={cy} dy="0.32em" fontSize={15}>{f(e.ef)}</text>
              {emd && e.emd != null && <text className="etq" x={x(e.lo)} y={cy + 22} dy="0.32em" fontSize={13}>mín. detectable ±{num(e.emd, 0)} %</text>}
            </g>
          );
        })}
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- Meta Ads: índices semanales
export function AdsSemanal({ w, h }: { w: number; h: number }) {
  const { ads } = useDatos();
  const pts = ads.semanal;
  const m = { t: 16, r: 20, b: 40, l: 60 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const x = d3.scalePoint<number>().domain(pts.map((_, i) => i)).range([0, iw]).padding(0.4);
  const y = d3.scaleLinear().domain([0, d3.max(pts, (p) => Math.max(p.g, p.c))! * 1.08]).range([ih, 0]).nice();
  const lin = (k: 'g' | 'c') => d3.line<(typeof pts)[number]>().x((_, i) => x(i)!).y((p) => y(p[k]))(pts)!;
  const xs = useMemo(() => pts.map((_, i) => m.l + x(i)!), [pts, x, m.l]);
  const buscar = useCallback((px: number) => masCercano(xs, px), [xs]);
  const { ref, h: hi, onMove, onLeave } = useHover(buscar);
  const ver = pts.map((p, i) => (p.ver ? i : -1)).filter((i) => i >= 0);
  return (
    <Svg w={w} h={h} label="Gasto en Meta y clientes nuevos, índice" svgRef={ref} onMove={onMove} onLeave={onLeave}>
      <g transform={`translate(${m.l},${m.t})`}>
        {ver.length > 0 && <rect x={x(ver[0])! - 10} width={x(ver[ver.length - 1])! - x(ver[0])! + 20} y={0} height={ih} fill={C.banda} />}
        <GridY ticks={y.ticks(5)} y={y} x1={iw} fmt={(v) => num(v)} />
        <Trazo d={lin('c')} stroke={C.t45} w={2.2} />
        <Trazo d={lin('g')} stroke={C.ambar} w={3.2} delay={0.2} />
        <g className="eje">{pts.map((p, i) => (i % 4 === 0 ? <text key={i} x={x(i)} y={ih + 26} textAnchor="middle">{fechaCorta(p.s)}</text> : null))}</g>
        {ver.length > 0 && <text className="etq" x={x(ver[0])! - 4} y={20}>verano</text>}
      </g>
      {hi != null && (() => {
        const p = pts[hi];
        const px = xs[hi];
        return (
          <g>
            <line x1={px} x2={px} y1={m.t} y2={m.t + ih} stroke={C.t45} />
            <Tip x={px} y={m.t + 70} limite={w} w={250} lineas={[`Semana del ${fechaLarga(p.s)}`, `Gasto (índice): ${num(p.g, 1)}`, `Clientes nuevos (índice): ${num(p.c, 1)}`]} />
          </g>
        );
      })()}
    </Svg>
  );
}

// ---------------------------------------------------------------- plan: curva de costo por percentil
export function CurvaCosto({ w, h, pasoNota = 1 }: { w: number; h: number; pasoNota?: number }) {
  const { plan } = useDatos();
  const { paso } = usePaso();
  const animar = useAnimar();
  const m = { t: 30, r: 30, b: 54, l: 52 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const pts = useMemo(() => plan.curva.filter((c) => c.metodo === 'lgbm'), [plan]);
  const ps = pts.map((c) => c.p);
  const x = d3.scaleLinear().domain([d3.min(ps)!, d3.max(ps)!]).range([0, iw]);
  const y = d3.scaleLinear().domain([0, d3.max(pts, (c) => c.costo)! * 1.1]).range([ih, 0]).nice();
  const xs = useMemo(() => pts.map((c) => m.l + x(c.p)), [pts, x, m.l]);
  const buscar = useCallback((px: number) => masCercano(xs, px), [xs]);
  const { ref, h: hi, onMove, onLeave } = useHover(buscar);
  const el = plan.elegido;
  const p90 = pts.find((c) => c.p === 90);
  const ver = paso >= pasoNota;
  const MG = motion.g as unknown as React.FC<Record<string, unknown>>;
  const d = d3.line<(typeof pts)[number]>().x((p) => x(p.p)).y((p) => y(p.costo))(pts)!;
  return (
    <Svg w={w} h={h} label="Plata perdida por vianda según el colchón" svgRef={ref} onMove={onMove} onLeave={onLeave}>
      <g transform={`translate(${m.l},${m.t})`}>
        <GridY ticks={y.ticks(4)} y={y} x1={iw} fmt={(v) => `$${num(v)}`} />
        <g className="eje">{ps.filter((p) => p % 10 === 0).map((p) => <text key={p} x={x(p)} y={ih + 26} textAnchor="middle">{p}</text>)}</g>
        <text className="etq" x={0} y={ih + 50} fontSize={15}>← menos colchón</text>
        <text className="etq" x={iw / 2} y={ih + 50} textAnchor="middle" fontSize={15} fontWeight={600}>p</text>
        <text className="etq" x={iw} y={ih + 50} textAnchor="end" fontSize={15}>más colchón →</text>
        <Trazo d={d} stroke={C.ambar} w={4} />
        <MG initial={false} animate={{ opacity: ver ? 1 : 0 }} transition={{ duration: animar ? 0.5 : 0 }}>
          {p90 && (
            <g>
              <circle cx={x(90)} cy={y(p90.costo)} r={7} fill={C.blanco} stroke={C.ambar} strokeWidth={3} />
              <text x={x(90) - 16} y={y(p90.costo) - 30} textAnchor="end" fontSize={22} fontWeight={700} fill={C.tinta}>${num(p90.costo, 1)}</text>
              <text x={x(90) - 16} y={y(p90.costo) - 10} textAnchor="end" fontSize={15} fill={C.t70}>con p = 90</text>
            </g>
          )}
          <text x={x(el.p)} y={y(el.costo) - 52} textAnchor="middle" fontSize={26} fontWeight={700} fill={C.ambar}>${num(el.costo, 1)}</text>
          <text x={x(el.p)} y={y(el.costo) - 30} textAnchor="middle" fontSize={15} fill={C.tinta}>con p = {el.p}: lo más barato</text>
        </MG>
        <circle cx={x(el.p)} cy={y(el.costo)} r={9} fill={C.ambar} stroke={C.blanco} strokeWidth={3} />
      </g>
      {hi != null && (() => {
        const c = pts[hi];
        const px = xs[hi];
        return (
          <g>
            <line x1={px} x2={px} y1={m.t} y2={m.t + ih} stroke={C.t45} />
            <Tip x={px} y={m.t + y(c.costo)} limite={w} w={250} lineas={[`p = ${c.p}`, `$${num(c.costo, 1)} perdidos por vianda`, `sobra ${pct(c.sob, 1)} · falta ${pct(c.fal, 1)}`]} />
          </g>
        );
      })()}
    </Svg>
  );
}

// ---------------------------------------------------------------- esquema walk-forward (con los orígenes reales)
export function WalkForward({ w, h }: { w: number; h: number }) {
  const { meta } = useDatos();
  const n = meta.origenes.length;
  const ini = 8; // semanas de entrenamiento antes del primer origen
  const total = n + ini;
  const m = { t: 56, r: 4, b: 4, l: 76 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const gap = 5;
  const cw = (iw - gap * (total - 1)) / total;
  const ch = Math.min(cw, (ih - gap * 1.6 * (n - 1)) / n);
  const rg = (ih - ch * n) / (n - 1);
  const animar = useAnimar();
  const MRect = motion.rect as unknown as React.FC<Record<string, unknown>>;
  return (
    <Svg w={w} h={h} label="Esquema del walk-forward">
      <g transform={`translate(${m.l},16)`} fontSize={15} fill={C.t70}>
        <rect x={0} y={0} width={16} height={16} rx={4} fill={C.t25} />
        <text x={26} y={13}>entrena</text>
        <rect x={110} y={0} width={16} height={16} rx={4} fill={C.ambar} />
        <text x={136} y={13}>pronostica</text>
        <rect x={244} y={0} width={16} height={16} rx={4} fill="none" stroke={C.t25} strokeWidth={1.2} />
        <text x={270} y={13}>todavía no se conoce</text>
        <text x={iw} y={13} textAnchor="end" fill={C.t45}>una celda = una semana →</text>
      </g>
      <g transform={`translate(${m.l},${m.t})`}>
        {meta.origenes.map((o, i) => {
          const y0 = i * (ch + rg);
          const ult = i === n - 1;
          const f = ini + i;
          return (
            <g key={o}>
              <text x={-14} y={y0 + ch / 2} dy="0.34em" textAnchor="end" fontSize={15} fill={ult ? C.tinta : C.t45} fontWeight={ult ? 700 : 400} style={{ fontFeatureSettings: "'tnum'" }}>{fechaCorta(o)}</text>
              {d3.range(total).map((k) => {
                const x0 = k * (cw + gap);
                const tipo = k < f ? 'e' : k === f ? 'p' : 'n';
                const d = animar ? i * 0.06 + k * 0.012 : 0;
                return (
                  <MRect key={k} x={x0} y={y0} width={cw} height={ch} rx={Math.min(5, ch / 3)}
                    fill={tipo === 'e' ? C.t25 : tipo === 'p' ? C.ambar : 'none'}
                    stroke={tipo === 'n' ? C.t12 : 'none'} strokeWidth={1.2}
                    style={{ transformOrigin: `${x0 + cw / 2}px ${y0 + ch / 2}px`, transformBox: 'view-box' }}
                    initial={animar ? { opacity: 0, scale: 0.6 } : false}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={animar ? { delay: tipo === 'p' ? d + 0.25 : d, duration: 0.35, ease: [0.22, 1, 0.36, 1] } : { duration: 0 }} />
                );
              })}
            </g>
          );
        })}
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- STL: serie, tendencia, estacional, resto
export function StlPaneles({ w, h, mostrar = 4, bajadas }: { w: number; h: number; mostrar?: number; bajadas?: string[] }) {
  const { eda } = useDatos();
  const st = eda.stl;
  const comps = [
    { k: 'y' as const, nombre: 'serie', col: C.tinta },
    { k: 't' as const, nombre: 'tendencia', col: C.ambar },
    { k: 's' as const, nombre: 'estacional (6)', col: C.oro },
    { k: 'r' as const, nombre: 'resto', col: C.t45 },
  ];
  const m = { l: bajadas ? 190 : 150, r: 10, t: 6, b: 30 };
  const iw = w - m.l - m.r;
  const ph = (h - m.t - m.b) / 4;
  const fechas = st.map((d) => toDate(d.f));
  const x = d3.scaleTime().domain(d3.extent(fechas) as [Date, Date]).range([0, iw]);
  return (
    <Svg w={w} h={h} label="Descomposición STL del total">
      <g transform={`translate(${m.l},${m.t})`}>
        {comps.map((c, j) => {
          const ext = d3.extent(st, (d) => d[c.k]) as [number, number];
          const y = d3.scaleLinear().domain(ext).range([ph - 10, 4]);
          const d = d3.line<number>().x((i) => x(fechas[i])).y((i) => y(st[i][c.k]))(st.map((_, i) => i))!;
          return (
            <g key={c.k} transform={`translate(0,${j * ph})`} opacity={j < mostrar ? 1 : 0.12}>
              <rect width={iw} height={ph - 6} fill="none" stroke={C.t12} />
              <text className="etq-b" x={-14} y={ph / 2} dy={bajadas ? '-0.25em' : '0.32em'} textAnchor="end">{c.nombre}</text>
              {bajadas && <text x={-14} y={ph / 2} dy="1.25em" textAnchor="end" fontSize={15} fill={C.t45}>{bajadas[j]}</text>}
              <path d={d} fill="none" stroke={c.col} strokeWidth={c.k === 't' ? 3 : 1.3} />
            </g>
          );
        })}
        <g className="eje">{x.ticks(d3.timeMonth.every(3)!).map((t) => <text key={+t} x={x(t)} y={4 * ph + 18} textAnchor="middle">{mesAnio(t)}</text>)}</g>
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- ACF / PACF (bastones), banda ±1,96/√n
export function Correlograma({ w, h, tipo, serie, titulo, min = -1, ejeX, simple = false }: { w: number; h: number; tipo: 'acf' | 'pacf'; serie: 'nivel' | 'dif'; titulo: string; min?: number; ejeX?: string; simple?: boolean }) {
  const { eda, meta } = useDatos();
  const a = eda.autocorr[serie];
  const v = a[tipo];
  const m = { t: simple ? 8 : 34, r: 10, b: ejeX ? 52 : 30, l: simple ? 34 : 46 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const x = d3.scaleLinear().domain([0, v.length - 1]).range([0, iw]);
  const y = d3.scaleLinear().domain([min, 1]).range([ih, 0]);
  const ticksY = simple ? [0, 1] : min === -1 ? [-1, 0, 1] : d3.range(Math.ceil(min * 2) / 2, 1.001, 0.5);
  const banda = 1.96 / Math.sqrt(a.n);
  const pts = v.map((r, k) => ({ r, k }));
  const xs = useMemo(() => pts.map((p) => m.l + x(p.k)), [pts, x, m.l]);
  const buscar = useCallback((px: number) => masCercano(xs, px), [xs]);
  const { ref, h: hi, onMove, onLeave } = useHover(buscar);
  return (
    <Svg w={w} h={h} label={titulo} svgRef={ref} onMove={onMove} onLeave={onLeave}>
      {!simple && <text className="etq-b" x={m.l} y={20}>{titulo}</text>}
      <g transform={`translate(${m.l},${m.t})`}>
        <rect x={0} width={iw} y={y(banda)} height={y(-banda) - y(banda)} fill={C.banda} />
        {!simple && min !== -1 && ticksY.filter((t) => t !== 0).map((t) => <line key={t} x1={0} x2={iw} y1={y(t)} y2={y(t)} stroke={C.t12} strokeDasharray="3 5" />)}
        <line x1={0} x2={iw} y1={y(0)} y2={y(0)} stroke={C.t45} />
        <g className="eje">{ticksY.map((t) => <text key={t} x={-8} y={y(t)} dy="0.32em" textAnchor="end">{num(t, t % 1 ? 1 : 0)}</text>)}
          {d3.range(0, v.length, meta.periodo).map((k) => <text key={k} x={x(k)} y={ih + 22} textAnchor="middle">{k}</text>)}
          {ejeX && <text x={iw / 2} y={ih + 46} textAnchor="middle" fontSize={14}>{ejeX}</text>}</g>
        {pts.slice(1).map((p) => {
          const est = p.k % meta.periodo === 0;
          const col = est ? C.ambar : C.t45;
          return <g key={p.k}><line x1={x(p.k)} x2={x(p.k)} y1={y(0)} y2={y(p.r)} stroke={col} strokeWidth={est ? 3 : 2} /><circle cx={x(p.k)} cy={y(p.r)} r={est ? 4.5 : 3} fill={col} /></g>;
        })}
      </g>
      {hi != null && hi > 0 && <Tip x={xs[hi]} y={m.t + y(pts[hi].r)} limite={w} w={170} lineas={[`rezago ${pts[hi].k}`, `${tipo.toUpperCase()} = ${num(pts[hi].r, 3)}`]} />}
    </Svg>
  );
}

// ---------------------------------------------------------------- Meta: clics contra clientes nuevos (log-log)
export function AdsClics({ w, h }: { w: number; h: number }) {
  const { ads } = useDatos();
  const pts = ads.semanal.filter((p) => p.k != null && p.s >= ads.clics.desde);
  const m = { t: 16, r: 24, b: 54, l: 64 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const x = d3.scaleLog().domain([d3.min(pts, (p) => p.k!)! * 0.9, d3.max(pts, (p) => p.k!)! * 1.1]).range([0, iw]);
  const y = d3.scaleLog().domain([d3.min(pts, (p) => p.c)! * 0.88, d3.max(pts, (p) => p.c)! * 1.08]).range([ih, 0]);
  const lx = pts.map((p) => Math.log(p.k!)), ly = pts.map((p) => Math.log(p.c));
  const mx = d3.mean(lx)!, my = d3.mean(ly)!;
  const b = d3.sum(lx.map((v, i) => (v - mx) * (ly[i] - my))) / d3.sum(lx.map((v) => (v - mx) ** 2));
  const [x0, x1] = x.domain();
  const fy = (v: number) => Math.exp(my + b * (Math.log(v) - mx));
  const xs = useMemo(() => pts.map((p) => m.l + x(p.k!)), [pts, x, m.l]);
  const buscar = useCallback((px: number) => masCercano(xs, px), [xs]);
  const { ref, h: hi, onMove, onLeave } = useHover(buscar);
  const ticksX = [50, 60, 80, 100, 120, 150].filter((t) => t >= x0 && t <= x1);
  const ticksY = [50, 70, 100, 140, 200].filter((t) => t >= y.domain()[0] && t <= y.domain()[1]);
  return (
    <Svg w={w} h={h} label="Clics de la campaña contra clientes nuevos" svgRef={ref} onMove={onMove} onLeave={onLeave}>
      <g transform={`translate(${m.l},${m.t})`}>
        <GridY ticks={ticksY} y={y} x1={iw} fmt={(v) => num(v)} />
        <g className="eje">{ticksX.map((t) => <text key={t} x={x(t)} y={ih + 26} textAnchor="middle">{t}</text>)}
          <text x={iw / 2} y={ih + 50} textAnchor="middle" fontSize={15}>clics de la campaña (índice, escala log)</text></g>
        <Trazo d={`M${x(x0)},${y(fy(x0))}L${x(x1)},${y(fy(x1))}`} stroke={C.tinta} w={2} dash="7 6" delay={0.4} />
        {pts.map((p) => (
          <circle key={p.s} cx={x(p.k!)} cy={y(p.c)} r={8} fill={p.s >= '2026-11-02' ? C.tinta : C.ambar} fillOpacity={0.85} stroke={C.blanco} strokeWidth={1.5} />
        ))}
      </g>
      {hi != null && (() => {
        const p = pts[hi];
        return <Tip x={xs[hi]} y={m.t + y(p.c)} limite={w} w={250} lineas={[`Semana del ${fechaLarga(p.s)}`, `Clics (índice): ${num(p.k!, 1)}`, `Clientes nuevos (índice): ${num(p.c, 1)}`]} />;
      })()}
    </Svg>
  );
}

// ---------------------------------------------------------------- recetario: % de los kg por familia
export function FamiliasBarras({ w, h }: { w: number; h: number }) {
  const { compras } = useDatos();
  const f = compras.familias.filter((x) => x.pct > 0).slice(0, 8);
  const m = { t: 6, r: 70, b: 6, l: 260 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const y = d3.scaleBand().domain(f.map((x) => x.familia)).range([0, ih]).padding(0.3);
  const x = d3.scaleLinear().domain([0, d3.max(f, (z) => z.pct)!]).range([0, iw]);
  const animar = useAnimar();
  return (
    <Svg w={w} h={h} label="Porcentaje de los kilos por familia de ingrediente">
      <g transform={`translate(${m.l},${m.t})`}>
        {f.map((z, i) => (
          <g key={z.familia}>
            <text className={i === 0 ? 'etq-b' : 'etq'} x={-14} y={y(z.familia)! + y.bandwidth() / 2} dy="0.32em" textAnchor="end">{z.familia}</text>
            <motion.rect y={y(z.familia)} height={y.bandwidth()} rx={6} fill={i === 0 ? C.ambar : C.t25}
              initial={animar ? { width: 0 } : false} animate={{ width: x(z.pct) }} transition={{ duration: animar ? 0.7 : 0, delay: animar ? 0.05 * i : 0 }} />
            <text className="etq" x={x(z.pct) + 10} y={y(z.familia)! + y.bandwidth() / 2} dy="0.32em">{num(z.pct, 1)} %</text>
          </g>
        ))}
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- robustez: matriz de puestos (modelo × serie × ventana)
/** Puesto 1 = ámbar vivo; puesto 8 = apagado (tinta 11 % sobre crema). Valores hex de styles.css. */
const colorPuesto = d3.scaleLinear<string>().domain([1, 8]).range(['#ea9a02', '#f0eadc']).interpolate(d3.interpolateRgb);

/** Filas: los 8 modelos (de menor a mayor peor caso). Columnas: Total, Particulares y Empresas, cada una
 *  con la ventana anterior y la nueva. `resaltar` (desde el paso indicado) marca la fila de ese modelo. */
export function MatrizPuestos({ w, h, resaltar = 'lgbm_directo', pasoResalte = 1 }: { w: number; h: number; resaltar?: string; pasoResalte?: number }) {
  const { total } = useDatos();
  const rb = total.robustez;
  const filas = rb.puestos;
  const cols = rb.series.flatMap((s) => (['anterior', 'nueva'] as const).map((v) => ({ serie: s.id, ventana: v })));
  const m = { t: 70, r: 8, b: 8, l: 214 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const x = d3.scaleBand<number>().domain(cols.map((_, i) => i)).range([0, iw]).paddingInner(0.08);
  const y = d3.scaleBand<string>().domain(filas.map((f) => f.id)).range([0, ih]).paddingInner(0.1);
  const visto = useVisto(pasoResalte);
  const animar = useAnimar();
  const gx = (k: number) => x(2 * k)!; // inicio del grupo de la serie k
  const gw = 2 * x.bandwidth() + x.step() - x.bandwidth();
  return (
    <Svg w={w} h={h} label="Puesto de cada modelo por serie y ventana (1 = menor MASE)">
      <g transform={`translate(${m.l},${m.t})`}>
        {rb.series.map((s, k) => (
          <g key={s.id}>
            <text className="etq-b" x={gx(k) + gw / 2} y={-40} textAnchor="middle">{s.nombre}</text>
            <line x1={gx(k) + 4} x2={gx(k) + gw - 4} y1={-30} y2={-30} stroke={C.t25} />
          </g>
        ))}
        {cols.map((c, i) => <text key={i} className="etq" x={x(i)! + x.bandwidth() / 2} y={-10} textAnchor="middle" fontSize={14} fill={C.t70}>{c.ventana}</text>)}
        {filas.map((f, j) => {
          const es = f.id === resaltar;
          const apagar = visto && !es;
          return (
            <motion.g key={f.id} transform={`translate(0,${y(f.id)})`} animate={{ opacity: apagar ? 0.38 : 1 }} transition={{ duration: animar ? 0.5 : 0 }}>
              <text className={es && visto ? 'etq-b' : 'etq'} x={-14} y={y.bandwidth() / 2} dy="0.32em" textAnchor="end">{f.nombre}</text>
              {f.celdas.map((c, i) => (
                <g key={i}>
                  <motion.rect x={x(i)} width={x.bandwidth()} height={y.bandwidth()} rx={6} fill={colorPuesto(c.puesto)}
                    initial={animar ? { opacity: 0 } : false} animate={{ opacity: 1 }} transition={{ duration: animar ? 0.4 : 0, delay: animar ? j * 0.05 + i * 0.03 : 0 }} />
                  <text x={x(i)! + x.bandwidth() / 2} y={y.bandwidth() / 2} dy="0.34em" textAnchor="middle" fontSize={19} fontWeight={700}
                    style={{ fill: c.puesto <= 2 ? 'var(--blanco)' : 'var(--tinta)' }}>
                    {c.puesto}
                    <title>{`${f.nombre}, ${c.serie} ${c.ventana}: puesto ${c.puesto}, MASE ${num(c.mase, 3)}`}</title>
                  </text>
                </g>
              ))}
            </motion.g>
          );
        })}
        {visto && (() => {
          const yy = y(resaltar)!;
          return <motion.rect x={-m.l + 6} y={yy - 5} width={w - 14} height={y.bandwidth() + 10} rx={10} fill="none" stroke={C.ambar} strokeWidth={3}
            initial={animar ? { opacity: 0 } : false} animate={{ opacity: 1 }} transition={{ duration: animar ? 0.5 : 0 }} />;
        })()}
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- robustez: peor caso de cada modelo (% sobre el mejor)
export function PeorCaso({ w, h, resaltar = 'lgbm_directo', tope = 50 }: { w: number; h: number; resaltar?: string; tope?: number }) {
  const { total } = useDatos();
  const filas = total.robustez.peor;
  const m = { t: 6, r: 74, b: 4, l: 196 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const y = d3.scaleBand<string>().domain(filas.map((f) => f.id)).range([0, ih]).paddingInner(0.42);
  const x = d3.scaleLinear().domain([0, tope]).range([0, iw]);
  const animar = useAnimar();
  const bh = y.bandwidth() * 0.62;
  return (
    <Svg w={w} h={h} label="Peor caso de cada modelo: % de MASE por encima del mejor">
      <g transform={`translate(${m.l},${m.t})`}>
        {filas.map((f, i) => {
          const es = f.id === resaltar;
          const corta = f.pct > tope;
          const largo = Math.max(x(Math.min(f.pct, tope)), 3);
          return (
            <g key={f.id} transform={`translate(0,${y(f.id)})`}>
              <text className={es ? 'etq-b' : 'etq'} x={-12} y={bh / 2} dy="0.32em" textAnchor="end" fontSize={es ? 18 : 16}>{f.nombre}</text>
              <motion.rect height={bh} rx={5} fill={es ? C.ambar : C.t25}
                initial={animar ? { width: 0 } : false} animate={{ width: largo }} transition={{ duration: animar ? 0.6 : 0, delay: animar ? i * 0.06 : 0 }} />
              <text className={es ? 'etq-b' : 'etq'} x={corta ? largo - 8 : largo + 8} y={bh / 2} dy="0.32em" textAnchor={corta ? 'end' : 'start'} fontSize={16}
                style={corta ? { fill: 'var(--tinta)' } : undefined}>{signed(f.pct, 1)} %{corta ? ' →' : ''}</text>
              <text x={0} y={bh + 14} fontSize={12.5} style={{ fill: 'var(--tinta-70)' }}>{f.serieNombre.toLowerCase()} · ventana {f.ventana}</text>
            </g>
          );
        })}
      </g>
    </Svg>
  );
}

// ---------------------------------------------------------------- robustez: rango de puestos de cada modelo
/** Una fila por modelo (ordenadas por su peor puesto). Eje x: puesto 1 (mejor) a 8. Cada punto es una de las
 *  pruebas (serie × ventana); la cápsula va del mejor al peor puesto. La franja sombreada marca "los 2 mejores":
 *  el único modelo cuya cápsula entra entera en la franja es el más confiable. */
export function RangoPuestos({ w, h, resaltar = 'lgbm_directo', pasoResalte = 1 }: { w: number; h: number; resaltar?: string; pasoResalte?: number }) {
  const { total } = useDatos();
  const filas = useMemo(() => total.robustez.puestos.map((f) => {
    const p = f.celdas.map((c) => c.puesto);
    const cuenta = d3.rollups(p, (v) => v.length, (v) => v).sort((a, b) => a[0] - b[0]);
    return { id: f.id, nombre: f.nombre, min: Math.min(...p), max: Math.max(...p), media: d3.mean(p)!, cuenta };
  }).sort((a, b) => a.max - b.max || a.media - b.media), [total]);
  const nMod = filas.length;
  const m = { t: 58, r: 120, b: 8, l: 230 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const x = d3.scaleLinear().domain([0.5, nMod + 0.5]).range([0, iw]);
  const y = d3.scaleBand<string>().domain(filas.map((f) => f.id)).range([0, ih]).paddingInner(0.25);
  const visto = useVisto(pasoResalte);
  const animar = useAnimar();
  const r = Math.min(y.bandwidth() * 0.36, 17);
  const yc = y.bandwidth() / 2;
  return (
    <Svg w={w} h={h} label="Mejor y peor puesto de cada modelo en las seis pruebas">
      <g transform={`translate(${m.l},${m.t})`}>
        <rect x={x(0.5)} y={-20} width={x(2.5) - x(0.5)} height={ih + 20} rx={12} fill={C.t12} />
        <text className="etq-b" x={(x(0.5) + x(2.5)) / 2} y={-30} textAnchor="middle" fontSize={16} fill={C.tinta}>los 2 mejores</text>
        {d3.range(1, nMod + 1).map((p) => (
          <text key={p} className="etq" x={x(p)} y={-30} textAnchor="middle" fontSize={15} fill={C.t45} style={{ display: p <= 2 ? 'none' : undefined }}>{p}.º</text>
        ))}
        <text className="etq" x={iw + 14} y={-30} fontSize={15} fill={C.t70}>peor puesto</text>
        {filas.map((f, j) => {
          const es = f.id === resaltar;
          const apagar = visto && !es;
          const col = es && visto ? C.ambar : C.t45;
          return (
            <motion.g key={f.id} transform={`translate(0,${y(f.id)})`} animate={{ opacity: apagar ? 0.45 : 1 }} transition={{ duration: animar ? 0.5 : 0 }}>
              <text className={es && visto ? 'etq-b' : 'etq'} x={-18} y={yc} dy="0.32em" textAnchor="end" fontSize={es && visto ? 21 : 18}>{f.nombre}</text>
              <line x1={0} x2={iw} y1={yc} y2={yc} stroke={C.t12} strokeDasharray="2 5" />
              <motion.rect y={yc - r} height={2 * r} rx={r} fill={es && visto ? 'rgba(234,154,2,0.22)' : C.t12}
                initial={animar ? { x: x(f.min) - r, width: 2 * r } : false}
                animate={{ x: x(f.min) - r, width: x(f.max) - x(f.min) + 2 * r }}
                transition={{ duration: animar ? 0.6 : 0, delay: animar ? j * 0.06 : 0 }} />
              {f.cuenta.map(([p, n]) => (
                <g key={p}>
                  <circle cx={x(p)} cy={yc} r={r * 0.78} fill={col} />
                  {n > 1 && <text x={x(p)} y={yc} dy="0.35em" textAnchor="middle" fontSize={13} fontWeight={700} style={{ fill: 'var(--blanco)' }}>×{n}</text>}
                  <title>{`${f.nombre}: ${n} ${n > 1 ? 'pruebas' : 'prueba'} en el puesto ${p}`}</title>
                </g>
              ))}
              <text className={es && visto ? 'etq-b' : 'etq'} x={iw + 14} y={yc} dy="0.32em" fontSize={es && visto ? 22 : 18}
                style={{ fill: es && visto ? 'var(--ambar)' : undefined }}>{f.max}.º</text>
            </motion.g>
          );
        })}
      </g>
    </Svg>
  );
}
