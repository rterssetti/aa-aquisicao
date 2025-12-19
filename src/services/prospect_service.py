from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import select

from src.models.assignment import DistributionLog, ProspectAssignment
from src.models.db import get_session
from src.repositories.prospects_repository import ProspectsRepository


@dataclass
class ProspectFilters:
    cd_cnae5: list[str] | None = None
    cd_cnae: list[str] | None = None
    faixa_fat: list[str] | None = None
    unidade_federal: list[str] | None = None
    poligono: list[str] | None = None
    pub_credito: list[str] | None = None
    porte: list[str] | None = None
    rating: list[str] | None = None
    fl_potencial: list[int] | None = None
    fl_cnae_foco: list[int] | None = None
    fl_pep: list[int] | None = None
    status_cadastral: list[str] | None = None
    segmento: list[str] | None = None
    campanha: list[str] | None = None
    funil: list[str] | None = None
    mes_ref_start: str | None = None
    mes_ref_end: str | None = None


@dataclass
class AssignmentResult:
    total: int
    assigned: int
    skipped_same_exec: int
    overwritten: int


def _apply_multi_filter(df: pd.DataFrame, column: str, values: list[Any] | None) -> pd.DataFrame:
    if not values:
        return df
    return df[df[column].isin(values)]


def filter_prospects(repo: ProspectsRepository, filters: ProspectFilters) -> pd.DataFrame:
    df = repo.load()
    df = _apply_multi_filter(df, "cd_cnae5", filters.cd_cnae5)
    df = _apply_multi_filter(df, "cd_cnae", filters.cd_cnae)
    df = _apply_multi_filter(df, "faixa_fat", filters.faixa_fat)
    df = _apply_multi_filter(df, "unidade_federal", filters.unidade_federal)
    df = _apply_multi_filter(df, "poligono", filters.poligono)
    df = _apply_multi_filter(df, "pub_credito", filters.pub_credito)
    df = _apply_multi_filter(df, "porte", filters.porte)
    df = _apply_multi_filter(df, "rating", filters.rating)
    df = _apply_multi_filter(df, "fl_potencial", filters.fl_potencial)
    df = _apply_multi_filter(df, "fl_cnae_foco", filters.fl_cnae_foco)
    df = _apply_multi_filter(df, "fl_pep", filters.fl_pep)
    df = _apply_multi_filter(df, "status_cadastral", filters.status_cadastral)
    df = _apply_multi_filter(df, "segmento", filters.segmento)
    df = _apply_multi_filter(df, "campanha", filters.campanha)
    df = _apply_multi_filter(df, "funil", filters.funil)

    if filters.mes_ref_start:
        df = df[df["mes_ref"] >= filters.mes_ref_start]
    if filters.mes_ref_end:
        df = df[df["mes_ref"] <= filters.mes_ref_end]
    return df


def assign_prospects(
    executivo_id: int, prospect_ids: list[str], filters: ProspectFilters
) -> AssignmentResult:
    assigned = 0
    skipped_same_exec = 0
    overwritten = 0
    filters_json = json.dumps(filters.__dict__, ensure_ascii=False)
    mes_ref = filters.mes_ref_start or filters.mes_ref_end

    with next(get_session()) as session:
        for prospect_id in prospect_ids:
            existing = session.execute(
                select(ProspectAssignment).where(ProspectAssignment.cnpj_cpf == prospect_id)
            ).scalar_one_or_none()

            if existing and existing.executivo_id == executivo_id:
                skipped_same_exec += 1
                continue

            previous_exec = existing.executivo_id if existing else None
            if existing:
                existing.executivo_id = executivo_id
                existing.assigned_at = datetime.utcnow()
                existing.filters_json = filters_json
                existing.mes_ref = mes_ref
                overwritten += 1
            else:
                session.add(
                    ProspectAssignment(
                        cnpj_cpf=prospect_id,
                        executivo_id=executivo_id,
                        filters_json=filters_json,
                        mes_ref=mes_ref,
                    )
                )
                assigned += 1

            session.add(
                DistributionLog(
                    cnpj_cpf=prospect_id,
                    executivo_id=executivo_id,
                    previous_executivo_id=previous_exec,
                    filters_json=filters_json,
                    mes_ref=mes_ref,
                )
            )

        session.commit()

    total = len(prospect_ids)
    return AssignmentResult(
        total=total,
        assigned=assigned,
        skipped_same_exec=skipped_same_exec,
        overwritten=overwritten,
    )
