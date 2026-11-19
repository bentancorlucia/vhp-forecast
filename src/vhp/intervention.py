"""Fase 7: efecto de eventos por contrafactual (gancho 1).

Para cada evento y serie:
1. Se entrena SOLO con los días anteriores al evento: el SARIMA de
   `models/sarimax.py` (misma grilla de órdenes (p,0,q)(P,1,Q)[6], elegida por
   AIC en el pre-período, statsmodels) más las exógenas de calendario, pero SIN
   constante: con D = 1 la constante es una deriva semanal que, proyectada 4-8
   semanas, sesga el contrafactual (con ella 2 de 3 placebos de la agencia de
   Meta daban -15/-20 % significativos; sin ella, ninguno). Las viandas van en
   log; las tasas por vianda, en nivel.
2. Se simulan 1000 caminos del período posterior (semilla 42): es el
   contrafactual, lo que se esperaba sin el evento.
3. Efecto = observado − contrafactual. Se reporta la media por día abierto
   (observado, contrafactual, efecto) y el efecto relativo en %, con
   intervalo 95 % de los caminos simulados. El intervalo incluye la
   incertidumbre de los shocks, no la de los parámetros (queda algo angosto).
4. Placebo: lo mismo con fechas falsas anteriores al evento, cuya ventana
   posterior no toca ningún evento real. Si los placebos también dan efecto,
   el método no es confiable. p-placebo = (1 + #|placebo| ≥ |real|) / (n + 1).
5. Efecto mínimo detectable (EMD) = 2,8 × desvío de los efectos placebo: con un test
   bilateral al 5 % y potencia 80 % (1,96 + 0,84 = 2,8), un efecto menor que eso no se
   distingue del ruido del método en esa serie y ese largo de ventana. Sirve sobre todo
   para los eventos con pocas semanas posteriores (baja de pauta de noviembre 2026).

Datos públicos (unidades × K): el efecto relativo y las tasas por vianda no
dependen de K; las unidades absolutas sí (van × K).
"""
from __future__ import annotations

import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402
from statsmodels.tsa.statespace.sarimax import SARIMAX  # noqa: E402

from vhp import eda  # noqa: E402
from vhp import evaluate as ev  # noqa: E402
from vhp.config import RAIZ, cargar_config, ruta  # noqa: E402
from vhp.models.comun import SEMILLA, columnas_variables  # noqa: E402
from vhp.models.sarimax import GRILLA  # noqa: E402
from vhp.nombres import nombre  # noqa: E402

RUTA_EVENTOS = RAIZ / "config" / "eventos.yaml"
EN_LOG = {"viandas_particulares": True}
H = 6


# --------------------------------------------------------------------- datos
def cargar_eventos(ruta_yaml=RUTA_EVENTOS) -> dict:
    with open(ruta_yaml, encoding="utf-8") as f:
        return yaml.safe_load(f)


def series_diarias(diarias: pd.DataFrame) -> pd.DataFrame:
    """Viandas de particulares y tasas de extras por vianda, por fecha (días con ventas)."""
    p = diarias[diarias["segmento"] == "particulares"]
    u = p.pivot_table(index="fecha", columns="tipo_producto", values="unidades", aggfunc="sum").fillna(0)
    out = pd.DataFrame({"viandas_particulares": u["Vianda"],
                        "tasa_postre_particulares": u["Postre"] / u["Vianda"],
                        "tasa_pan_particulares": u["Pan"] / u["Vianda"],
                        "tasa_extras_particulares": (u["Postre"] + u["Pan"]) / u["Vianda"]})
    out.index = pd.to_datetime(out.index)
    return out


