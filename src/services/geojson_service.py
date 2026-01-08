from __future__ import annotations

"""Serviços para baixar e converter as malhas territoriais do IBGE.

O IBGE disponibiliza as geometrias municipais em um arquivo ZIP contendo
Shapefile (SHP/DBF/SHX). Este módulo baixa o ZIP, identifica os componentes
necessários, respeita a codificação definida pelo CPG quando disponível e
converte as feições para GeoJSON para uso no mapa do Streamlit.
"""

import io
import json
import zipfile
from pathlib import Path
from typing import Any, Iterable

import requests
import shapefile

IBGE_MUNICIPALITIES_ZIP_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/"
    "malhas_territoriais/malhas_municipais/municipio_2024/Brasil/BR_Municipios_2024.zip"
)

GEOJSON_FILENAME = "municipalities.geojson"

MUNICIPALITY_CODE_KEYS = (
    "CD_MUN",
    "CD_GEOCMU",
    "codarea",
)


def normalize_municipality_code(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    value = str(value).strip()
    if value.isdigit() and len(value) < 7:
        return value.zfill(7)
    return value


def _extract_municipality_code(properties: dict[str, Any]) -> str:
    for key in MUNICIPALITY_CODE_KEYS:
        if key in properties:
            code = normalize_municipality_code(properties.get(key))
            if code:
                return code
    return ""


def _select_shapefile_components(names: Iterable[str]) -> tuple[str, str, str, str | None]:
    shp_name = next((name for name in names if name.lower().endswith(".shp")), "")
    if not shp_name:
        raise ValueError("Arquivo .shp não encontrado no zip das malhas IBGE.")

    base_name = shp_name[:-4]
    dbf_name = f"{base_name}.dbf"
    shx_name = f"{base_name}.shx"
    cpg_name = f"{base_name}.cpg" if f"{base_name}.cpg" in names else None

    return shp_name, dbf_name, shx_name, cpg_name


def _read_cpg_encoding(zip_file: zipfile.ZipFile, cpg_name: str | None) -> str | None:
    if not cpg_name:
        return None
    try:
        raw = zip_file.read(cpg_name)
    except KeyError:
        return None
    encoding = raw.decode("utf-8", errors="ignore").strip()
    return encoding or None


def _load_shapefile_from_zip(zip_path: Path) -> shapefile.Reader:
    with zipfile.ZipFile(zip_path) as zip_file:
        names = zip_file.namelist()
        shp_name, dbf_name, shx_name, cpg_name = _select_shapefile_components(names)
        encoding = _read_cpg_encoding(zip_file, cpg_name) or "latin-1"

        shp_bytes = zip_file.read(shp_name)
        dbf_bytes = zip_file.read(dbf_name)
        shx_bytes = zip_file.read(shx_name)

    return shapefile.Reader(
        shp=io.BytesIO(shp_bytes),
        dbf=io.BytesIO(dbf_bytes),
        shx=io.BytesIO(shx_bytes),
        encoding=encoding,
    )


def _convert_shapefile_to_geojson(reader: shapefile.Reader) -> dict[str, Any]:
    fields = [field[0] for field in reader.fields[1:]]
    features: list[dict[str, Any]] = []

    for shape_record in reader.iterShapeRecords():
        properties = {
            fields[index]: shape_record.record[index]
            for index in range(len(fields))
        }
        geometry = shape_record.shape.__geo_interface__
        feature: dict[str, Any] = {
            "type": "Feature",
            "geometry": geometry,
            "properties": properties,
        }
        code = _extract_municipality_code(properties)
        if code:
            feature["id"] = code
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def download_municipality_geojson(data_dir: Path, force: bool = False) -> Path:
    """Baixa a malha municipal (ZIP) e converte o shapefile para GeoJSON.

    O fluxo salva o ZIP em disco, extrai os bytes do SHP/DBF/SHX, carrega com
    pyshp e monta um FeatureCollection já com o código IBGE como `id`.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = data_dir / GEOJSON_FILENAME

    if geojson_path.exists() and not force:
        return geojson_path

    zip_path = data_dir / "municipalities.zip"
    response = requests.get(IBGE_MUNICIPALITIES_ZIP_URL, timeout=120)
    response.raise_for_status()
    zip_path.write_bytes(response.content)

    reader = _load_shapefile_from_zip(zip_path)
    geojson = _convert_shapefile_to_geojson(reader)

    with geojson_path.open("w", encoding="utf-8") as geojson_file:
        json.dump(geojson, geojson_file)

    return geojson_path


def load_municipality_geojson(data_dir: Path, force: bool = False) -> dict[str, Any]:
    geojson_path = download_municipality_geojson(data_dir, force=force)
    with geojson_path.open("r", encoding="utf-8") as geojson_file:
        return json.load(geojson_file)
