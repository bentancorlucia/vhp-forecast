import { useCallback, useRef, useState, type ReactNode } from 'react';

/** Paleta de gráficos: una serie protagonista en ámbar; el resto en oro o tinta con opacidad. */
export const C = {
  ambar: 'var(--ambar)',
  oro: 'var(--oro)',
  tinta: 'var(--tinta)',
  t70: 'var(--tinta-70)',
  t45: 'var(--tinta-45)',
  t25: 'var(--tinta-25)',
  t12: 'var(--tinta-12)',
  banda: 'var(--crema-osc)',
  blanco: 'var(--blanco)',
} as const;

export function Svg({ w, h, label, children, onMove, onLeave, svgRef }: {
  w: number; h: number; label: string; children: ReactNode;
  onMove?: (e: React.MouseEvent<SVGSVGElement>) => void; onLeave?: () => void; svgRef?: React.RefObject<SVGSVGElement>;
}) {
  return (
    <svg ref={svgRef} width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label} className="svg-chart" onMouseMove={onMove} onMouseLeave={onLeave}>
      {children}
    </svg>
  );
}

/** Hover que funciona aunque el escenario esté escalado con transform: pasa a coordenadas del SVG. */
export function useHover<T>(buscar: (x: number, y: number) => T | null) {
  const ref = useRef<SVGSVGElement>(null);
  const [h, setH] = useState<T | null>(null);
  const onMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const svg = ref.current;
    const m = svg?.getScreenCTM();
    if (!svg || !m) return;
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
    setH(buscar(p.x, p.y));
  }, [buscar]);
  return { ref, h, onMove, onLeave: () => setH(null) };
}

/** Caja de tooltip dentro del SVG. */
export function Tip({ x, y, lineas, w = 230, limite }: { x: number; y: number; lineas: ReactNode[]; w?: number; limite: number }) {
  const h = 14 + lineas.length * 22;
  const tx = x + w + 16 > limite ? x - w - 14 : x + 14;
  return (
    <g className="tip" transform={`translate(${tx},${Math.max(0, y - h / 2)})`} pointerEvents="none">
      <rect width={w} height={h} rx={8} />
      {lineas.map((l, i) => <text key={i} x={12} y={24 + i * 22} fontWeight={i === 0 ? 700 : 400}>{l}</text>)}
    </g>
  );
}

export function GridY({ ticks, y, x0 = 0, x1, fmt }: { ticks: number[]; y: (v: number) => number; x0?: number; x1: number; fmt: (v: number) => string }) {
  return (
    <g className="eje">
      {ticks.map((t) => (
        <g key={t} transform={`translate(0,${y(t)})`}>
          <line x1={x0} x2={x1} className="grid" />
          <text x={x0 - 10} dy="0.32em" textAnchor="end">{fmt(t)}</text>
        </g>
      ))}
    </g>
  );
}

export function masCercano(xs: number[], px: number) {
  let best = 0, d = Infinity;
  for (let i = 0; i < xs.length; i++) {
    const di = Math.abs(xs[i] - px);
    if (di < d) { d = di; best = i; }
  }
  return best;
}
