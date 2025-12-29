from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.db import init_db
from src.repositories.prospects_repository import LocalFileRepository
from src.services.executive_service import (
    create_executive,
    get_executive_map,
    list_executives,
    set_executive_active,
    update_executive,
)
from src.services.prospect_service import (
    AssignmentResult,
    ProspectFilters,
    assign_prospects,
    filter_prospects,
    list_assignments,
    list_distribution_logs,
)

DATA_PATH = Path("data") / "prospects.parquet"

st.set_page_config(page_title="aa-aquisicao", layout="wide")
init_db()

st.title("aa-aquisicao")

repo = LocalFileRepository(DATA_PATH)

IBGE_MUNICIPALITIES_GEOJSON_URL = (
    "https://servicodados.ibge.gov.br/api/v2/malhas/municipios?"
    "formato=application/vnd.geo+json&qualidade=minima"
)


@st.cache_data(show_spinner="Baixando geometrias municipais do IBGE...")
def fetch_municipality_geojson() -> dict[str, Any]:
    local_geojson_path = PROJECT_ROOT / "data" / "municipalities.geojson"

    if local_geojson_path.exists():
        with local_geojson_path.open("r", encoding="utf-8") as geojson_file:
            return json.load(geojson_file)

    local_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(IBGE_MUNICIPALITIES_GEOJSON_URL, timeout=60)
    response.raise_for_status()
    geojson = response.json()

    with local_geojson_path.open("w", encoding="utf-8") as geojson_file:
        json.dump(geojson, geojson_file)

    return geojson


def build_municipality_layer(
    geojson: dict[str, Any],
    municipality_counts: pd.DataFrame,
    municipality_column: str,
) -> pdk.Layer:
    counts_map = {
        str(row[municipality_column]): int(row["prospects"])
        for _, row in municipality_counts.iterrows()
    }

    max_prospects = max(counts_map.values()) if counts_map else 0
    max_prospects = max_prospects or 1

    for feature in geojson.get("features", []):
        code = str(feature.get("id") or feature.get("properties", {}).get("codarea", ""))
        prospects = counts_map.get(code, 0)

        intensity = prospects / max_prospects
        fill_color = [
            230 - int(140 * intensity),
            100 + int(60 * intensity),
            80,
            50 if prospects == 0 else 160,
        ]

        feature.setdefault("properties", {})
        feature["properties"].update(
            {
                "prospects": prospects,
                "codigo_ibge": code,
                "fill_color": fill_color,
            }
        )

    return pdk.Layer(
        "GeoJsonLayer",
        geojson,
        pickable=True,
        stroked=False,
        filled=True,
        get_fill_color="properties.fill_color",
        get_line_color=[255, 255, 255],
        line_width_min_pixels=0.5,
        opacity=0.6,
    )


