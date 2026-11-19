// Diapositivas "En código": fragmentos reales del repo (los extrae el script con ast) + explicación paso a paso.
import type { ReactNode } from 'react';
import { Codigo, Paso, useDatos, usePaso } from '../components/marca';
import type { Datos } from '../lib/tipos';
import type { Diapo } from './tipos';

interface Marca { busca: string[]; titulo: string; texto: (d: Datos) => ReactNode }

function DiapoCodigo({ id, intro, marcas, ancho = 930 }: { id: string; intro: (d: Datos) => ReactNode; marcas: Marca[]; ancho?: number }) {
  const d = useDatos();
  const { paso } = usePaso();
  const c = d.codigo[id];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `${ancho}px 1fr`, gap: 40, height: '100%', alignItems: 'start' }}>
      <Paso n={0}>
        <Codigo archivo={c.archivo} codigo={c.codigo} ancho={ancho} marcas={marcas.map((m, i) => ({ busca: m.busca, desde: i + 1 }))} />
      </Paso>
      <div className="col" style={{ gap: marcas.length > 4 ? 8 : 14 }}>
        <Paso n={0}><p style={{ fontSize: marcas.length > 4 ? 19 : 22, color: 'var(--tinta-80)' }}>{intro(d)}</p></Paso>
        {marcas.map((m, i) => {
          const activa = paso === i + 1 || (paso >= 99);
          return (
            <Paso key={m.titulo} n={i + 1}>
              <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', opacity: activa || paso < i + 1 ? 1 : 0.5, transition: 'opacity .4s' }}>
                <span className="cifra" style={{ fontSize: 40, color: activa ? 'var(--ambar)' : 'var(--tinta-45)', width: 34, flex: 'none' }}>{i + 1}</span>
                <div>
                  <h3 style={{ fontSize: marcas.length > 4 ? 21 : 23, margin: '2px 0 4px' }}>{m.titulo}</h3>
                  <p style={{ fontSize: marcas.length > 4 ? 17 : 19, margin: 0, lineHeight: 1.4 }}>{m.texto(d)}</p>
                </div>
              </div>
            </Paso>
          );
        })}
      </div>
    </div>
  );
}

/** La cuenta de la compra (diapo "La compra, en una cuenta"), con los factores que explica esta diapo resaltados. */
export function Cuenta({ activos }: { activos: number[] }) {
  const partes = ['pronóstico', 'participación', 'colchón'];
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 19, color: 'var(--tinta-45)', whiteSpace: 'nowrap' }}>
      {partes.map((t, i) => (
        <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {i > 0 && <span>×</span>}
          <span style={activos.includes(i) ? { background: 'var(--ambar)', color: 'var(--blanco)', borderRadius: 6, padding: '2px 10px', fontWeight: 700 } : { padding: '2px 0' }}>{t}</span>
        </span>
      ))}
      <span>= compra</span>
    </span>
  );
}

const C = (id: string, intro: (d: Datos) => ReactNode, marcas: Marca[], ancho?: number) => () => <DiapoCodigo id={id} intro={intro} marcas={marcas} ancho={ancho} />;
const S = (s: string) => s; // marca visual de "sección" para leer mejor la lista de abajo

export const COD_BASELINES: Diapo = {
  id: 'cod-baselines', seccion: S('Marco teórico'), titulo: 'En código: los modelos de referencia', pasos: 4,
  Comp: C('baselines', (d) => <>Cada modelo de referencia es una línea de numpy. <code>y</code> es la serie hasta el sábado de origen y <code>H</code>, el horizonte: {d.meta.horizonte} días, de lunes a sábado.</>, [
    { busca: ['np.repeat(y[-1], H)'], titulo: 'Naive', texto: () => 'Repite el último valor, el del sábado, para los H días. Ignora que cada día de la semana tiene su propio nivel: el lunes queda igual al sábado.' },
    { busca: ['y[-H:].copy()'], titulo: 'Naive estacional', texto: () => 'Toma los últimos H días tal cual: el lunes que viene será como el lunes pasado. Es la vara contra la que mide el MASE.' },
    { busca: ['reshape(semanas, H)', 'w.mean(axis=0)'], titulo: 'Media móvil de 4 semanas', texto: () => 'Arma una tabla de 4 filas (semanas) por H columnas (días) y promedia cada columna: el lunes pronosticado es el promedio de los últimos 4 lunes.' },
  ]),
  notas: () => 'Mostrá que lo simple es realmente simple: una línea por modelo. El truco de la media móvil es el reshape: arma una tabla semanas por días y promedia columnas, así cada día se compara con el mismo día de otras semanas.',
};

