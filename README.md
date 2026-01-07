# aa-aquisicao

MVP em Python para distribuição de prospects com filtros, mapa e auditoria de carregamento.

## Requisitos

- Python 3.11+

## Configuração

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Gerar dataset dummy

```bash
python scripts/generate_dummy_data.py
```

Isso cria `data/prospects.parquet` com ~50k linhas.

## Baixar geometrias municipais do IBGE

```bash
python scripts/download_geojson.py
```

O script garante a criação da pasta `data/` e salva o arquivo `municipalities.geojson` para uso offline. Use `--force` para sobrescrever um arquivo existente.

## Executar scripts auxiliares

Os scripts do projeto ficam no diretório `scripts/` e podem ser executados com:

```bash
python scripts/<nome_do_script>.py
```

Exemplos:

- Gerar dataset dummy:
  ```bash
  python scripts/generate_dummy_data.py
  ```
- Baixar geometrias municipais do IBGE:
  ```bash
  python scripts/download_geojson.py --force
  ```

## Rodar o app

```bash
streamlit run app/main.py
```

## Estrutura

- `app/` Streamlit UI
- `src/` serviços, repositórios e modelos
- `data/` dados dummy
- `db/` SQLite local

## Observações

- O repositório Impala ODBC é apenas um stub (`src/repositories/prospects_repository.py`).
- O filtro por cidade não aparece no MVP pois não existe no dataset atual.
