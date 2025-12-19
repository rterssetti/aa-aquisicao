from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random

import numpy as np
import pandas as pd
from faker import Faker

OUTPUT_PATH = Path("data") / "prospects.parquet"

fake = Faker("pt_BR")
random.seed(42)
np.random.seed(42)

PUB_CREDITO = ["Verde", "Amarelo", "Cinza", "Vermelho", "Roxo"]
RATINGS = ["A", "B", "C", "D"]
PORTES = ["MEI", "ME", "EPP", "MEDIO", "GRANDE"]
FAIXAS_FAT = ["0-100k", "100k-500k", "500k-1M", "1M-5M", "5M+"]
UF = [
    "SP",
    "RJ",
    "MG",
    "ES",
    "PR",
    "SC",
    "RS",
    "BA",
    "PE",
    "CE",
]
SEGMENTOS = ["Varejo", "Indústria", "Serviços", "Agro", "Tech"]
CAMPANHAS = ["Q1", "Q2", "Q3", "Q4"]
FUNIS = ["Topo", "Meio", "Fundo"]
STATUS_CADASTRAL = ["ATIVO", "SUSPENSO", "INAPTO"]
MOTIVOS = ["OK", "RESTRICAO", "EM_ANALISE"]
STATUS_CCL = ["REGULAR", "IRREGULAR"]
STATUS_CNAE = ["ATIVO", "INATIVO"]
OP_MEI = ["SIM", "NAO"]
MARCA_ATUACAO = ["", "A", "B", "C"]


def random_date(start: date, end: date) -> date:
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def generate_rows(total: int) -> pd.DataFrame:
    data = []
    start_date = date(2023, 1, 1)
    end_date = date(2024, 12, 31)

    for _ in range(total):
        cnpj_root = fake.random_number(digits=9, fix_len=True)
        cnpj_full = fake.random_number(digits=14, fix_len=True)
        cd_cnae = fake.random_number(digits=7, fix_len=True)
        cd_cnae5 = str(cd_cnae)[:5]
        uf = random.choice(UF)
        polygon = f"sp_{random.randint(0, 200)}"
        lat = float(np.random.uniform(-33.75, 5.3))
        lon = float(np.random.uniform(-73.99, -34.8))
        mes_ref = random_date(start_date, end_date)

        data.append(
            {
                "pub_credito": random.choice(PUB_CREDITO),
                "cnpj9": str(cnpj_root),
                "rating": random.choice(RATINGS),
                "porte": random.choice(PORTES),
                "nomecli": fake.company(),
                "cod_grp": str(fake.random_number(digits=6, fix_len=True)),
                "fat_num": str(fake.random_number(digits=8, fix_len=True)),
                "motivo_final": random.choice(MOTIVOS),
                "status_ccl": random.choice(STATUS_CCL),
                "pub_credito_grupo": random.choice(PUB_CREDITO),
                "soma_fat_grp": str(fake.random_number(digits=9, fix_len=True)),
                "cd_cnae5": cd_cnae5,
                "cnpj_cpf": str(cnpj_full),
                "faixa_fat": random.choice(FAIXAS_FAT),
                "fl_cnae_foco": random.randint(0, 1),
                "status_cnae": random.choice(STATUS_CNAE),
                "fl_ramo_performar": random.randint(0, 1),
                "cd_cnae": str(cd_cnae),
                "ds_cnae": fake.job(),
                "op_mei": random.choice(OP_MEI),
                "fl_potencial": random.randint(0, 1),
                "qtd_cnpj_grupo": random.randint(1, 20),
                "unidade_federal": uf,
                "funil": random.choice(FUNIS),
                "segmento": random.choice(SEGMENTOS),
                "campanha": random.choice(CAMPANHAS),
                "fl_pep": random.randint(0, 1),
                "status_cadastral": random.choice(STATUS_CADASTRAL),
                "marca_atuacao": random.choice(MARCA_ATUACAO),
                "mes_ref": mes_ref.isoformat(),
                "poligono": polygon,
                "lat": lat,
                "long": lon,
            }
        )

    return pd.DataFrame(data)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate_rows(50000)
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