def grillas(cfg: dict | None = None) -> dict[str, pd.DataFrame]:
    cfg = cfg or cargar_config()
    d = eda.cargar_datos()
    s = series_diarias(d["diarias"]).reindex(d["cal"].index)
    # Clientes nuevos y pedidos de clientes que ya compraron, por día (particulares, × K).
    # En nivel, no en log: hay días con 0 (4 en cada serie, 06/05/2025–14/11/2026).
    cl = pd.read_csv(ruta("processed", cfg) / "particulares_diario.csv", parse_dates=["fecha"]).set_index("fecha")
    s["clientes_nuevos_particulares"] = cl["clientes_nuevos"].reindex(s.index)
    s["pedidos_recurrentes_particulares"] = cl["pedidos_recurrentes"].reindex(s.index)
    return {c: ev.armar_grilla(s[c], d["clima"].reset_index(), cfg["serie"]["meses_verano"]) for c in s}


# ------------------------------------------------------------ contrafactual
def _ajustar_uno(y: np.ndarray, X, orden, estacional):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avisos de convergencia / no invertibilidad
        try:
            return SARIMAX(y, exog=X, order=orden, seasonal_order=estacional, trend="n").fit(disp=False, maxiter=200)
        except (np.linalg.LinAlgError, ValueError):
            return None


def ajustar_sarima(y: np.ndarray, X=None, n_jobs: int = -1):
    """Grilla de órdenes de `models/sarimax.py` con exógenas y sin constante; devuelve el ajuste de menor AIC."""
    res = Parallel(n_jobs=n_jobs)(delayed(_ajustar_uno)(y, X, o, e) for o, e in GRILLA)
    return min((r for r in res if r is not None and np.isfinite(r.aic)), key=lambda r: r.aic)


def contrafactual(g: pd.DataFrame, fecha, n_dias: int, log: bool, n_sim: int = 1000,
                  semilla: int = SEMILLA) -> dict:
    """Ajusta con g < fecha y simula los n_dias filas siguientes de la grilla."""
    fecha = pd.Timestamp(fecha)
    pre, post = g[g.index < fecha], g[g.index >= fecha].iloc[:n_dias]
    tr = np.log if log else (lambda x: x)
    y = tr(pre["y_modelo"].to_numpy(float))
    cols = columnas_variables(pre, ev.EXOG_CAL)
    X, Xf = (pre[cols].to_numpy(float), post[cols].to_numpy(float)) if cols else (None, None)

    res = ajustar_sarima(y, X)
    (p, d, q), (P, D, Q, s) = res.model.order, res.model.seasonal_order
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sims = res.simulate(len(post), repetitions=n_sim, anchor="end", exog=Xf,
                            rng=np.random.default_rng(semilla))
    sims = np.asarray(sims).reshape(len(post), n_sim)
    cf = np.exp(sims) if log else sims

    ok = post["abierto"].to_numpy() == 1
    obs = post["y"].to_numpy(float)[ok]
    media_cf = cf[ok].mean(axis=0)  # contrafactual medio por día abierto, por camino
    efecto = obs.mean() - media_cf
    pct = 100 * efecto / media_cf
    diario = pd.DataFrame({"y": post["y"], "cf_med": np.median(cf, axis=1),
                           "cf_inf": np.quantile(cf, 0.025, axis=1), "cf_sup": np.quantile(cf, 0.975, axis=1)},
                          index=post.index)
    return {"dias": int(ok.sum()), "desde": post.index[ok].min(), "hasta": post.index[ok].max(),
            "observado": obs.mean(), "contrafactual": float(np.median(media_cf)),
            "efecto": float(np.median(efecto)), "efecto_inf": float(np.quantile(efecto, 0.025)),
            "efecto_sup": float(np.quantile(efecto, 0.975)),
            "efecto_pct": float(np.median(pct)), "pct_inf": float(np.quantile(pct, 0.025)),
            "pct_sup": float(np.quantile(pct, 0.975)), "prob_efecto_positivo": float((efecto > 0).mean()),
            "orden": f"({p},{d},{q})({P},{D},{Q})[{s}]", "diario": diario}


