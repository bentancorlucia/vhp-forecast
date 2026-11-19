// Método · el flujo de trabajo (main.py) y el dataset. Cada etapa del código ordena el resto de la presentación.
import type { FC } from 'react';
import { motion } from 'framer-motion';
import { CURVA, Icono, Paso, useAnimar, useDatos, usePaso, useVisto } from '../components/marca';
import type { Diapo } from './tipos';

const S = 'Método';

// ---------------------------------------------------------------- el flujo de trabajo
const MDiv = motion.div as unknown as FC<Record<string, unknown>>;

function Flujo() {
  const { meta, dataset, total } = useDatos();
  const { paso } = usePaso();
  const animar = useAnimar();
  const etapas = [
    { t: 'Datos', que: 'Limpiar, anonimizar y armar la serie de días hábiles.', cmd: 'prepare · anonymize · calendar · clima' },
    { t: 'Explorar', que: 'Tendencia, semana y estacionariedad.', cmd: 'eda' },
    { t: 'Modelar', que: `${total.metricas.length} candidatos con la misma interfaz.`, cmd: 'backtest' },
    { t: 'Validar', que: `Walk-forward en ${meta.nOrigenes} sábados.`, cmd: 'backtest' },
    { t: 'Explicar', que: 'Clima, eventos y pauta en Meta.', cmd: 'mix · eventos · ads' },
    { t: 'Decidir', que: 'Pronóstico + colchón → la compra.', cmd: 'plan · compras · report' },
  ];
  const visto = paso >= 1;
  const LINEA = 1.5; // segundos que tarda la línea en cruzar
  const t = (i: number) => (animar ? 0.15 + (i / (etapas.length - 1)) * LINEA : 0);
  return (
    <div className="flujo2">
      <Paso n={0}>
        <p className="pregunta" style={{ margin: 0 }}>Un solo comando, <code className="flujo2-cmd">python main.py all</code>, corre <b>seis etapas en orden</b>. Cada parte de esta presentación es una de ellas.</p>
      </Paso>

      <div className="flujo2-linea" style={{ visibility: visto ? 'visible' : 'hidden' }}>
        <div className="flujo2-riel">
          <MDiv className="flujo2-trazo"
            initial={animar && visto ? { scaleX: 0 } : false}
            animate={{ scaleX: visto ? 1 : 0 }}
            transition={{ duration: animar ? LINEA : 0, ease: [0.65, 0, 0.35, 1], delay: animar ? 0.15 : 0 }} />
        </div>
        {etapas.map((e, i) => (
          <div key={e.t} className="flujo2-etapa">
            <MDiv className="flujo2-nodo"
              initial={animar && visto ? { scale: 0, opacity: 0 } : false}
              animate={visto ? { scale: 1, opacity: 1 } : { scale: 0, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 420, damping: 22, delay: t(i) }}>
              {i + 1}
            </MDiv>
            <MDiv className="flujo2-texto"
              initial={animar && visto ? { opacity: 0, y: 14 } : false}
              animate={visto ? { opacity: 1, y: 0 } : { opacity: 0, y: 14 }}
              transition={{ duration: animar ? 0.55 : 0, ease: CURVA, delay: t(i) + (animar ? 0.12 : 0) }}>
              <h3>{e.t}</h3>
              <p>{e.que}</p>
              <span className="mono">{e.cmd}</span>
            </MDiv>
          </div>
        ))}
      </div>

      <Paso n={1} demora={LINEA + 0.45}>
        <p className="flujo2-pie">
          {dataset.nTests} tests con pytest <i>·</i> lo crudo nunca sale de <span className="mono">raw_private/</span> <i>·</i> cada número sale de <span className="mono">reports/</span>
        </p>
      </Paso>
    </div>
  );
}

