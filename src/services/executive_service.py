from __future__ import annotations

from typing import Iterable

from sqlalchemy import select

from src.models.db import get_session
from src.models.executive import Executive


def list_executives(active_only: bool = False) -> list[Executive]:
    with next(get_session()) as session:
        stmt = select(Executive)
        if active_only:
            stmt = stmt.where(Executive.ativo.is_(True))
        return list(session.execute(stmt).scalars())


def create_executive(nome: str, email: str, regiao: str | None) -> Executive:
    with next(get_session()) as session:
        executive = Executive(nome=nome, email=email, regiao=regiao)
        session.add(executive)
        session.commit()
        session.refresh(executive)
        return executive


def update_executive(executive_id: int, nome: str, email: str, regiao: str | None) -> None:
    with next(get_session()) as session:
        executive = session.get(Executive, executive_id)
        if not executive:
            raise ValueError("Executivo não encontrado")
        executive.nome = nome
        executive.email = email
        executive.regiao = regiao
        session.commit()


def set_executive_active(executive_id: int, ativo: bool) -> None:
    with next(get_session()) as session:
        executive = session.get(Executive, executive_id)
        if not executive:
            raise ValueError("Executivo não encontrado")
        executive.ativo = ativo
        session.commit()


def get_executive_map(executives: Iterable[Executive]) -> dict[int, str]:
    return {executive.id: f"{executive.nome} ({executive.email})" for executive in executives}
