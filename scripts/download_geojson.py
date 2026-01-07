from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse

from src.services.geojson_service import download_municipality_geojson

DATA_DIR = Path("data")


def download_geojson(force: bool = False) -> Path:
    geojson_path = download_municipality_geojson(DATA_DIR, force=force)
    print(f"GeoJSON salvo em {geojson_path}")
    return geojson_path


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
