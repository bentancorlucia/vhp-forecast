"""Tests de la fase 6: participaciones y unidades por categoría."""
import numpy as np
import pandas as pd
import pytest

from vhp import calendar as cal
from vhp import evaluate as ev
from vhp.models import mix as mx

CATS = ["a", "b", "c"]


def test_categorias_suman_el_segmento():
    """Participaciones suman 1 y unidades por categoría suman el pronóstico del segmento (pronóstico y límites del intervalo 80 %)."""
    U, g = _datos_mix()
    origen = [d for d in g.index if d.dayofweek == 5][-3]
    hist, fut = ev.partir(g, origen)
    rng = np.random.default_rng(0)
    q5 = rng.uniform(50, 150, len(fut))
    sq = pd.DataFrame({"q0.1": 0.8 * q5, "q0.5": q5, "q0.9": 1.2 * q5}, index=fut.index)
    for f in mx.catalogo().values():
        P = f(U.loc[hist.index], hist, fut)
        assert np.allclose(P.sum(axis=1), 1)
        uc = mx.unidades_categoria(sq, P)
        assert set(uc) == set(U.columns)
        pd.testing.assert_frame_equal(sum(uc.values()), sq)


def _datos_mix(n_semanas=30, semilla=0):
    rng = np.random.default_rng(semilla)
    dias = pd.DatetimeIndex(cal.dias_habiles("2025-06-02", pd.Timestamp("2025-06-02") + pd.Timedelta(7 * n_semanas, unit="D")))
    clima = pd.DataFrame({"fecha": pd.date_range(dias.min(), dias.max()),
                          "temperature_2m_max": rng.normal(18, 5, (dias.max() - dias.min()).days + 1),
                          "precipitation_sum": rng.exponential(2, (dias.max() - dias.min()).days + 1)})
    g = ev.armar_grilla(pd.Series(100.0, index=dias), clima)
    t = g["temperature_2m_max"].to_numpy()
    p_a = 1 / (1 + np.exp(-(t - 18) / 4))  # "a" sube con el calor
    U = pd.DataFrame({"a": rng.poisson(60 * p_a), "b": rng.poisson(60 * (1 - p_a)), "c": rng.poisson(20, len(g))},
                     index=g.index).astype(float)
    U[g["abierto"] == 0] = np.nan
    return U, g


@pytest.mark.parametrize("nombre", list(mx.catalogo()))
def test_participaciones_suman_1_y_no_ven_el_futuro(nombre):
    U, g = _datos_mix()
    origen = [d for d in g.index if d.dayofweek == 5][-3]
    hist, fut = ev.partir(g, origen)
    f = mx.catalogo()[nombre]
    P1 = f(U.loc[hist.index], hist, fut)
    assert np.allclose(P1.sum(axis=1), 1) and (P1 >= 0).all().all()
    U2 = U.copy()
    U2.loc[U2.index > origen] *= 7  # cambiar las ventas futuras no cambia nada
    P2 = f(U2.loc[hist.index], hist, fut)
    pd.testing.assert_frame_equal(P1, P2)


def test_mix_reciente_usa_solo_el_pasado():
    U, _ = _datos_mix()
    r1 = mx.mix_reciente(U)
    U2 = U.copy()
    U2.iloc[100:] *= 3
    pd.testing.assert_frame_equal(r1.iloc[:101], mx.mix_reciente(U2).iloc[:101])


def test_efecto_temperatura_recupera_el_signo():
    U, g = _datos_mix()
    ef = mx.efecto_temperatura(U, g, 12.0, 26.0, n_boot=20).set_index("categoria")
    assert ef.loc["a", "calor_menos_frio_pp"] > 10 and ef.loc["b", "calor_menos_frio_pp"] < -10
    assert np.isclose(ef["calor_menos_frio_pp"].sum(), 0, atol=1e-6)
