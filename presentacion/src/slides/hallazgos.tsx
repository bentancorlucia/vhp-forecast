// D. Hallazgos (8) y E. Cierre (3). Cada hallazgo recuerda la métrica que usa.
import { Flecha, Nota, Paso, Periodo, Sello, useDatos } from '../components/marca';
import { AdsSemanal, Backtest, LineaDemanda, CurvaCosto, EventosForest, MixTemperatura, PerfilSemanal, RankingEmpate } from '../charts/graficos';
import { fechaLarga, num, pct, pctFrac, pctSigned, pval, signed } from '../lib/format';
import type { Diapo } from './tipos';

const S = 'Hallazgos';
function Patrones() {
  const { eda, meta } = useDatos();
  const ds = eda.diaSemana;
  const lunP = ds[0].particulares, sabE = ds[ds.length - 1].empresas;
  const fer = (s: string) => eda.efectos[`${s}|feriado_laborable`];
  const ver = eda.efectos['Total|verano'];
  return (
    <div className="patrones">
      <div className="col" style={{ position: 'relative', gap: 0 }}>
        <Paso n={0}><PerfilSemanal w={1010} h={610} /><Periodo>Pedidos de cada día relativos a la media del segmento (1 = un día promedio), {meta.datosPeriodo}</Periodo></Paso>
        <Paso n={1} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
          <Nota style={{ left: 250, top: 18 }}>el lunes los particulares piden {pctSigned((lunP - 1) * 100, 0)}</Nota>
          <Flecha de={[245, 50]} a={[132, 82]} curva={-0.3} />
        </Paso>
      </div>
      <div className="riel">
        <Paso n={2} className="dato">
          <span className="dato-n">{pctSigned(fer('Total').ef, 0)}</span>
          <span className="dato-t">feriado en que se abre</span>
          <span className="dato-d">empresas <b>{pctSigned(fer('Empresas').ef, 0)}</b> · particulares {pctSigned(fer('Particulares').ef, 0)}</span>
        </Paso>
        <Paso n={3} className="dato">
          <span className="dato-n">{pctSigned(ver.ef, 0)}</span>
          <span className="dato-t">verano (enero)</span>
          <span className="dato-d">IC [{pctSigned(ver.lo, 0)}; {pctSigned(ver.hi, 0)}] · estacionalidad, no quiebre</span>
        </Paso>
        <Paso n={4} className="dato dato-fin">
          <p>Empresas el sábado: {num(sabE, 2)} ×. Cada segmento se pronostica <b>por separado</b> y el plan de compras usa los segmentos.</p>
        </Paso>
        <Paso n={2} style={{ marginTop: 'auto' }}><Periodo>Regresión de log(y) con calendario, IC&nbsp;95&nbsp;%</Periodo></Paso>
      </div>
    </div>
  );
}

