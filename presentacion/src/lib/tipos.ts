// Forma de public/data/presentacion.json (lo escribe scripts/exportar_datos.py).

export interface Pred { f: string; o: string; h: number; y: number; lo: number; m: number; hi: number }
export interface Metrica { id: string; nombre: string; n: number; mae: number; mase: number; wape: number; cob: number }
export interface Efecto { ef: number; lo: number; hi: number; p: number; dias: number }
export interface Decision { id: string; fase: string; titulo: string; decision: string; porque: string; quien: string }
export interface PlanFila { metodo: string; p: number; cob: number; sob: number; fal: number; costo: number; elegido?: boolean }
export interface Evento {
  evento: string; nombre: string; serie: string; serieNombre: string; unidad: 'pct' | 'tasa';
  desde: string; hasta: string; dias: number; ef: number; lo: number; hi: number; orden: string; nPlac: number; sigPlac: number;
  pPlac: number | null; emd: number | null;
}

export interface Datos {
  meta: {
    titulo: string; subtitulo: string; desde: string; hasta: string; datosPeriodo: string; diasHabiles: number;
    periodo: number; horizonte: number; btDesde: string; btHasta: string; btPeriodo: string; origenes: string[];
    nOrigenes: number; diasBacktest: number; semanasIntervalo: number;
    costos: { sobrante: number; faltante: number; sobranteXL: number; faltanteXL: number };
    finEmpresas: string; hastaParticulares: string; datosPeriodoPart: string; diasHabilesPart: number;
    percentiles: number[]; categorias: string[]; nCategorias: number; partParticulares: number; logo: boolean; semanaPlan: string; diaIncompleto: string; variablesModelo: string;
  };
  dataset: {
    columnas: string[]; nArchivos: number; tipos: string[]; nPlatos: number; filasProcesadas: number;
    muestra: { f: string; seg: string; cat: string; u: number }[];
    cruce: { f: string; u: number; ev: string; tmax: number; lluvia: number; meta: number | null }[];
    climaVars: string[]; climaDias: number; feriadosNoLab: number; feriadosLab: number; calVars: string[];
    semanasMeta: number; nTests: number;
  };
  serie: { f: string; p: number; e: number | null; fer: number; ver: number }[];
  eda: {
    stl: { f: string; y: number; t: number; s: number; r: number }[];
    autocorr: Record<'nivel' | 'dif', { acf: number[]; pacf: number[]; n: number }>;
    diaSemana: { dia: string; total: number; particulares: number; empresas: number }[];
    efectos: Record<string, Efecto>;
    estacionariedad: { t: string; n: number; p: number; c: string }[];
    rho: { cat: string; rho: number; p: number; part: number }[];
  };
  total: {
    metricas: Metrica[];
    dm: { m1: string; m2: string; n1: string; n2: string; dm: number; p: number; mejor: string }[];
    ljungBox: { modelo: string; rezago: number; stat: number; p: number }[];
    pred: Record<string, Pred[]>;
    sarimaUltimo: string;
    cobIC: { k: number; n: number; lo: number; hi: number };
    dmLgbm: { m2: string; n2: string; p: number; gana1: number; gana2: number; err1: number; err2: number }[];
    segmentos: Record<string, { metricas: { id: string; nombre: string; mase: number; wape: number }[]; pPrimero: number | null }>;
    sarimaCal: { mase: number; wape: number; maseLgbm: number; p: number };
    ejemplo: {
      fecha: string;
      modelos: Record<string, { y: number; yhat: number; lo: number; hi: number; escala: number }>;
      semana: { dias: { f: string; y: number; yhat: number; lo: number; hi: number }[]; mae: number; wape: number; escala: number; mase: number; cubiertos: number };
    };
  };
  mix: {
    temperatura: { seg: string; cat: string; frio: number; calor: number; d: number; lo: number; hi: number }[];
    temps: { calor: number; frio: number };
    participacion: { seg: string; id: string; metodo: string; logloss: number; mae_pp: number }[];
    unidades: { nivel: string; id: string; metodo: string; mase: number; wape: number; cob: number }[];
  };
  eventos: Evento[];
  ads: {
    semanal: { s: string; g: number; c: number; k: number | null; ver: number }[];
    clics: { coef: number; lo: number; hi: number; p: number; r2: number; semanas: number; desde: string; hasta: string; cv: number; grangerF: number; grangerP: number };
    campania: { coef: number; lo: number; hi: number; p: number; semanas: number };
    cv: number; cvDesde: string; cvHasta: string; escalon: number; semanaFin: string;
    regresion: { coef: number; lo: number; hi: number; p: number; semanas: number; corr: number; desde: string; hasta: string };
    granger: { F: number; p: number; rezagos: number; semanas: number; desde: string; hasta: string };
  };
  plan: {
    curva: PlanFila[]; simulacion: PlanFila[]; sensibilidad: { faltante: number; p: number; costo: number }[];
    semana: { seg: string; cat: string; pron: number; plan: number; p80: number; p90: number }[];
    pElegido: number; elegido: PlanFila; pCostosFijos: number; pAntes: number; periodo: string;
    xl: Record<string, number>; hasta: Record<string, string>; factor: Record<string, number>;
  };
  compras: {
    semana: string; ingredientes: number; proveedores: number; sinReceta12: number; sinRecetaSemana: number;
    platosSinReceta: number; ratioPlan: number; ratioP90: number; gramosGuarnicion: number; factorXL: number;
    familias: { familia: string; pct: number; unid: number }[];
  };
  decisiones: Decision[];
  limitaciones: { titulo: string; texto: string; implica: string; fuente: string }[];
  futuro: string[];
  figuras: string[];
  codigo: Record<string, { archivo: string; codigo: string }>;
}