// ---------------------------------------------------------------- el dataset
/** Paso del flujo, en chico: ícono + título + una línea. */
function Nodo({ ic, t, sub, clave }: { ic: string; t: string; sub: string; clave?: boolean }) {
  return (
    <div className={`ds-nodo${clave ? ' clave' : ''}`}>
      <div className="ds-ico"><Icono n={ic} tam={30} /></div>
      <div><h3>{t}</h3><p>{sub}</p></div>
    </div>
  );
}

const FlechaDer = () => (
  <svg className="ds-flecha" width="56" height="24" viewBox="0 0 56 24" aria-hidden>
    <path d="M2 12H48M38 3l11 9-11 9" fill="none" stroke="var(--ambar)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const DIAS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const fechaCorta = (iso: string) => {
  const d = new Date(iso + 'T12:00:00');
  return `${DIAS[d.getDay()]} ${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
};
const coma = (x: number) => x.toLocaleString('es-UY', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function Dataset() {
  const { dataset: ds } = useDatos();
  const nv = `nueva${useVisto(2) ? ' on' : ''}`;
  const agregadas: [string, string][] = [['calendario', 'evento'], ['sol', 'máx °C'], ['nube', 'lluvia mm'], ['megafono', 'Meta']];
  return (
    <div className="ds">
      <Paso n={0} className="ds-flujo">
        <Nodo ic="archivo" t="Exports" sub="una fila = un producto de un pedido" />
        <FlechaDer />
        <Nodo ic="candado" t="Limpiar y anonimizar" sub="sin datos personales · × K" />
        <FlechaDer />
        <Nodo ic="grafico" t="Pedidos por día" sub="unidades de cada categoría" clave />
      </Paso>

      <Paso n={1}>
        <table className="ds-tabla">
          <thead>
            <tr className="grupo">
              <th colSpan={3}>de los pedidos</th>
              <th colSpan={4} className={nv}>+ se agrega por fecha</th>
            </tr>
            <tr>
              <th>fecha</th><th>categoría</th><th className="n">unidades × K</th>
              {agregadas.map(([ic, t]) => <th key={t} className={nv}><span><Icono n={ic} tam={20} />{t}</span></th>)}
            </tr>
          </thead>
          <tbody>
            {ds.cruce.map((r) => {
              const ev = r.ev !== '—';
              return (
                <tr key={r.f} className={ev ? 'evento' : ''}>
                  <td>{fechaCorta(r.f)}</td>
                  <td>tartas y huevo</td>
                  <td className="n"><b>{r.u}</b></td>
                  <td className={nv}>{ev ? <b>{r.ev}</b> : '—'}</td>
                  <td className={`${nv} n`}>{coma(r.tmax)}</td>
                  <td className={`${nv} n`}>{coma(r.lluvia)}</td>
                  <td className={`${nv} n`}>{r.meta == null ? '—' : coma(r.meta)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="ds-pie">Empresas, febrero de 2026. Meta: gasto de esa semana, como índice.</p>
      </Paso>
    </div>
  );
}

export const FLUJO: Diapo = {
  id: 'flujo', seccion: S, titulo: 'El flujo de trabajo', pasos: 2, Comp: Flujo,
  notas: (d) => `Este es el mapa de todo el trabajo y también de la presentación. Un solo comando corre seis etapas: datos, explorar, modelar, validar, explicar y decidir. Todo tiene tests (${d.dataset.nTests}) y los datos crudos nunca salen de la carpeta privada.`,
};

export const DATASET: Diapo = {
  id: 'dataset', seccion: S, titulo: 'El dataset: del export a la serie', pasos: 3, etapa: 1, Comp: Dataset,
  notas: (d) => `Los datos son ${d.dataset.nArchivos} exports mensuales del sistema de pedidos. Cada fila es un producto de un pedido: por ejemplo, una tarta de jamón y queso, con su cantidad. Sacamos teléfono y empresa, multiplicamos las cantidades por una constante secreta K y sumamos por día y categoría. Después, a cada día le pegamos el calendario, el clima y el gasto en Meta de esa semana. En el ejemplo se ve el lunes de carnaval: bajan las tartas. Esas columnas nuevas son las que el modelo usa para explicar la demanda.`,
};
