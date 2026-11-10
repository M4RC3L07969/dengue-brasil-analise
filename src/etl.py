"""Leitura padronizada das notificações de dengue do SINAN.

O SINAN usou quatro leiautes de arquivo entre 2000 e 2026, com nomes de colunas e códigos
diferentes (até 2006, por exemplo, a classificação final se chamava CON_CLASSI e a UF era
gravada como sigla). Este módulo lê cada arquivo anual em blocos, apenas com as colunas
necessárias, e entrega os registros com nomes de colunas padronizados para todos os anos.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterator

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv

from src import config

LEGACY_LAST_YEAR = 2006
READ_BLOCK_BYTES = 32 << 20
LEGACY_COLUMNS = {
    "DT_NOTIFIC": "dt_notificacao",
    "DT_SIN_PRI": "dt_sintomas",
    "SEM_PRI": "semana_sintomas_sinan",
    "SG_UF": "uf_residencia",
    "ID_MN_RESI": "municipio_residencia",
    "NU_IDADE": "idade_codigo",
    "CS_SEXO": "sexo",
    "CS_RACA": "raca",
    "CON_CLASSI": "classificacao",
    "CON_CRITER": "criterio",
    "CON_EVOLUC": "evolucao",
    "HOSPITALIZ": "hospitalizacao",
    "NDUPLIC": "duplicidade",
}

CURRENT_COLUMNS = {
    "DT_NOTIFIC": "dt_notificacao",
    "DT_SIN_PRI": "dt_sintomas",
    "SEM_PRI": "semana_sintomas_sinan",
    "SG_UF": "uf_residencia",
    "ID_MN_RESI": "municipio_residencia",
    "NU_IDADE_N": "idade_codigo",
    "ANO_NASC": "ano_nascimento",
    "CS_SEXO": "sexo",
    "CS_RACA": "raca",
    "CLASSI_FIN": "classificacao",
    "CRITERIO": "criterio",
    "EVOLUCAO": "evolucao",
    "HOSPITALIZ": "hospitalizacao",
    "SOROTIPO": "sorotipo",
    "NDUPLIC_N": "duplicidade",
}

STANDARD_FIELDS = tuple(dict.fromkeys([*CURRENT_COLUMNS.values(), *LEGACY_COLUMNS.values()]))


def column_map(year: int) -> dict[str, str]:
    """Retorna o mapeamento de colunas originais para nomes padronizados conforme o leiaute do ano."""
    return LEGACY_COLUMNS if year <= LEGACY_LAST_YEAR else CURRENT_COLUMNS


def read_raw_year(year: int, block_bytes: int = READ_BLOCK_BYTES) -> Iterator[pd.DataFrame]:
    """Lê o arquivo anual do SINAN em blocos, já com as colunas padronizadas.

    Todas as colunas são lidas como texto para que nenhum código (por exemplo, "08" ou "A046")
    seja alterado por inferência automática de tipos. Colunas ausentes no leiaute do ano são
    criadas vazias, de modo que todos os anos tenham a mesma estrutura.

    Yields:
        Blocos de registros com as colunas de `STANDARD_FIELDS` e o ano do arquivo.
    """
    mapping = column_map(year)
    path = config.sinan_zip_path(year)
    with zipfile.ZipFile(path) as archive:
        member = next(name for name in archive.namelist() if name.lower().endswith(".csv"))
        with archive.open(member) as handle:
            header = handle.readline().decode("utf-8").strip().split(",")
        available = [column for column in mapping if column in header]
        with archive.open(member) as handle:
            reader = pacsv.open_csv(
                handle,
                read_options=pacsv.ReadOptions(block_size=block_bytes, encoding="utf-8"),
                parse_options=pacsv.ParseOptions(delimiter=","),
                convert_options=pacsv.ConvertOptions(
                    include_columns=available,
                    column_types={column: pa.string() for column in available},
                    strings_can_be_null=True,
                ),
            )
            for batch in reader:
                frame = batch.to_pandas(types_mapper=pd.ArrowDtype).rename(columns=mapping)
                frame = frame.astype("string")
                for field in STANDARD_FIELDS:
                    if field not in frame:
                        frame[field] = pd.Series(pd.NA, index=frame.index, dtype="string")
                frame["ano_arquivo"] = np.int16(year)
                yield frame[["ano_arquivo", *STANDARD_FIELDS]]
