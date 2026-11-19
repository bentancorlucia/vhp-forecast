import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import 'katex/dist/katex.min.css';
import './styles.css';
import { DatosCtx } from './components/marca';
import { Presentacion, VistaImprimir, VistaNotas } from './App';
import type { Datos } from './lib/tipos';

function Raiz() {
  const [datos, setDatos] = useState<Datos | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch('data/presentacion.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setDatos)
      .catch((e) => setError(`No se pudo leer data/presentacion.json (${e.message}). Corré "npm run datos".`));
  }, []);
  if (error) return <p style={{ padding: 40, fontSize: 20 }}>{error}</p>;
  if (!datos) return null;
  const q = new URLSearchParams(window.location.search);
  const Vista = q.has('notas') ? VistaNotas : q.has('imprimir') ? VistaImprimir : Presentacion;
  return <DatosCtx.Provider value={datos}><Vista /></DatosCtx.Provider>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><Raiz /></StrictMode>);