def render_filters(df: pd.DataFrame) -> ProspectFilters:
    st.sidebar.header("Filtros")

    def multi_select(label: str, column: str) -> list[str]:
        options = sorted(df[column].dropna().unique())
        return st.sidebar.multiselect(label, options)

    cd_cnae5 = multi_select("CNAE 5", "cd_cnae5")
    cd_cnae = multi_select("CNAE", "cd_cnae")
    faixa_fat = multi_select("Faixa faturamento", "faixa_fat")
    unidade_federal = multi_select("UF", "unidade_federal")
    poligono = multi_select("Polígono", "poligono")

    pub_credito = multi_select("Pub. crédito", "pub_credito")
    rating = multi_select("Rating", "rating")
    porte = multi_select("Porte", "porte")
    fl_potencial = st.sidebar.multiselect("Potencial", sorted(df["fl_potencial"].unique()))
    fl_cnae_foco = st.sidebar.multiselect("CNAE foco", sorted(df["fl_cnae_foco"].unique()))
    fl_pep = st.sidebar.multiselect("PEP", sorted(df["fl_pep"].unique()))
    status_cadastral = multi_select("Status cadastral", "status_cadastral")
    segmento = multi_select("Segmento", "segmento")
    campanha = multi_select("Campanha", "campanha")
    funil = multi_select("Funil", "funil")

    mes_ref_start = st.sidebar.text_input("Mês ref início (YYYY-MM-DD)", "")
    mes_ref_end = st.sidebar.text_input("Mês ref fim (YYYY-MM-DD)", "")

    return ProspectFilters(
        cd_cnae5=cd_cnae5,
        cd_cnae=cd_cnae,
        faixa_fat=faixa_fat,
        unidade_federal=unidade_federal,
        poligono=poligono,
        pub_credito=pub_credito,
        rating=rating,
        porte=porte,
        fl_potencial=[int(x) for x in fl_potencial] if fl_potencial else None,
        fl_cnae_foco=[int(x) for x in fl_cnae_foco] if fl_cnae_foco else None,
        fl_pep=[int(x) for x in fl_pep] if fl_pep else None,
        status_cadastral=status_cadastral,
        segmento=segmento,
        campanha=campanha,
        funil=funil,
        mes_ref_start=mes_ref_start or None,
        mes_ref_end=mes_ref_end or None,
    )


st.header("Distribuir prospects")

try:
    base_df = repo.load()
except FileNotFoundError:
    st.error("Dataset não encontrado. Gere o arquivo em data/prospects.parquet")
    st.stop()

filters = render_filters(base_df)
filtered_df = filter_prospects(repo, filters)

col1, col2, col3 = st.columns(3)
col1.metric("Prospects", len(filtered_df))
col2.metric("UFs", filtered_df["unidade_federal"].nunique())
col3.metric("Polígonos", filtered_df["poligono"].nunique())

st.subheader("Preview")
page_size = st.selectbox("Linhas por página", [25, 50, 100], index=0)
page = st.number_input("Página", min_value=1, value=1)
start = (page - 1) * page_size
end = start + page_size
st.dataframe(filtered_df.iloc[start:end])

st.subheader("Mapa")
municipality_column: str | None = None
for candidate in ("municipio_ibge", "poligono"):
    if candidate in filtered_df.columns:
        municipality_column = candidate
        break

if not municipality_column:
    st.info("Nenhuma coluna de município encontrada no dataset para construir o mapa.")