function PorQueLgbm() {
  const { total, meta } = useDatos();
  const [g, m2, m3] = total.metricas;
  const { particulares: sp, empresas: se } = total.segmentos;
  const razones = [
    { t: 'El menor error', d: <>Total: MASE <b>{num(g.mase, 3)}</b> y WAPE <b>{pctFrac(g.wape, 1)}</b>, primero de siete. Empresas: primero ({num(se.metricas[0].mase, 3)}). Particulares: {sp.metricas[0].nombre} queda apenas adelante ({num(sp.metricas[0].mase, 3)} contra {num(sp.metricas.find((m) => m.id === 'lgbm_directo')!.mase, 3)}; p&nbsp;=&nbsp;{num(sp.pPrimero ?? 1, 2)}).</> },
    { t: 'Nadie lo supera, pero tampoco se separa', d: <>SARIMA con calendario lo iguala (MASE {num(total.sarimaCal.mase, 3)}; p&nbsp;=&nbsp;{num(total.sarimaCal.p, 2)}). Es un <b>SARIMAX</b>: una regresión sobre el calendario cuyo error sigue un SARIMA. La ventaja de LightGBM <b>no</b> viene de ver el calendario.</> },
  ];
  return (
    <div className="col" style={{ height: '100%' }}>
      <Paso n={0} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <p className="pregunta" style={{ margin: 0 }}>Siete modelos, el mismo walk-forward: LightGBM es el que menos se equivoca.</p>
      </Paso>
      <div style={{ display: 'grid', gridTemplateColumns: '780px 1fr', gap: 64, flex: 1, alignItems: 'center' }}>
        <Paso n={0}>
          <RankingEmpate w={780} h={560} />
          <Periodo>Total de viandas, {g.n} días, backtest {meta.btPeriodo} · DM: {g.nombre} contra cada modelo</Periodo>
        </Paso>
        <div className="col" style={{ gap: 30 }}>
          <Paso n={1}><h2 style={{ margin: 0, paddingBottom: 12, borderBottom: '2px solid var(--ambar)' }}>Por qué lo elegimos</h2></Paso>
          {razones.map((r, i) => (
            <Paso key={r.t} n={i + 1} style={{ display: 'flex', gap: 20 }}>
              <span style={{ fontFamily: 'var(--f-titulo)', fontWeight: 700, color: 'var(--ambar)', fontSize: 44, lineHeight: 1, width: 34, flex: 'none' }}>{i + 1}</span>
              <div>
                <h3 style={{ margin: '2px 0 6px' }}>{r.t}</h3>
                <p style={{ fontSize: 20, margin: 0, color: 'var(--tinta-70)' }}>{r.d}</p>
              </div>
            </Paso>
          ))}
          <Paso n={2}>
            <div className="tarjeta crema" style={{ padding: '16px 22px' }}>
              <h3 style={{ fontSize: 22, margin: '0 0 6px' }}>Elegimos {g.nombre.split(' ')[0]} por el menor error, pero…</h3>
              <p style={{ fontSize: 18, margin: 0, lineHeight: 1.4 }}>…{m2.nombre} y {m3.nombre} andan parejo y el test no los separa.</p>
            </div>
          </Paso>
        </div>
      </div>
    </div>
  );
}

function BacktestTiempo() {
  const { total, meta } = useDatos();
  const g = total.metricas[0];
  return (
    <div className="col" style={{ height: '100%' }}>
      <Paso n={0} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="leyenda"><span><i style={{ background: 'var(--tinta)' }} />real</span><span><i style={{ background: 'var(--ambar)' }} />LightGBM</span><span><i style={{ background: 'var(--crema-osc)', height: 14 }} />intervalo 80 %</span><span>○ fuera del intervalo</span><span className="chica">(pasá el mouse)</span></div>
      </Paso>
      <div style={{ position: 'relative', display: 'flex', gap: 24, alignItems: 'center' }}>
        <Paso n={1}><Backtest w={1150} h={560} /><Periodo>Total de viandas × K, {meta.nOrigenes} semanas pronosticadas, backtest {meta.btPeriodo} · líneas verticales: cada sábado de origen</Periodo></Paso>
        <Paso n={2} style={{ textAlign: 'center' }}>
          <Sello valor={pctFrac(g.cob, 0)} sub="de los días dentro del intervalo 80 %" tam={220} />
          <p className="chica" style={{ marginTop: 16, maxWidth: 230 }}>Los círculos vacíos son los días que quedaron fuera.</p>
        </Paso>
      </div>
    </div>
  );
}

function ClimaMix() {
  const { mix, meta } = useDatos();
  const pe = mix.participacion.filter((x) => x.seg === 'empresas');
  const ll = (id: string) => num(pe.find((x) => x.id === id)!.logloss, 3);
  const carne = mix.temperatura.find((x) => x.seg === 'empresas' && x.cat === 'carne vacuna')!;
  return (
    <div className="patrones" style={{ gridTemplateColumns: '1fr 340px', gap: 72 }}>
      <div className="col" style={{ gap: 0 }}>
        <Paso n={0}>
          <p className="pregunta" style={{ margin: 0 }}>Con calor se pide <b>menos carne vacuna</b>.</p>
        </Paso>
        <Paso n={1} style={{ marginTop: 28 }}>
          <MixTemperatura w={960} h={470} seg="empresas" resaltar="carne vacuna" />
          <Periodo>Empresas: participación con calor ({num(mix.temps.calor, 1)} °C) − con frío ({num(mix.temps.frio, 1)} °C), en puntos porcentuales, {meta.datosPeriodo} · intervalo de confianza 95 % (si no cruza el 0, el cambio es significativo)</Periodo>
        </Paso>
      </div>
      <div className="riel" style={{ justifyContent: 'center', gap: 40 }}>
        <Paso n={2} className="dato">
          <span className="dato-n">{signed(carne.d, 1)} pp</span>
          <span className="dato-t">carne vacuna con calor</span>
          <span className="dato-d">la categoría que más cambia</span>
        </Paso>
        <Paso n={3} className="dato">
          <span className="dato-t" style={{ marginTop: 0 }}>¿Sirve para pronosticar?</span>
          <span className="dato-n">No</span>
          <span className="dato-d">Agregar el clima no baja el error: {ll('multinomial_clima')} con clima contra <b>{ll('media_4sem')}</b> sin él (log loss, menor es mejor)</span>
        </Paso>
        <Paso n={4} className="dato dato-fin">
          <p>Si hace calor, las últimas 4 semanas ya fueron de calor: el mix reciente <b>ya trae la estación</b>.</p>
          <Periodo>Backtest {meta.btPeriodo}</Periodo>
        </Paso>
      </div>
    </div>
  );
}