# ------------------------------------------------------------------- placebo
def _regimen_nuevo(pre: pd.DataFrame, ventana: pd.DataFrame) -> bool:
    """True si alguna variable de calendario es constante en el entrenamiento pero
    cambia en la ventana (ej.: una ventana que cruza enero sin ningún enero antes).
    El modelo no puede saber el efecto de esa variable y el placebo no sería justo."""
    for c in ev.EXOG_CAL:
        vals = pre[c].unique()
        if len(vals) == 1 and (ventana[c] != vals[0]).any():
            return True
    return False


def fechas_placebo(g: pd.DataFrame, fecha, n_dias: int, fechas_eventos: list, n: int = 8,
                   paso_dias: int = 14, min_pre: int = 120) -> list[pd.Timestamp]:
    """Fechas falsas anteriores al evento: la ventana posterior termina antes del
    evento, no contiene ninguna fecha de evento real ni un régimen de calendario
    que no esté en el entrenamiento; al menos `min_pre` filas de entrenamiento."""
    fecha = pd.Timestamp(fecha)
    eventos = pd.to_datetime(fechas_eventos)
    idx = g.index
    out = []
    cand = fecha - pd.Timedelta(paso_dias, unit="D")
    while len(out) < n:
        i = idx.searchsorted(cand)
        if i < min_pre:
            break
        ventana = idx[i: i + n_dias]
        if (len(ventana) == n_dias and ventana.max() < fecha
                and not any((eventos >= ventana.min()) & (eventos <= ventana.max()))
                and not _regimen_nuevo(g.iloc[:i], g.loc[ventana])):
            out.append(idx[i])
        cand -= pd.Timedelta(paso_dias, unit="D")
    return sorted(out)


# -------------------------------------------------------------------- correr
def _fila(ev_id: str, serie: str, r: dict) -> dict:
    return {"evento": ev_id, "serie": serie, **{k: v for k, v in r.items() if k != "diario"}}


def analizar(G: dict, eventos: dict, n_sim: int = 1000, n_placebo: int = 8, verbose: bool = True):
    fechas_ev = []
    for e in eventos.values():
        fechas_ev += [e["fecha"]] + ([e["fin"]] if "fin" in e else [])
    filas, placebos, diarios = [], [], {}
    for ev_id, e in eventos.items():
        for s in e["series"]:
            g, n_dias, log = G[s], H * e["semanas_post"], EN_LOG.get(s, False)
            r = contrafactual(g, e["fecha"], n_dias, log, n_sim)
            filas.append(_fila(ev_id, s, r))
            diarios[(ev_id, s)] = r["diario"]
            # viandas, clientes y pedidos: efecto relativo (%, no depende de K); tasas: efecto
            # absoluto (por vianda), porque con tasas cerca de 0 el % explota
            k, ki, ks = (("efecto", "efecto_inf", "efecto_sup") if s.startswith("tasa")
                         else ("efecto_pct", "pct_inf", "pct_sup"))
            pl = []
            for f in fechas_placebo(g, e["fecha"], n_dias, fechas_ev, n=n_placebo):
                rp = contrafactual(g, f, n_dias, log, n_sim)
                pl.append({"evento": ev_id, "serie": s, "fecha_placebo": f, "metrica": k, "efecto": rp[k],
                           "inf": rp[ki], "sup": rp[ks], "significativo": not (rp[ki] <= 0 <= rp[ks])})
            pl = pd.DataFrame(pl)
            placebos.append(pl)
            fila = filas[-1]
            fila["metrica_placebo"] = k
            if len(pl):
                fila.update({"n_placebos": len(pl), "placebos_significativos": int(pl["significativo"].sum()),
                             "p_placebo": (1 + (pl["efecto"].abs() >= abs(r[k])).sum()) / (len(pl) + 1),
                             "efecto_minimo_detectable": 2.8 * pl["efecto"].std(ddof=1) if len(pl) > 1 else np.nan})
            if verbose:
                print(f"  {ev_id} / {s}: listo ({len(pl)} placebos)", flush=True)
    return pd.DataFrame(filas), pd.concat(placebos, ignore_index=True), diarios


