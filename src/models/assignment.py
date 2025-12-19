from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.db import Base


class ProspectAssignment(Base):
    __tablename__ = "prospect_assignments"
    __table_args__ = (UniqueConstraint("cnpj_cpf", name="uq_prospect_assignments_cnpj"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cnpj_cpf: Mapped[str] = mapped_column(String, nullable=False)
    executivo_id: Mapped[int] = mapped_column(Integer, ForeignKey("executives.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    filters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    mes_ref: Mapped[str | None] = mapped_column(String, nullable=True)


class DistributionLog(Base):
    __tablename__ = "distribution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cnpj_cpf: Mapped[str] = mapped_column(String, nullable=False)
    executivo_id: Mapped[int] = mapped_column(Integer, ForeignKey("executives.id"), nullable=False)
    previous_executivo_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    filters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    mes_ref: Mapped[str | None] = mapped_column(String, nullable=True)