/** Esquema mínimo: contrafactual vs. observado, y una fecha falsa (placebo) antes del evento. */
function EsquemaEvento() {
  return (
    <svg width="320" height="160" viewBox="0 0 470 170" aria-hidden style={{ flex: 'none' }}>
      <line x1="110" x2="110" y1="18" y2="160" stroke="var(--tinta-45)" strokeDasharray="2 5" />
      <text x="116" y="28" fontSize="15" fill="var(--tinta-45)">placebo</text>
      <line x1="230" x2="230" y1="18" y2="160" stroke="var(--tinta-45)" strokeDasharray="5 5" />
      <text x="236" y="28" fontSize="15" fill="var(--tinta)">evento</text>
      <path d="M10,130 L40,118 L70,126 L100,108 L130,118 L160,100 L190,110 L230,96" fill="none" stroke="var(--tinta)" strokeWidth="2.5" />
      <path d="M230,96 L260,92 L290,99 L320,86 L350,93 L380,82 L405,88" fill="none" stroke="var(--tinta-45)" strokeWidth="2.5" strokeDasharray="7 6" />
      <path d="M230,96 L260,62 L290,70 L320,52 L350,60 L380,44 L405,50" fill="none" stroke="var(--ambar)" strokeWidth="3" />
      <text x="300" y="40" fontSize="15" fill="var(--tinta)">observado</text>
      <text x="300" y="134" fontSize="15" fill="var(--tinta)">contrafactual</text>
      <path d="M392,48 L392,84" stroke="var(--tinta)" strokeWidth="2" />
      <text x="398" y="71" fontSize="15" fontWeight="700" fill="var(--tinta)">efecto</text>
    </svg>
  );
}

