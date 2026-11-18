"""MLP (PyTorch) con los mismos rezagos y variables de calendario que LightGBM.

- Entrada: las mismas columnas que `lgbm.rasgos` (18 lags y 2 medias móviles
  divididos por el nivel del origen, calendario del día objetivo y h). El día
  de la semana y h van en one-hot. Estrategia directa: una fila por (origen, h).
- Red: Linear → ReLU → Linear → ReLU → Linear (dos capas ocultas, 32 y 16).
- Objetivo: y / nivel; pérdida: error absoluto medio (como LightGBM).
- Preprocesamiento: Pipeline de sklearn = ColumnTransformer (numéricas tal cual,
  OneHotEncoder con categorías fijas para dow y h) → StandardScaler. Se ajusta
  SOLO con las filas de entrenamiento de hist (sin la validación interna ni nada
  posterior al origen).
- Early stopping: las filas cuyo día objetivo cae en las últimas
  `semanas_validacion` semanas de hist son validación; se guarda el mejor estado.
- Semilla fija (42) y algoritmos deterministas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from torch import nn

from vhp.models import lgbm
from vhp.models.comun import SEMILLA, salida

H = 6


CATEGORICAS = ["dow", "h"]


def preprocesador(columnas: list[str]) -> Pipeline:
    """One-hot de dow (0–5) y h (1–6) con categorías fijas + escalado de todas las columnas.

    Orden de salida: numéricas en el orden de `columnas`, después dow_0..5 y h_1..6."""
    numericas = [c for c in columnas if c not in CATEGORICAS]
    one_hot = OneHotEncoder(categories=[list(range(6)), list(range(1, H + 1))],
                            handle_unknown="ignore", sparse_output=False, dtype=float)
    columnas_tf = ColumnTransformer([("num", "passthrough", numericas), ("cat", one_hot, CATEGORICAS)])
    return Pipeline([("columnas", columnas_tf), ("escala", StandardScaler())])


def red(n_entrada: int, oculta1: int = 32, oculta2: int = 16) -> nn.Module:
    return nn.Sequential(nn.Linear(n_entrada, oculta1), nn.ReLU(),
                         nn.Linear(oculta1, oculta2), nn.ReLU(),
                         nn.Linear(oculta2, 1))


def modelo(exog: list[str], epocas_max: int = 300, paciencia: int = 20, semanas_validacion: int = 4,
           lr: float = 1e-3, lote: int = 64):
    def f(hist: pd.DataFrame, fut: pd.DataFrame) -> pd.DataFrame:
        torch.manual_seed(SEMILLA)
        np.random.seed(SEMILLA)
        torch.use_deterministic_algorithms(True)
        torch.set_num_threads(1)

        X, obj, pos, Xf, nivel = lgbm.rasgos(hist, fut, exog)
        val = pos >= len(hist) - H * semanas_validacion  # día objetivo en las últimas semanas de hist
        prep = preprocesador(list(X.columns)).fit(X[~val])  # one-hot + escalado ajustados solo con train
        t = lambda a: torch.tensor(np.asarray(a), dtype=torch.float32)  # noqa: E731
        Xtr, ytr = t(prep.transform(X[~val])), t(obj[~val]).unsqueeze(1)
        Xva, yva = t(prep.transform(X[val])), t(obj[val]).unsqueeze(1)

        net = red(Xtr.shape[1])
        opt = torch.optim.Adam(net.parameters(), lr=lr)
        perdida = nn.L1Loss()
        gen = torch.Generator().manual_seed(SEMILLA)
        mejor, estado, sin_mejora = np.inf, None, 0
        for _ in range(epocas_max):
            net.train()
            orden = torch.randperm(len(Xtr), generator=gen)
            for i in range(0, len(orden), lote):
                b = orden[i: i + lote]
                opt.zero_grad()
                loss = perdida(net(Xtr[b]), ytr[b])
                loss.backward()
                opt.step()
            net.eval()
            with torch.no_grad():
                lv = perdida(net(Xva), yva).item()
            if lv < mejor - 1e-5:
                mejor, estado, sin_mejora = lv, {k: v.clone() for k, v in net.state_dict().items()}, 0
            else:
                sin_mejora += 1
                if sin_mejora >= paciencia:
                    break
        net.load_state_dict(estado)
        net.eval()
        with torch.no_grad():
            p = net(t(prep.transform(Xf))).squeeze(1).numpy() * nivel
        return salida(fut.index, p)

    return f