def _coma(x: float, d: int) -> str:
    x = round(float(x), 4)  # igual que eventos_efectos.csv (y la tabla de resultados.md)
    return f"{x:+.{d}f}".replace("-", "−").replace(".", ",")


def titulo_evento(ev_id: str, s: str, r) -> str:
    """Título de panel con la misma unidad que la tabla de eventos: % en conteos y
    diferencia por vianda en las tasas."""
    if s.startswith("tasa"):
        ef = f"{_coma(r.efecto, 3)} [{_coma(r.efecto_inf, 3)}; {_coma(r.efecto_sup, 3)}] por vianda"
    else:
        ef = f"{_coma(r.efecto_pct, 0)} % [{_coma(r.pct_inf, 0)}; {_coma(r.pct_sup, 0)}]"
    return f"{nombre(ev_id)} — {nombre(s)}: efecto {ef}"


def fig_eventos(G: dict, efectos: pd.DataFrame, diarios: dict, destino, semanas_pre: int = 6,
                claves: list | None = None) -> None:
    """Observado contra contrafactual, un panel por análisis, con un solo título por panel."""
    claves = claves or list(diarios)
    fig, axs = plt.subplots(len(claves), 1, figsize=(11, 2.7 * len(claves)))
    for ax, (ev_id, s) in zip(np.atleast_1d(axs), claves):
        d = diarios[(ev_id, s)]
        g = G[s]
        pre = g[(g.index < d.index.min()) & (g["abierto"] == 1)].iloc[-H * semanas_pre:]
        abiertos = g.loc[d.index, "abierto"] == 1
        ax.plot(pre.index, pre["y"], "k.-", lw=0.8)
        ax.fill_between(d.index, d["cf_inf"], d["cf_sup"], alpha=0.25, color="C0", label="Contrafactual, banda 95 %")
        ax.plot(d.index, d["cf_med"], "C0-", lw=1, label="Contrafactual (mediana)")
        ax.plot(d.index[abiertos], d["y"][abiertos], "k.-", lw=0.8, label="Observado")
        ax.axvline(d.index.min(), color="C3", ls="--", lw=1)
        r = efectos[(efectos.evento == ev_id) & (efectos.serie == s)].iloc[0]
        ax.set_title(titulo_evento(ev_id, s, r), fontsize=9)
        ax.tick_params(labelsize=7)
    np.atleast_1d(axs)[0].legend(fontsize=7, ncol=3)
    fig.tight_layout()
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)


def correr() -> dict:
    cfg = cargar_config()
    eventos = cargar_eventos()
    G = grillas(cfg)
    print(f"Fase 7: {len(eventos['eventos'])} eventos")
    efectos, placebos, diarios = analizar(G, eventos["eventos"])
    tablas, figs = ruta("tablas", cfg), ruta("figuras", cfg)
    efectos.round(4).to_csv(tablas / "eventos_efectos.csv", index=False)
    placebos.round(4).to_csv(tablas / "eventos_placebo.csv", index=False)
    claves = list(diarios)  # dos figuras, como en el informe: los primeros cinco análisis y el resto
    fig_eventos(G, efectos, diarios, figs / "10_eventos.png", claves=claves[:5])
    fig_eventos(G, efectos, diarios, figs / "10b_eventos.png", claves=claves[5:])
    cols = ["evento", "serie", "desde", "hasta", "dias", "observado", "contrafactual", "efecto", "efecto_inf",
            "efecto_sup", "efecto_pct", "pct_inf", "pct_sup", "prob_efecto_positivo", "metrica_placebo", "n_placebos", "placebos_significativos", "p_placebo", "efecto_minimo_detectable", "orden"]
    print(efectos[[c for c in cols if c in efectos]].round(3).to_string(index=False))
    print("Notas:", *eventos.get("notas", []), sep="\n  ")
    return {"efectos": efectos, "placebos": placebos, "diarios": diarios}