function Eventos() {
  const { eventos, meta } = useDatos();
  const pl = (id: string, serie?: string) => eventos.find((e) => e.evento === id && (!serie || e.serie === serie))!;
  const ag = pl('agencia_meta');
  const sp = pl('suba_precio', 'viandas_particulares');
  const txt = { margin: 0, fontSize: 19, lineHeight: 1.4 };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 34 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1.25fr auto 1fr', gap: 36, alignItems: 'center', background: 'var(--crema-osc)', borderRadius: 16, padding: '18px 32px' }}>
        <Paso n={0} style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <EsquemaEvento />
          <p style={txt}>Comparamos lo observado con el <b>contrafactual</b>: un SARIMA entrenado solo con los días previos, lo que habría pasado sin el evento. La distancia es el <b>efecto</b>.</p>
        </Paso>
        <div style={{ width: 1, alignSelf: 'stretch', background: 'var(--tinta-12)' }} />
        <Paso n={1}>
          <h3 style={{ margin: '0 0 6px' }}>Prueba placebo</h3>
          <p style={txt}>Hacemos de cuenta que el evento fue antes, en una <b>fecha donde no pasó nada</b>, y medimos igual. Ahí el efecto tiene que dar 0. Si no da 0, el método inventa efectos y no le creemos.</p>
        </Paso>
      </div>
      <div className="grid2" style={{ flex: 1, minHeight: 0 }}>
        <Paso n={2} className="col" style={{ gap: 10, borderTop: '2px solid var(--tinta-12)', paddingTop: 16 }}>
          <h2 style={{ margin: 0, fontSize: 30 }}>Extras por vianda</h2>
          <div><EventosForest w={670} h={230} unidad="tasa" resaltar={['postres_web', 'panes_web']} /><Periodo>Punto = efecto · barra = IC 95 %: <b>si cruza el 0, el efecto no es seguro</b></Periodo></div>
          <p style={{ ...txt, marginTop: 8, borderLeft: '4px solid var(--ambar)', paddingLeft: 16 }}><b>Postres en la web: claro</b> (placebos con efecto: {pl('postres_web').sigPlac} de {pl('postres_web').nPlac}). <b>Panes: efecto chico, a confirmar:</b> {pl('panes_web').sigPlac} de {pl('panes_web').nPlac} placebos también dieron significativos.</p>
        </Paso>
        <Paso n={3} className="col" style={{ gap: 10, borderTop: '2px solid var(--tinta-12)', paddingTop: 16 }}>
          <h2 style={{ margin: 0, fontSize: 30 }}>Viandas de particulares</h2>
          <div><EventosForest w={670} h={230} unidad="pct" resaltar={['agencia_meta']} solo={['agencia_meta', 'influencer', 'suba_precio']} /><Periodo>Particulares, efecto medio en %, datos {meta.datosPeriodoPart}</Periodo></div>
          <p style={{ ...txt, marginTop: 8, borderLeft: '4px solid var(--oro)', paddingLeft: 16 }}>Suba de precio e influencer: cruzan el 0, <b>no se distinguen</b> (la suba, con solo {sp.nPlac} placebos, es preliminar). Agencia de Meta {pctSigned(ag.ef, 0)}: <b>cota superior</b>, mezclada con la vuelta del verano.</p>
        </Paso>
      </div>
    </div>
  );
}

function MetaAds() {
  const { ads } = useDatos();
  const rg = ads.regresion, gr = ads.granger;
  return (
    <div className="grid-6-4" style={{ gridTemplateColumns: '1.75fr 1fr', gap: 72 }}>
      <div className="col" style={{ gap: 0 }}>
        <Paso n={0}>
          <div className="leyenda"><span><i style={{ background: 'var(--ambar)' }} />gasto en Meta</span><span><i style={{ background: 'var(--tinta-45)' }} />clientes nuevos</span></div>
        </Paso>
        <Paso n={1}><AdsSemanal w={860} h={530} /><Periodo>Índice semanal (100 = media desde febrero), {fechaLarga(rg.desde)}–{fechaLarga(ads.semanaFin)}</Periodo></Paso>
      </div>
      <div className="riel" style={{ justifyContent: 'center', gap: 40, paddingTop: 0 }}>
        <Paso n={2} className="dato">
          <span className="dato-n">{pct(ads.cv, 1)}</span>
          <span className="dato-t">variación del gasto desde febrero</span>
          <span className="dato-d">El único cambio es el salto de enero a febrero (×{num(ads.escalon, 1)}), que coincide con el fin del verano.</span>
        </Paso>
        <Paso n={3} className="dato">
          <span className="dato-t" style={{ marginTop: 0 }}>Describe, pero no predice</span>
          <span className="dato-d" style={{ color: 'var(--tinta)' }}>Un gasto casi constante no anticipa nada, y su único salto se confunde con el verano.</span>
          <span className="dato-d" style={{ fontSize: 15, marginTop: 4 }}>elasticidad {signed(rg.coef, 2)} [{signed(rg.lo, 2)}; {signed(rg.hi, 2)}], p = {pval(rg.p)} · Granger p = {num(gr.p, 2)} → efecto no identificado</span>
        </Paso>
        <Paso n={4} className="dato dato-fin" style={{ borderTop: '2px solid var(--ambar)' }}>
          <p>Para medirlo, hay que variar el gasto <b>a propósito</b>, por ejemplo en semanas alternas.</p>
        </Paso>
      </div>
    </div>
  );
}

