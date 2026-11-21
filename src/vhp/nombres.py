"""Nombres en español para figuras y tablas: un solo diccionario para todo el proyecto.

`nombre(x)` traduce un identificador del código (modelo, serie, evento, columna) a
texto de informe. Si no está en el diccionario, cambia "_" por espacios y pone
mayúscula inicial.
"""
from __future__ import annotations

NOMBRES = {
    # series
    "unique_id": "Serie",
    "Total": "Total",
    "Total/particulares": "Particulares",
    "Total/empresas": "Empresas",
    "particulares": "Particulares",
    "empresas": "Empresas",
    # modelos
    "naive": "Naive",
    "naive_estacional": "Naive estacional",
    "media_movil_4sem": "Media móvil 4 semanas",
    "ets": "ETS",
    "sarima": "SARIMA",
    "sarimax": "SARIMAX",
    "lgbm_directo": "LightGBM directo",
    "mlp": "MLP",
    # mix
    "media_4sem": "Media de 4 semanas",
    "multinomial": "Multinomial",
    "multinomial_clima": "Multinomial con clima",
    # eventos
    "agencia_meta": "Agencia de Meta",
    "influencer": "Influencer",
    "postres_web": "Postres en la web",
    "panes_web": "Panes en la web",
    "suba_precio": "Suba de precio",
    "suba_precio_13sem": "Suba de precio, 13 semanas",
    "meta_reparto": "Cambio de reparto en Meta",
    "baja_pauta": "Baja de pauta",
    # series de eventos
    "viandas_particulares": "Viandas, particulares",
    "tasa_postre_particulares": "Postres por vianda, particulares",
    "tasa_pan_particulares": "Panes por vianda, particulares",
    "tasa_extras_particulares": "Extras por vianda, particulares",
    "clientes_nuevos_particulares": "Clientes nuevos, particulares",
    "pedidos_recurrentes_particulares": "Pedidos recurrentes, particulares",
    # STL
    "y": "Serie",
    "tendencia": "Tendencia",
    "estacional": "Estacional",
    "resto": "Resto",
}


def nombre(x: str) -> str:
    """Nombre en español de un identificador del código."""
    if x in NOMBRES:
        return NOMBRES[x]
    s = str(x).replace("_", " ")
    return s[:1].upper() + s[1:]
