"""Parâmetros centrais do projeto: caminhos, recorte temporal e endereços das fontes de dados.

Concentrar essas definições em um único módulo garante que download, tratamento e análise
usem exatamente os mesmos caminhos e o mesmo recorte, o que é essencial para a reprodutibilidade.
"""

from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
SINAN_RAW_DIR = RAW_DIR / "sinan"
IBGE_RAW_DIR = RAW_DIR / "ibge"
PROCESSED_DIR = DATA_DIR / "processed"
DOCS_DIR = ROOT_DIR / "docs"
ASSETS_DIR = DOCS_DIR / "assets"

FIRST_YEAR = 2000
LAST_YEAR = 2026
YEARS = tuple(range(FIRST_YEAR, LAST_YEAR + 1))
PARTIAL_YEARS = frozenset({2026})

SINAN_CSV_URL = (
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR{yy:02d}.csv.zip"
)
SINAN_DICTIONARY_URL = (
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/dic_dados_dengue.pdf"
)
SINAN_DATASET_PAGE = "https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue"

IBGE_AGGREGATES_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"
IBGE_LOCALITIES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"

HTTP_TIMEOUT_SECONDS = 120
HTTP_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class PopulationSource:
    """Tabela do IBGE (sistema SIDRA) usada como fonte de população residente.

    Attributes:
        table: código da tabela no SIDRA.
        variable: código da variável de população dentro da tabela.
        periods: anos disponíveis que serão consultados.
        label: descrição da origem do número (censo ou estimativa).
    """

    table: int
    variable: int
    periods: tuple[int, ...]
    label: str


POPULATION_SOURCES = (
    PopulationSource(table=200, variable=93, periods=(2000, 2010), label="censo"),
    PopulationSource(table=4709, variable=93, periods=(2022,), label="censo"),
    PopulationSource(
        table=6579,
        variable=9324,
        periods=(
            2001, 2002, 2003, 2004, 2005, 2006, 2008, 2009, 2011, 2012, 2013,
            2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2024, 2025, 2026,
        ),
        label="estimativa",
    ),
)

TERRITORIAL_LEVELS = {"uf": "N3", "municipio": "N6"}


def sinan_url(year: int) -> str:
    """Retorna o endereço do arquivo anual de notificações de dengue do SINAN."""
    return SINAN_CSV_URL.format(yy=year % 100)


def sinan_zip_path(year: int) -> Path:
    """Retorna o caminho local onde o arquivo anual do SINAN é armazenado."""
    return SINAN_RAW_DIR / f"DENGBR{year % 100:02d}.csv.zip"