function PlanCompras() {
  const { plan, meta } = useDatos();
  const cs = meta.costos;
  const segs = ['particulares', 'empresas'] as const;
  const cats = plan.semana.filter((x) => x.seg === 'particulares').map((x) => x.cat);
  const fila = (seg: string, cat: string) => plan.semana.find((x) => x.seg === seg && x.cat === cat);
  const suma = (k: 'pron' | 'plan' | 'p90', seg?: string) => d3sum(plan.semana.filter((x) => !seg || x.seg === seg).map((x) => x[k]));
  const caro = plan.sensibilidad[plan.sensibilidad.length - 1];
  const pron = suma('pron');
  const extra = (n: number) => `+${num(((n / pron) - 1) * 100, 0)} %`;
  const semana = meta.semanaPlan.replace(/\/\d{4}$/, '');
  return (
    <div className="plan">
      <div className="col" style={{ gap: 0, minHeight: 0 }}>
        <Paso n={0}>
          <p className="pregunta" style={{ margin: 0, fontSize: 28 }}>Conviene comprar <b>cerca de lo esperado</b>: asegurarse no paga.</p>
          <p className="chica" style={{ margin: '6px 0 18px' }}><b>p</b> = en qué % de las semanas alcanza lo que se compra. Con p&nbsp;=&nbsp;50 alcanza 1 de cada 2 semanas; con p&nbsp;=&nbsp;90, 9 de cada 10. Para que alcance más seguido hay que comprar más.</p>
        </Paso>
        <Paso n={0} className="plan-ej">
          <div className="plan-caja">
            <span className="k">pronóstico</span>
            <span className="v">{num(pron)}</span>
            <span className="d">viandas para la semana</span>
          </div>
          <span className="flecha">→</span>
          <div className="plan-caja elegida">
            <span className="k">compra con p = {plan.pElegido}</span>
            <span className="v">{num(suma('plan'))}<small>{extra(suma('plan'))}</small></span>
            <span className="d">a veces sobra, a veces falta</span>
          </div>
          <span className="flecha">vs</span>
          <div className="plan-caja">
            <span className="k">compra con p = 90</span>
            <span className="v">{num(suma('p90'))}<small>{extra(suma('p90'))}</small></span>
            <span className="d">casi nunca falta, casi siempre sobra</span>
          </div>
        </Paso>
        <Paso n={0} style={{ marginTop: 26 }}>
          <h3 style={{ margin: 0, fontSize: 22 }}>Plata perdida por cada vianda vendida</h3>
          <p className="chica" style={{ margin: '2px 0 0', fontSize: '15px' }}>sobrantes + faltantes, simulado con las 12 semanas reales del 24/08 al 14/11/2026</p>
          <CurvaCosto w={860} h={320} pasoNota={0} />
        </Paso>
      </div>

      <div className="col" style={{ gap: 14, minHeight: 0 }}>
        <Paso n={1} className="col" style={{ gap: 10 }}>
          <h3 style={{ margin: 0, fontSize: 22 }}>¿Por qué no asegurarse?</h3>
          <div className="plan-porque">
            <div><div className="v">${cs.sobrante}</div><div className="d">tirar una vianda</div></div>
            <span className="mayor">&gt;</span>
            <div style={{ textAlign: 'right' }}><div className="v" style={{ color: 'var(--tinta-70)' }}>${cs.faltante}</div><div className="d">perder una venta</div></div>
          </div>
          <p className="chica" style={{ margin: 0, fontSize: '16px' }}>Tirar duele más: comprar de más no paga. El factor de p&nbsp;=&nbsp;{plan.pElegido} (×{num(plan.factor.empresas, 2)} en empresas, ×{num(plan.factor.particulares, 2)} en particulares) solo corrige que el modelo se quedó corto más veces de las que se pasó; <b>no es un margen de seguridad</b>. Si perder una venta costara <b>${caro.faltante}</b>, convendría p&nbsp;=&nbsp;{caro.p}.</p>
          <p className="plan-supuesto"><b>Supuesto:</b> no se consultó qué pasa en la práctica cuando falta un ingrediente (¿se cambia el plato?, ¿se compra en el día?). Los ${cs.faltante} son una estimación.</p>
        </Paso>

        <Paso n={2} className="ticket-envol">
          <div className="ticket">
            <div className="ticket-cab"><span>Comanda</span><span>{semana}</span></div>
            <div className="ticket-tit">Lista de la semana</div>
            <hr />
            <div className="ticket-fila cab"><span>vianda</span>{segs.map((s) => <span key={s} className="n">{s === 'particulares' ? 'part.' : 'emp.'}</span>)}</div>
            {cats.map((c) => (
              <div key={c} className="ticket-fila"><span>{c}</span>{segs.map((s) => <span key={s} className="n">{num(fila(s, c)?.plan)}</span>)}</div>
            ))}
            <hr />
            <div className="ticket-fila tot"><span>total</span>{segs.map((s) => <span key={s} className="n">{num(suma('plan', s))}</span>)}</div>
            <div className="ticket-pie">p = {plan.pElegido} · cantidades × K (secreta)</div>
          </div>
        </Paso>
      </div>
    </div>
  );
}

