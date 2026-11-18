"""Punto de entrada: python main.py prepare | anonymize | calendar | clima | eda | backtest | mix | eventos | ads | plan | compras | report | all"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from vhp import ads, anonymize, decision, eda, report, external, intervention, jerarquico, load, pronostico, recetario  # noqa: E402
from vhp import calendar as calendario  # noqa: E402

PASOS = {
    "prepare": load.preparar,
    "anonymize": anonymize.anonimizar,
    "calendar": calendario.calendario,
    "clima": external.clima,
    "eda": eda.correr,
    "backtest": pronostico.correr,
    "mix": jerarquico.correr,
    "eventos": intervention.correr,
    "ads": ads.correr,
    "plan": decision.correr,
    "compras": recetario.correr,
    "report": report.correr,
}


def main() -> None:
    paso = sys.argv[1] if len(sys.argv) > 1 else "all"
    if paso == "all":
        for f in PASOS.values():
            f()
    elif paso in PASOS:
        PASOS[paso]()
    else:
        sys.exit(f"Paso desconocido: {paso}. Opciones: {', '.join(PASOS)} o all")


if __name__ == "__main__":
    main()
