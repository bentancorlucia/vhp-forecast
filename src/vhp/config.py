"""Lectura de la configuración y rutas del proyecto."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]


def cargar_config(ruta: Path | None = None) -> dict:
    """Lee config/config.yaml y devuelve un diccionario."""
    ruta = ruta or RAIZ / "config" / "config.yaml"
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ruta(clave: str, cfg: dict | None = None) -> Path:
    """Ruta absoluta de una entrada de `rutas` en config.yaml."""
    cfg = cfg or cargar_config()
    return RAIZ / cfg["rutas"][clave]