const d3sum = (v: number[]) => v.reduce((a, b) => a + b, 0);

// ---------------------------------------------------------------- E. Cierre
// Versión corta para la diapositiva; el detalle va en las notas y en decisiones.yaml.
const DEC_CORTA: Record<string, [string, string]> = {
  dias_habiles: ['Los días cerrados no existen', 'Un día cerrado no es demanda cero: se excluye.'],
  segmentos: ['Dos segmentos, dos modelos', 'Particulares y empresas tienen semanas opuestas.'],
  walk_forward: ['Backtest walk-forward', '12 semanas, reentrenando cada una, sin mirar el futuro.'],
  modelo_total: ['LightGBM', 'El menor error; SARIMA y ETS quedan cerca.'],
  costo_faltante: ['El faltante tiene costo', 'Sobrar duele más: comprar cerca del pronóstico.'],
  platos_a_ingredientes: ['Del plan a los ingredientes', 'El recetario convierte viandas en kilos.'],
};

function Decisiones() {
  const { decisiones } = useDatos();
  return (
    <div className="decisiones">
      {decisiones.map((d, i) => {
        const [titulo, frase] = DEC_CORTA[d.id] ?? [d.titulo, d.decision];
        return (
          <Paso key={d.id} n={i} className="decision">
            <span className="decision-n">{String(i + 1).padStart(2, '0')}</span>
            <span className="decision-tipo">{d.quien === 'Lucía' ? 'negocio' : 'técnica'}</span>
            <h3>{titulo}</h3>
            <p>{frase}</p>
          </Paso>
        );
      })}
    </div>
  );
}

function Limitaciones() {
  const { limitaciones } = useDatos();
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '28px 80px', alignContent: 'start', paddingTop: 4 }}>
      {limitaciones.map((l, k) => (
        <Paso key={l.titulo} n={k} style={{ borderTop: `2px solid ${k < 2 ? 'var(--ambar)' : 'var(--tinta-25)'}`, paddingTop: 14 }}>
          <h3 style={{ fontSize: 29, marginBottom: 6 }}>{l.titulo}</h3>
          <p style={{ fontSize: 20, lineHeight: 1.35, margin: 0 }}>{l.texto}</p>
          <p style={{ fontSize: 20, lineHeight: 1.35, margin: '6px 0 0', color: 'var(--tinta-70)' }}>{l.implica}</p>
        </Paso>
      ))}
    </div>
  );
}