else:
    municipality_counts = (
        filtered_df.dropna(subset=[municipality_column])
        .assign(**{municipality_column: lambda df: df[municipality_column].astype(str)})
        .groupby(municipality_column)
        .size()
        .reset_index(name="prospects")
    )

    if municipality_counts.empty:
        st.info("Nenhum município encontrado com os filtros atuais.")
    else:
        try:
            geojson = fetch_municipality_geojson()
            layer = build_municipality_layer(geojson, municipality_counts, municipality_column)
            view_state = pdk.ViewState(latitude=-14.235, longitude=-51.9253, zoom=3.5)

            st.pydeck_chart(
                pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip={
                        "text": "Município IBGE: {codigo_ibge}\nProspects: {prospects}",
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001
            st.error(
                "Não foi possível carregar as geometrias municipais do IBGE. "
                "Verifique a conexão ou tente novamente."
            )

st.subheader("Carregar para executivo")
executives = list_executives(active_only=True)
executive_map = get_executive_map(executives)
selected_exec_id = st.selectbox(
    "Executivo", options=list(executive_map.keys()), format_func=executive_map.get
)

if st.button("Carregar para executivo"):
    prospect_ids = filtered_df["cnpj_cpf"].dropna().astype(str).tolist()
    result: AssignmentResult = assign_prospects(selected_exec_id, prospect_ids, filters)
    st.success(
        f"Total: {result.total} | Novos: {result.assigned} | "
        f"Reatribuições: {result.overwritten} | Ignorados: {result.skipped_same_exec}"
    )

st.divider()
st.header("Consultas de carga por executivo")

all_execs = list_executives(active_only=False)
executive_map_all = get_executive_map(all_execs)

tab_logs, tab_assignments = st.tabs(["Distribuições recentes", "Carteira atual"])

with tab_logs:
    selected_log_exec = st.selectbox(
        "Executivo",
        options=[None] + list(executive_map_all.keys()),
        format_func=lambda x: executive_map_all.get(x, "Todos"),
    )

    logs = list_distribution_logs(selected_log_exec)
    if logs:
        logs_df = pd.DataFrame(
            [
                {
                    "Data": log.assigned_at.strftime("%Y-%m-%d %H:%M"),
                    "Executivo atual": executive_map_all.get(log.executivo_id, log.executivo_id),
                    "Executivo anterior": executive_map_all.get(log.previous_executivo_id, "-")
                    if log.previous_executivo_id
                    else "-",
                    "CNPJ/CPF": log.cnpj_cpf,
                    "Mês ref": log.mes_ref or "-",
                    "Filtros": log.filters_json,
                }
                for log in logs
            ]
        )
        st.dataframe(logs_df, use_container_width=True, height=400)
    else:
        st.info("Nenhuma distribuição registrada para o filtro selecionado.")

with tab_assignments:
    selected_assignment_exec = st.selectbox(
        "Executivo",
        options=[None] + list(executive_map_all.keys()),
        format_func=lambda x: executive_map_all.get(x, "Todos"),
        key="assignment_exec_selector",
    )

    assignments = list_assignments(selected_assignment_exec)
    if assignments:
        assignments_df = pd.DataFrame(
            [
                {
                    "CNPJ/CPF": assignment.cnpj_cpf,
                    "Executivo": executive_map_all.get(assignment.executivo_id, assignment.executivo_id),
                    "Carregado em": assignment.assigned_at.strftime("%Y-%m-%d %H:%M"),
                    "Mês ref": assignment.mes_ref or "-",
                    "Filtros": assignment.filters_json,
                }
                for assignment in assignments
            ]
        )

        base_columns = [
            col
            for col in [
                "razao_social",
                "nome_fantasia",
                "nm_razao_social",
                "nm_fantasia",
                "segmento",
                "unidade_federal",
            ]
            if col in base_df.columns
        ]
        if base_columns:
            extra_info = base_df[["cnpj_cpf", *base_columns]].drop_duplicates("cnpj_cpf")
            assignments_df = assignments_df.merge(
                extra_info, left_on="CNPJ/CPF", right_on="cnpj_cpf", how="left"
            ).drop(columns=["cnpj_cpf"])

        st.dataframe(assignments_df, use_container_width=True, height=400)
    else:
        st.info("Nenhum prospecto carregado para o filtro selecionado.")

st.divider()
st.header("Executivos")

with st.form("executive_form"):
    st.subheader("Criar executivo")
    nome = st.text_input("Nome")
    email = st.text_input("Email")
    regiao = st.text_input("Região")
    submitted = st.form_submit_button("Salvar")
    if submitted:
        create_executive(nome, email, regiao or None)
        st.success("Executivo criado")

st.subheader("Gerenciar executivos")
all_execs = list_executives(active_only=False)
for exec_item in all_execs:
    with st.expander(f"{exec_item.nome} ({exec_item.email})"):
        nome = st.text_input("Nome", exec_item.nome, key=f"nome_{exec_item.id}")
        email = st.text_input("Email", exec_item.email, key=f"email_{exec_item.id}")
        regiao = st.text_input("Região", exec_item.regiao or "", key=f"regiao_{exec_item.id}")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Atualizar", key=f"update_{exec_item.id}"):
                update_executive(exec_item.id, nome, email, regiao or None)
                st.success("Executivo atualizado")
        with col_b:
            toggle_label = "Inativar" if exec_item.ativo else "Ativar"
            if st.button(toggle_label, key=f"toggle_{exec_item.id}"):
                set_executive_active(exec_item.id, not exec_item.ativo)
                st.success("Status atualizado")
