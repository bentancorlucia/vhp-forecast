// A. Apertura (3 diapositivas)
import { K, Paso, Periodo, useDatos, useVisto } from '../components/marca';
import { LineaDemanda, SerieDiaria } from '../charts/graficos';
import { PORTADA } from './portada';
import type { Diapo } from './tipos';

function Portada() {
  const { meta } = useDatos();
  const visto = useVisto(1);
  return (
    <section className="diapo portada">
      <Paso n={1} className="portada-arriba">
        <p className="portada-curso">{PORTADA.curso}</p>
        <div className="portada-creditos">
          <p className="portada-autoras">{PORTADA.integrantes}</p>
          <p className="portada-dato">{PORTADA.institucion} · {PORTADA.fecha}</p>
        </div>
      </Paso>
      <Paso n={1} demora={0.1}>
        <h1>Del pedido<span className="l2">al plato</span></h1>
      </Paso>
      <div className="portada-medio">
        <Paso n={1} demora={0.35}><p className="sub">{meta.subtitulo}</p></Paso>
      </div>
      {visto && <div className="portada-linea"><LineaDemanda w={1600} h={260} /></div>}
    </section>
  );
}

function Negocio() {
  const { meta } = useDatos();
  return (
    <div className="col" style={{ height: '100%', justifyContent: 'center', gap: 72 }}>
      <Paso n={0}>
        <p style={{ fontSize: 30, color: 'var(--tinta-70)', margin: 0 }}>
          VHP cocina <b style={{ color: 'var(--tinta)' }}>a demanda</b> · los insumos se compran <b style={{ color: 'var(--tinta)' }}>el sábado</b> para toda la semana
        </p>
      </Paso>
      <Paso n={0}>
        <div style={{ position: 'relative', display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', paddingTop: 66 }}>
          <div style={{ position: 'absolute', left: '6.25%', right: '6.25%', top: 66 + 9, height: 2, background: 'var(--tinta-12)' }} />
          <div style={{ position: 'absolute', left: '31.25%', right: '6.25%', top: 38, height: 18, borderTop: '2.5px solid var(--ambar)', borderLeft: '2.5px solid var(--ambar)', borderRight: '2.5px solid var(--ambar)', borderRadius: '8px 8px 0 0' }} />
          <div style={{ position: 'absolute', left: '25%', right: 0, top: 0, textAlign: 'center', fontSize: 19, color: 'var(--ambar)', fontWeight: 700 }}>{meta.horizonte} días de entregas a cubrir</div>
          {['Sáb', 'Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'].map((d, i) => {
            const compra = i === 0, dom = i === 1;
            return (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, position: 'relative' }}>
                <div style={{ width: 20, height: 20, borderRadius: '50%', background: compra ? 'var(--ambar)' : dom ? 'var(--fondo, #fdfbf5)' : 'var(--tinta)', border: dom ? '2px solid var(--tinta-12)' : 'none' }} />
                <div style={{ fontSize: 21, fontWeight: dom ? 400 : 700, color: dom ? 'var(--tinta-70)' : compra ? 'var(--ambar)' : 'var(--tinta)' }}>{d}</div>
                {compra && <div style={{ fontSize: 17, color: 'var(--ambar)', marginTop: -6 }}>se compra</div>}
              </div>
            );
          })}
        </div>
      </Paso>
      <Paso n={1}>
        <p className="fr" style={{ fontWeight: 600, fontSize: 68, lineHeight: 1.1, letterSpacing: '-0.02em', margin: 0, maxWidth: 1400 }}>
          ¿Qué hay que comprar para los próximos {meta.horizonte} días, para que <span style={{ color: 'var(--ambar)' }}>sobre o falte lo menos posible</span>?
        </p>
      </Paso>
    </div>
  );
}

function LosDatos() {
  const { meta } = useDatos();
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 360px', gap: 48, height: '100%', alignItems: 'center' }}>
      <Paso n={0}>
        <p className="chica" style={{ margin: '0 0 8px' }}>Viandas por día · línea gruesa: promedio semanal · fina: cada día</p>
        <SerieDiaria w={1000} h={590} />
        <Periodo>Días hábiles {meta.datosPeriodo} · unidades × K</Periodo>
      </Paso>
      <div className="col teoria-st">
        <Paso n={1}>
          <p className="st-def">Una <b>serie temporal</b> es una secuencia de observaciones <K t="\{y_t\}_{t=1}^{T}" /> ordenadas en el tiempo, a intervalos regulares.</p>
        </Paso>
        <Paso n={1} demora={0.1}>
          <p className="st-formula"><K t="y_t = T_t + S_t + \varepsilon_t" /></p>
          <dl className="st-comp">
            <dt><K t="T_t" /></dt><dd><b>tendencia</b>: el nivel de largo plazo</dd>
            <dt><K t="S_t" /></dt><dd><b>estacionalidad</b>: ciclos fijos (semana, año…)</dd>
            <dt><K t="\varepsilon_t" /></dt><dd><b>ruido</b>: lo que no se explica</dd>
          </dl>
        </Paso>
        <Paso n={2}>
          <p className="st-cierre"><b>Autocorrelación:</b> <K t={`y_t`} /> se parece a <K t={`y_{t-1}`} /> y a <K t={`y_{t-${meta.periodo}}`} />. Por eso el orden importa: se entrena con el pasado y se evalúa en el futuro.</p>
        </Paso>
      </div>
    </div>
  );
}

export const APERTURA: Diapo[] = [
  {
    id: 'portada', seccion: '', titulo: 'Portada', pasos: 2, propia: true, Comp: Portada,
    notas: () => 'Presentate y contá en una frase de qué va: pronosticar cuántas viandas se van a pedir la semana siguiente para saber qué comprar. Decí que es un caso real con datos del negocio, anonimizados.',
  },
  {
    id: 'negocio', seccion: 'Apertura', titulo: 'El negocio y la pregunta', sinTitulo: true, pasos: 2, Comp: Negocio,
    notas: (d) => `La cocina trabaja a demanda: cada día cocina lo que se entrega al día siguiente, así que no hay stock de platos. Los insumos, en cambio, se compran por adelantado: el sábado, para los ${d.meta.horizonte} días de la semana. Queremos predecir qué comprar para que sobre o falte lo menos posible.`,
  },
  {
    id: 'datos', seccion: 'Método', etapa: 2, titulo: 'Los pedidos como serie temporal', tituloRico: <>Los pedidos como <em className="resalte">serie temporal</em></>, pasos: 3, Comp: LosDatos,
    notas: (d) => `Una serie temporal es una secuencia de observaciones ordenadas en el tiempo, a intervalos regulares: acá, viandas por día. Se suele pensar como tendencia más estacionalidad más ruido; en Viandas la estación es de ${d.meta.periodo} días hábiles. Además tiene autocorrelación: hoy se parece a ayer y al mismo día de la semana pasada. Por eso el orden importa: se entrena con el pasado y se evalúa en el futuro.`,
  },
];

