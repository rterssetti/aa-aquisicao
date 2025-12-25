from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pydeck as pdk
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
from src.services.prospect_service import AssignmentResult, ProspectFilters, assign_prospects, filter_prospects

DATA_PATH = Path("data") / "prospects.parquet"

st.set_page_config(page_title="aa-aquisicao", layout="wide")
init_db()

st.title("aa-aquisicao")

repo = LocalFileRepository(DATA_PATH)


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
map_df = filtered_df[["lat", "long", "unidade_federal", "poligono"]].dropna()
if not map_df.empty:
    layer = pdk.Layer(
        "ScatterplotLayer",
        map_df,
        get_position="[long, lat]",
        get_radius=8000,
        get_color="[30, 144, 255, 160]",
        pickable=True,
    )
    view_state = pdk.ViewState(latitude=map_df["lat"].mean(), longitude=map_df["long"].mean(), zoom=4)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "UF: {unidade_federal}\nPolígono: {poligono}"}))
else:
    st.info("Nenhum ponto para mapear com os filtros atuais.")

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
