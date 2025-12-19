from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd


class ProspectsRepository(Protocol):
    def load(self) -> pd.DataFrame:
        ...


@dataclass
class LocalFileRepository:
    file_path: Path

    def load(self) -> pd.DataFrame:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Prospects file not found: {self.file_path}")

        if self.file_path.suffix == ".parquet":
            return pd.read_parquet(self.file_path)
        if self.file_path.suffix == ".csv":
            return pd.read_csv(self.file_path)
        raise ValueError("Unsupported file format. Use .csv or .parquet")


@dataclass
class ImpalaOdbcRepository:
    dsn: str
    database: str

    def load(self) -> pd.DataFrame:
        raise NotImplementedError(
            "Impala ODBC repository is a stub. Provide ODBC connection in production."
        )
