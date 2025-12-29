from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

IBGE_MUNICIPALITIES_GEOJSON_URL = (
    "https://servicodados.ibge.gov.br/api/v2/malhas/municipios?"
    "formato=application/vnd.geo+json&qualidade=minima"
)
DATA_DIR = Path("data")
GEOJSON_PATH = DATA_DIR / "municipalities.geojson"


def download_geojson(force: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if GEOJSON_PATH.exists() and not force:
        print(f"Arquivo já existe em {GEOJSON_PATH}. Use --force para substituir.")
        return GEOJSON_PATH

    response = requests.get(IBGE_MUNICIPALITIES_GEOJSON_URL, timeout=60)
    response.raise_for_status()
    geojson = response.json()

    with GEOJSON_PATH.open("w", encoding="utf-8") as geojson_file:
        json.dump(geojson, geojson_file)

    print(f"GeoJSON salvo em {GEOJSON_PATH}")
    return GEOJSON_PATH


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Baixa as geometrias municipais do IBGE e prepara a pasta data"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Força o download mesmo que o arquivo já exista",
    )
    args = parser.parse_args()

    download_geojson(force=args.force)


if __name__ == "__main__":
    main()
