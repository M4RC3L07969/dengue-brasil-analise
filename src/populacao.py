"""Tratamento da população residente do IBGE usada como denominador das taxas de incidência.

O IBGE não publica população para todos os anos: 2007 e 2023 não têm estimativa nem censo.
Esses anos são preenchidos por interpolação linear entre os anos vizinhos de cada localidade,
e a coluna `populacao_interpolada` identifica os valores obtidos dessa forma.
"""

from __future__ import annotations

import pandas as pd

from src import config


def load_states() -> pd.DataFrame:
    """Lê a tabela de unidades da federação (código, sigla, nome e região)."""
    states = pd.read_csv(config.IBGE_RAW_DIR / "estados.csv", dtype={"codigo_uf": "int8"})
    return states.astype({"sigla_uf": "string", "nome_uf": "string", "regiao": "category"})


def complete_years(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    """Cria uma linha para cada combinação de localidade e ano e interpola os anos sem dado.

    A interpolação é feita apenas entre anos com valor conhecido (sem extrapolar para antes da
    criação de um município, por exemplo).
    """
    grid = pd.MultiIndex.from_product([frame[key].unique(), config.YEARS], names=[key, "ano"])
    complete = frame.set_index([key, "ano"]).reindex(grid).sort_index().reset_index()
    complete["populacao_interpolada"] = complete["populacao"].isna()
    complete["populacao"] = complete.groupby(key)["populacao"].transform(
        lambda series: series.interpolate(method="linear", limit_area="inside")
    )
    complete["populacao_interpolada"] &= complete["populacao"].notna()
    complete["populacao"] = complete["populacao"].round().astype("Int64")
    return complete


def load_population(level: str) -> pd.DataFrame:
    """Lê a população residente por ano em nível de UF ou de município.

    Args:
        level: "uf" ou "municipio".

    Returns:
        Tabela com o código da localidade (`codigo_uf` ou `codigo_municipio`), o ano,
        a população e a indicação de valor interpolado. Códigos de município são reduzidos
        a 6 dígitos para serem compatíveis com o SINAN.
    """
    raw = pd.read_csv(config.IBGE_RAW_DIR / f"populacao_{level}.csv")
    if level == "uf":
        key = "codigo_uf"
        raw[key] = raw["codigo_ibge"].astype("int8")
    else:
        key = "codigo_municipio"
        raw[key] = (raw["codigo_ibge"] // 10).astype("int32")
    frame = raw[[key, "ano", "populacao"]].dropna(subset=["populacao"])
    frame = frame.groupby([key, "ano"], as_index=False)["populacao"].sum()
    return complete_years(frame, key)