export const COD_SARIMA: Diapo = {
  id: 'cod-sarima', seccion: 'Marco teórico', titulo: 'En código: SARIMA elegido por AIC', pasos: 5,
  Comp: C('sarima', () => <>Con statsmodels. Se prueban varios SARIMA y se queda el de menor AIC; <code>hist</code> tiene solo los días hasta el origen.</>, [
    { busca: ['GRILLA ='], titulo: 'La grilla', texto: () => '36 combinaciones de órdenes: p y q entre 0 y 2, P y Q entre 0 y 1. Las diferencias quedan fijas: d = 0 y D = 1 (una diferencia semanal), según el test ADF.' },
    { busca: ['np.log('], titulo: 'Sobre el logaritmo', texto: () => 'En días de mucha demanda la serie varía más. Con el log esa variación se vuelve pareja y los errores pasan a ser relativos.' },
    { busca: ['Parallel(', 'validos ='], titulo: 'Ajustar todas', texto: () => 'Se ajustan las 36 en paralelo. Las que no convergen devuelven None o un AIC infinito, y se descartan.' },
    { busca: ['min(validos'], titulo: 'Quedarse con la mejor', texto: () => 'Gana la de menor AIC: el mejor ajuste con la menor cantidad de parámetros. La búsqueda se repite en cada sábado, así que elegir el modelo tampoco usa datos futuros.' },
  ]),
  notas: () => 'La grilla son todas las combinaciones chicas de órdenes. Se ajustan todas, se tiran las que fallan y se queda la de menor AIC. Lo importante: esto pasa en cada sábado del backtest, con los datos que había ese día.',
};

export const COD_LGBM: Diapo = {
  id: 'cod-lgbm', seccion: 'Método', etapa: 3, titulo: 'En código: la serie como tabla', pasos: 5,
  Comp: C('lgbm', () => <>Para usar un modelo de tablas, cada sábado <code>o</code> se convierte en una fila de variables. LightGBM y el MLP usan exactamente las mismas.</>, [
    { busca: ['nivel = y['], titulo: 'El nivel', texto: () => 'La media de la última semana. Todas las variables se dividen por él, así el modelo aprende la forma de la semana y no el tamaño: sigue sirviendo aunque la demanda crezca.' },
    { busca: ['v = y[o - LAGS', 'lag{k}'], titulo: 'Los rezagos', texto: () => 'Los últimos 18 días (tres semanas), dados vuelta para que lag0 sea el sábado, lag1 el viernes y así hacia atrás.' },
    { busca: ['mm_sem_ant', 'mm_3sem'], titulo: 'Medias móviles', texto: () => 'El promedio de la semana anterior y el de las últimas tres. Comparados con el nivel, indican si la demanda viene subiendo o bajando.' },
    { busca: ['LGBMRegressor', 'm.predict(Xf) * nivel'], titulo: 'Estrategia directa', texto: () => 'Un solo LightGBM pronostica los seis días: el día a pronosticar es una columna más. Predice en escala relativa y se multiplica por el nivel para volver a viandas.' },
  ]),
  notas: () => 'Este es el corazón del modelo ganador. Dividir por el nivel de la última semana hace que el modelo aprenda la forma de la semana, no el tamaño, y eso funciona aunque la demanda crezca. Después, un solo LightGBM con el horizonte como columna.',
};

export const COD_WALK: Diapo = {
  id: 'cod-walk', seccion: 'Método', etapa: 4, titulo: 'En código: cortar sin mirar el futuro', pasos: 4,
  Comp: C('walk_forward', () => <>En cada sábado de origen los datos se cortan en dos: lo que se sabía ese día y lo que hay que pronosticar.</>, [
    { busca: ['hist = grilla.loc'], titulo: 'hist', texto: () => 'Todos los días hasta el sábado de origen, incluido. Es lo único con lo que se entrena.' },
    { busca: ['fut = grilla.loc'], titulo: 'fut, sin la respuesta', texto: () => 'Los 6 días siguientes, con el calendario (feriados, verano) pero sin las columnas de demanda: el modelo no puede ver la respuesta.' },
    { busca: ['def escala_mase', 'y[H:] - y[:-H]', 'nanmean'], titulo: 'La escala del MASE', texto: () => 'Resta cada día con el mismo día de la semana anterior y promedia los errores absolutos: es lo que erraría el naive estacional. Sale de hist, sin mirar el futuro.' },
  ]),
  notas: () => 'La fuga de información se evita acá: el futuro se entrega sin la columna de la respuesta, y todo lo demás, incluida la escala del MASE, se calcula con lo que había hasta el sábado. Hay tests que verifican que ningún split usa fechas de test.',
};