function Conclusion() {
  const { total, plan, meta } = useDatos();
  const g = total.metricas[0];
  const p90 = plan.simulacion.find((x) => x.metodo === plan.elegido.metodo && x.p === 90)!;
  const frases = [
    <>La demanda de la semana se puede anticipar con un error del <b>{pctFrac(g.wape, 1)}</b>. LightGBM es el más preciso, pero SARIMA y ETS andan casi igual: <b>lo simple también sirve</b>.</>,
    <>El clima cambia <b>qué</b> se pide, no <b>cuánto</b>. De las acciones, solo postres y panes en la web tuvieron un efecto claro; Meta no se puede evaluar hasta <b>variar el gasto a propósito</b>.</>,
    <>Conviene comprar <b>cerca de lo esperado</b>: asegurarse el 90&nbsp;% cuesta <b>${num(p90.costo, 1)}</b> contra ${num(plan.elegido.costo, 1)} por vianda. El plan sale cada sábado, en kilos por ingrediente.</>,
  ];
  return (
    <section className="diapo" style={{ justifyContent: 'center' }}>
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 220, opacity: 0.55 }}><LineaDemanda w={1600} h={220} grosor={4} /></div>
      <h1 style={{ fontSize: 76, marginBottom: 10 }}>En tres frases</h1>
      <div className="col" style={{ gap: 24, marginTop: 14, maxWidth: 1080, marginBottom: 160 }}>
        {frases.map((f, i) => (
          <Paso key={i} n={i}><p style={{ fontSize: 31, lineHeight: 1.35, margin: 0, display: 'flex', gap: 22 }}><span style={{ fontFamily: 'var(--f-titulo)', fontWeight: 700, color: 'var(--ambar)', fontSize: 46, lineHeight: 1 }}>{i + 1}</span><span>{f}</span></p></Paso>
        ))}
        <Paso n={2}><Periodo>Backtest {meta.btPeriodo}; datos {meta.datosPeriodo}</Periodo></Paso>
      </div>
      <Paso n={3} style={{ position: 'absolute', right: 96, bottom: 70 }}>
        <h1 style={{ fontSize: 120, fontStyle: 'italic', fontWeight: 500 }}>¿Preguntas?</h1>
      </Paso>
    </section>
  );
}

export const HALLAZGOS: Diapo[] = [
  { id: 'patrones', seccion: S, titulo: 'Patrones: dos semanas opuestas', pasos: 5, Comp: Patrones,
    notas: (d) => `Los particulares piden sobre todo el lunes: ${num(d.eda.diaSemana[0].particulares, 2)} veces su media. Las empresas casi no piden el sábado. En los feriados en que se abre, las empresas caen mucho más porque las oficinas cierran. Y enero cae por el verano. Por eso pronosticamos cada segmento por separado.` },
  { id: 'por-que-lgbm', seccion: 'Método', titulo: 'Por qué LightGBM', pasos: 3, Comp: PorQueLgbm,
    notas: (d) => `Comparamos siete modelos en las mismas ${d.meta.nOrigenes} semanas. Elegimos LightGBM porque tiene el menor error en el Total, MASE ${num(d.total.metricas[0].mase, 3)} y WAPE ${pctFrac(d.total.metricas[0].wape, 1)}, también en la ventana anterior y en empresas; en particulares ETS queda apenas adelante, sin diferencia significativa. Siendo honestas: con Diebold-Mariano no se separa de ${d.total.metricas[1].nombre} ni de ${d.total.metricas[2].nombre}. Probamos además darle el calendario a SARIMA. Eso se llama SARIMAX: una regresión sobre las variables de calendario cuyo error sigue un SARIMA; como el calendario se conoce de antemano, se puede usar para pronosticar. Y lo iguala: MASE ${num(d.total.sarimaCal.mase, 3)}. O sea que la ventaja no viene del calendario. La media móvil gana más días, ${d.total.dmLgbm.find((x) => x.m2 === 'media_movil_4sem')!.gana2} contra ${d.total.dmLgbm.find((x) => x.m2 === 'media_movil_4sem')!.gana1}, pero cuando pierde, pierde por más. Nadie lo supera, pero tampoco se separa.` },
  { id: 'backtest', seccion: 'Método', titulo: 'El backtest en el tiempo', pasos: 3, Comp: BacktestTiempo,
    notas: (d) => `Así se ve semana a semana: la línea oscura es lo real, la ámbar el pronóstico y la banda el intervalo del 80 %. Los círculos vacíos son los días que quedaron afuera. El peor día es el lunes ${fechaLarga(d.meta.diaIncompleto)}, que tiene un export incompleto; sacarlo no cambia el ranking.` },
  { id: 'clima', seccion: S, titulo: 'El clima cambia qué se pide', pasos: 5, Comp: ClimaMix,
    notas: () => 'Con calor se pide menos carne vacuna, sobre todo en empresas, y el intervalo no toca el cero. Pero para pronosticar a una semana el clima no ayuda: la log loss del modelo con clima es igual o peor que usar el mix de las últimas cuatro semanas, que ya trae la estación.' },
  { id: 'eventos', seccion: S, titulo: 'Efecto de los eventos', pasos: 4, Comp: Eventos,
    notas: (d) => `Para medir un evento entrenamos un SARIMA solo con lo anterior y lo proyectamos: eso es lo que habría pasado sin el evento, y la diferencia con lo observado es el efecto. Para confiar, repetimos en fechas falsas, como un placebo: ahí no pasó nada y debería dar cero. Poner postres en la web subió claramente los postres por vianda, y ningún placebo dio efecto. Con los panes el efecto es chico y hay que confirmarlo: ${d.eventos.find((e) => e.evento === 'panes_web')!.sigPlac} de ${d.eventos.find((e) => e.evento === 'panes_web')!.nPlac} placebos también dieron significativos. La suba de precio, ahora con ocho semanas, y el influencer no se distinguen de cero; la suba sigue preliminar porque entran pocos placebos. La agencia de Meta da un efecto grande, pero coincide con la vuelta del verano y no tenemos un febrero anterior para separarlo: lo tomamos como cota superior.` },
  { id: 'meta-ads', seccion: S, titulo: 'Meta Ads: el gasto casi no varía', pasos: 5, Comp: MetaAds,
    notas: () => 'Para medir el efecto de algo, ese algo tiene que moverse. Desde febrero, y hasta noviembre, el gasto casi no cambia; el movimiento grande está en enero a febrero, mezclado con el verano. La regresión y Granger sobre el gasto no encuentran nada. La recomendación es variar el gasto a propósito.' },
  { id: 'plan', seccion: S, titulo: 'Plan de compras', pasos: 3, Comp: PlanCompras,
    notas: (d) => `La compra es el pronóstico de la semana por un percentil de los errores recientes. Probamos varios percentiles y el más barato fue p = ${d.plan.pElegido}: conviene comprar cerca de lo esperado. El factor de p = ${d.plan.pElegido}, por ${num(d.plan.factor.empresas, 2)} en empresas y por ${num(d.plan.factor.particulares, 2)} en particulares, solo corrige que el modelo se quedó corto más veces de las que se pasó; no es un margen de seguridad. Asegurarse el 90 % cuesta mucho más por vianda. La teoría da el cuantil ${num(d.meta.costos.faltante / (d.meta.costos.faltante + d.meta.costos.sobrante), 2)} y la simulación elige ${d.plan.pElegido} porque la curva de costo es casi plana alrededor de ese punto. El sobrante y el faltante se ponderan por la proporción de viandas XL. Con empresas hasta noviembre p pasó de 45 a 50, casi empatados en costo. Si perder un cliente costara más, p sube. A la derecha, el plan real para la semana siguiente, con datos de los dos segmentos hasta el sábado anterior.` },
];