export const COD_INTERVALO: Diapo = {
  id: 'cod-intervalo', seccion: 'Método', etapa: 4, titulo: 'En código: el intervalo 80 %', pasos: 4,
  Comp: C('intervalo', (d) => <>El intervalo de cada modelo sale de sus propios errores en las {d.meta.semanasIntervalo} semanas anteriores, sin suponer ninguna distribución.</>, [
    { busca: ['previos = res', '& (res["origen"] >='], titulo: 'Solo semanas terminadas', texto: () => 'Solo pronósticos cuya semana ya terminó: el origen más reciente que entra es el de hace 7 días, que cierra justo en este sábado.' },
    { busca: ['np.percentile(d["y"] / d["q0.5"], [10, 90])'], titulo: 'Percentiles 10 y 90', texto: () => 'Para cada modelo se calcula real ÷ pronóstico en esas semanas. El percentil 10 refleja las veces que el pronóstico se pasó y el 90, las que se quedó corto.' },
    { busca: ['actual.loc[fil, "q0.1"]', 'actual.loc[fil, "q0.9"]'], titulo: 'Multiplicar', texto: () => 'Los límites son el pronóstico nuevo por esos dos factores. Como son proporciones, el intervalo es más ancho cuando la demanda es mayor.' },
  ]),
  notas: () => 'El intervalo es empírico: miramos cuánto se equivocó el mismo modelo en las semanas que ya terminaron, en proporción, y aplicamos esos percentiles al pronóstico nuevo. Es el mismo método para todos los modelos.',
};

export const COD_PLAN: Diapo = {
  id: 'cod-plan', seccion: 'Cómo se usa', titulo: 'En código: el colchón de la compra', pasos: 4,
  Comp: C('plan', () => <>La misma idea que el intervalo, pero con el total de la semana por categoría y con el percentil que menos cuesta en vez de uno fijo.</>, [
    { busca: ['r=d["y"] / d[metodo]'], titulo: 'El error como cociente', texto: () => 'Para cada semana y categoría ya terminadas, real ÷ pronóstico. Un 1,10 significa que se vendió 10 % más de lo pronosticado.' },
    { busca: ['groupby(por)', 'np.percentile(x["r"], p)'], titulo: 'Juntar el segmento', texto: (d) => `Se juntan los errores de las ${d.meta.nCategorias} categorías de cada segmento, porque una sola tiene pocos. El percentil p de esos cocientes es el factor que multiplica la compra.` },
    { busca: ['def elegir_p', 'sort_values(["costo_por_vianda"', 'iloc[0]'], titulo: 'Elegir p', texto: () => 'Se ordena por costo simulado por vianda (sobrante + faltante) y se toma el primero. Si dos empatan, gana el p más chico: el colchón menor.' },
  ]),
  notas: () => 'El plan reutiliza la idea del intervalo: el error como cociente, el percentil como colchón. La única diferencia es que el percentil no se fija en 80: se elige el que menos cuesta en la simulación.',
};

export const COD_MODELO: Diapo = {
  id: 'cod-modelo', seccion: 'Cómo se usa', titulo: 'En código: los dos primeros factores', pasos: 5,
  Comp: C('modelo_final', () => <><Cuenta activos={[0, 1]} /><span style={{ display: 'block', marginTop: 12 }}>Recibe un sábado y devuelve el pronóstico diario de la semana siguiente, por segmento y categoría.</span></>, [
    { busca: ['hist = G[uid]', 'ev.partir'], titulo: 'Cortar en el sábado', texto: () => 'Por segmento: hist hasta el sábado; fut con los días a pronosticar y su calendario.' },
    { busca: ['f_seg = lgbm.directo', 'sq = f_seg(hist, fut)'], titulo: 'Pronosticar el total', texto: () => 'LightGBM directo, con calendario, pronostica el total diario del segmento: es más estable que cada categoría.' },
    { busca: ['P = mx.media_4sem', 'unidades_categoria'], titulo: 'Repartir por categoría', texto: () => 'Total × participación de cada categoría ese día de la semana en las últimas 4 semanas. Suman el total.' },
    { busca: ['naive_estacional, y'], titulo: 'Guardar para comparar', texto: () => 'También el naive estacional y lo real: con eso se elige el colchón (próxima diapo).' },
  ], 900),
  notas: () => 'Este es el código de las etapas dos y tres. Para cada segmento corta los datos en el sábado, LightGBM pronostica el total diario y ese total se reparte entre categorías con la participación de las últimas cuatro semanas, mismo día de la semana. Además guarda el naive estacional y lo que realmente se vendió, que es lo que usamos para elegir el colchón.',
};