export const CIERRE: Diapo[] = [
  { id: 'decisiones', seccion: 'Cierre', titulo: 'Decisiones clave y por qué', pasos: 6, Comp: Decisiones,
    notas: () => 'Estas son las decisiones que más pesan. Algunas son del negocio, como que los días cerrados no existen o cómo se valora el faltante; otras son técnicas, como validar con walk-forward. Todas están documentadas con su porqué en el repo.' },
  { id: 'limitaciones', seccion: 'Cierre', titulo: 'Lo que estos datos no permiten decir', pasos: 6, Comp: Limitaciones,
    notas: () => 'Lo más importante: sin la hora de creación del pedido no podemos usar lo ya confirmado; faltan los pedidos que entran por fuera del sistema; Meta no se puede medir sin variar el gasto ni saber de qué anuncio viene cada pedido; y la suba de precio y la baja de pauta tienen pocas semanas. Sobre p: no es data leakage, porque cada plan usa solo semanas ya terminadas; pero p se elige con el mismo backtest en el que se informa el costo, así que ese costo es algo optimista. Las acciones para resolverlas están en la hoja de ruta que vimos.' },
  { id: 'conclusion', seccion: 'Cierre', titulo: 'Conclusión', pasos: 4, propia: true, Comp: Conclusion,
    notas: () => 'Cerrá con las tres frases, despacio. Uno: se puede pronosticar bien, y un modelo simple compite con el mejor. Dos: qué mueve la demanda, qué acción funcionó y qué hay que hacer para medir Meta. Tres: comprar cerca del pronóstico es lo más barato, y el plan ya sale listo cada sábado. Después, abrí a preguntas.' },
];

