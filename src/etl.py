"""Pipeline de extração, transformação e carga (ETL) das notificações de dengue do SINAN.

Etapas:
    1. Leitura em blocos de cada arquivo anual, apenas com as colunas necessárias, todas como texto.
    2. Padronização dos nomes de colunas entre os quatro leiautes usados pelo SINAN desde 2000.
    3. Limpeza e decodificação: datas, idade, códigos de UF e município, sexo, raça/cor,
       classificação final, critério de confirmação, evolução, hospitalização e sorotipo.
    4. Filtro de casos prováveis (exclusão de duplicidades e de casos descartados).
    5. Derivação de métricas: semana e ano epidemiológicos, faixa etária, caso grave e óbito.
       Caso grave: classificação "com sinais de alarme" ou "grave" (incluindo os códigos antigos
       de dengue com complicações, febre hemorrágica e síndrome do choque) confirmada por critério
       laboratorial ou clínico-epidemiológico, conforme orientação do Ministério da Saúde.
       Óbito: evolução "óbito pelo agravo" com critério de confirmação laboratorial ou
       clínico-epidemiológico.
    6. Gravação dos registros tratados por ano em Parquet.

Toda linha removida ou corrigida é contabilizada por ano e motivo em `data/processed/etl_log.csv`,
de forma que nenhuma operação destrutiva fique sem registro.

Uso:
    python -m src.etl                    # processa 2000-2026
    python -m src.etl --anos 2023-2025   # processa apenas alguns anos
"""

from __future__ import annotations

import argparse
import json
import logging
import zipfile
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from src import config
from src.download import parse_years

logger = logging.getLogger(__name__)

LEGACY_LAST_YEAR = 2006
READ_BLOCK_BYTES = 32 << 20
MAX_NOTIFICATION_DELAY_DAYS = 365
MIN_VALID_DATE = pd.Timestamp("1999-01-01")
MAX_VALID_DATE = pd.Timestamp(f"{config.LAST_YEAR}-12-31")
MAX_AGE_YEARS = 110

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

UF_CODES = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27, "SE": 28, "BA": 29,
    "MG": 31, "ES": 32, "RJ": 33, "SP": 35,
    "PR": 41, "SC": 42, "RS": 43,
    "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}
VALID_UF_CODES = frozenset(UF_CODES.values())

LEGACY_AGE_UNITS = {"H": "1", "D": "2", "M": "3", "A": "4"}
AGE_UNIT_DIVISORS = {"1": 24 * 365.25, "2": 365.25, "3": 12.0, "4": 1.0}

AGE_BINS = [0, 1, 5, 10, 15, 20, 30, 40, 50, 60, 70, 80, np.inf]
AGE_LABELS = ["<1", "1-4", "5-9", "10-14", "15-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]

SEX = {"M": "Masculino", "F": "Feminino"}
RACE = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", "5": "Indígena"}
CLASSIFICATION = {
    "1": "dengue",
    "10": "dengue",
    "2": "dengue_com_sinais_de_alarme",
    "11": "dengue_com_sinais_de_alarme",
    "3": "dengue_grave",
    "4": "dengue_grave",
    "12": "dengue_grave",
    "5": "descartado",
    "8": "inconclusivo",
    "13": "chikungunya",
}
CRITERION = {"1": "laboratorial", "2": "clinico_epidemiologico", "3": "clinico_ou_em_investigacao"}
OUTCOME = {
    "1": "cura",
    "2": "obito_por_dengue",
    "3": "obito_por_outras_causas",
    "4": "obito_em_investigacao",
}
YES_NO = {"1": "sim", "2": "nao"}
SEROTYPE = {"1": "DENV-1", "2": "DENV-2", "3": "DENV-3", "4": "DENV-4"}

SEVERE_CLASSES = frozenset({"dengue_com_sinais_de_alarme", "dengue_grave"})
CONFIRMATION_CRITERIA = frozenset({"laboratorial", "clinico_epidemiologico"})
EXCLUDED_CLASSES = frozenset({"descartado", "chikungunya"})

CATEGORY_LEVELS = {
    "sexo": [*SEX.values(), "Ignorado"],
    "raca": [*RACE.values(), "Ignorada"],
    "classificacao": [
        "dengue", "dengue_com_sinais_de_alarme", "dengue_grave", "inconclusivo", "em_investigacao",
    ],
    "criterio": [*CRITERION.values(), "ignorado"],
    "evolucao": [*OUTCOME.values(), "ignorado"],
    "hospitalizacao": ["sim", "nao", "ignorado"],
    "sorotipo": list(SEROTYPE.values()),
    "faixa_etaria": AGE_LABELS,
}

RECORD_COLUMNS = [
    "ano_arquivo", "dt_notificacao", "dt_sintomas", "dt_sintomas_imputada", "ano_epi", "semana_epi",
    "codigo_uf", "codigo_municipio", "idade_anos", "faixa_etaria", "sexo", "raca", "classificacao",
    "criterio", "evolucao", "hospitalizacao", "sorotipo", "grave", "obito",
]


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


def clean_code(series: pd.Series) -> pd.Series:
    """Remove espaços, o sufixo decimal ".0" que alguns anos gravam em códigos e textos vazios."""
    cleaned = series.str.strip().str.replace(r"^(\d+)\.0+$", r"\1", regex=True)
    return cleaned.mask(cleaned == "")


def decode(series: pd.Series, mapping: dict[str, str], default: str | None, categories: list[str] | None = None) -> pd.Series:
    """Traduz códigos do SINAN em rótulos legíveis.

    Códigos numéricos com zeros à esquerda ("01") são tratados como equivalentes ("1").
    Códigos fora do dicionário recebem o valor `default`.
    """
    codes = clean_code(series)
    normalized = codes.where(~codes.str.fullmatch(r"0+\d+", na=False), codes.str.lstrip("0"))
    decoded = normalized.map(mapping).astype("object")
    if default is not None:
        decoded = decoded.fillna(default)
    return pd.Categorical(decoded, categories=categories) if categories else decoded


def parse_date(series: pd.Series) -> pd.Series:
    """Converte datas no formato AAAA-MM-DD; valores inválidos ou fora do período viram ausentes."""
    dates = pd.to_datetime(clean_code(series), format="%Y-%m-%d", errors="coerce")
    return dates.where(dates.between(MIN_VALID_DATE, MAX_VALID_DATE))


def epidemiological_week(dates: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Calcula ano e semana epidemiológicos (padrão do Ministério da Saúde).

    A semana epidemiológica vai de domingo a sábado. A semana 1 de um ano é a que contém o dia 4
    de janeiro, ou seja, a primeira semana com ao menos quatro dias no novo ano.

    Returns:
        Par de séries (ano epidemiológico, semana epidemiológica), ausentes quando a data falta.
    """
    def first_sunday(years: np.ndarray) -> np.ndarray:
        jan4 = (years - 1970).astype("datetime64[Y]").astype("datetime64[D]") + np.timedelta64(3, "D")
        days_since_sunday = (jan4.astype("int64") + 4) % 7
        return jan4 - days_since_sunday.astype("timedelta64[D]")

    valid = dates.notna().to_numpy()
    result_year = pd.Series(pd.NA, index=dates.index, dtype="Int16")
    result_week = pd.Series(pd.NA, index=dates.index, dtype="Int8")
    if not valid.any():
        return result_year, result_week

    days = dates.to_numpy(dtype="datetime64[ns]")[valid].astype("datetime64[D]")
    years = days.astype("datetime64[Y]").astype("int64") + 1970
    years = np.where(days < first_sunday(years), years - 1, years)
    years = np.where(days >= first_sunday(years + 1), years + 1, years)
    weeks = (days - first_sunday(years)).astype("int64") // 7 + 1

    result_year[valid] = years
    result_week[valid] = weeks
    return result_year, result_week


def decode_uf(series: pd.Series) -> pd.Series:
    """Converte a UF (sigla nos arquivos até 2006, código IBGE depois) em código IBGE numérico."""
    codes = clean_code(series).str.upper()
    from_letters = codes.map(UF_CODES)
    numeric = pd.to_numeric(codes, errors="coerce")
    result = from_letters.fillna(numeric)
    return result.where(result.isin(VALID_UF_CODES)).astype("Int8")


def decode_municipality(series: pd.Series) -> pd.Series:
    """Padroniza o código IBGE do município em 6 dígitos (o SINAN não usa o dígito verificador).

    Códigos cujos dois primeiros dígitos não correspondem a uma UF válida são descartados.
    """
    codes = clean_code(series).str.slice(0, 6)
    numeric = pd.to_numeric(codes.where(codes.str.fullmatch(r"\d{6}", na=False)), errors="coerce")
    return numeric.where((numeric // 10_000).isin(VALID_UF_CODES)).astype("Int32")


def decode_age(age_code: pd.Series, birth_year: pd.Series, reference_year: pd.Series) -> pd.Series:
    """Converte a idade codificada do SINAN em anos.

    O primeiro caractere indica a unidade (1 ou H = horas, 2 ou D = dias, 3 ou M = meses,
    4 ou A = anos) e os três seguintes, o valor. Quando o código é inválido, usa-se a diferença
    entre o ano de referência e o ano de nascimento, se disponível. Idades acima de 110 anos são
    consideradas erro de digitação.
    """
    codes = clean_code(age_code).str.upper()
    codes = codes.where(codes.str.fullmatch(r"[1-4HDMA]\d{3}", na=False))
    unit = codes.str.slice(0, 1).replace(LEGACY_AGE_UNITS)
    value = pd.to_numeric(codes.str.slice(1), errors="coerce")
    divisor = unit.map(AGE_UNIT_DIVISORS).astype("float64")
    age = value.astype("float64") / divisor

    birth = pd.to_numeric(clean_code(birth_year), errors="coerce")
    from_birth = reference_year.astype("float64") - birth.astype("float64")
    age = age.fillna(from_birth)
    return age.where(age.between(0, MAX_AGE_YEARS)).astype("float32")


def normalize_sinan_week(series: pd.Series, legacy: bool) -> pd.Series:
    """Converte a semana informada pelo SINAN para AAAASS (até 2006 o formato era SSAAAA)."""
    codes = clean_code(series)
    if legacy:
        codes = codes.str.slice(2, 6) + codes.str.slice(0, 2)
    return pd.to_numeric(codes, errors="coerce").astype("Int32")


def transform(raw: pd.DataFrame, quality: dict[str, int]) -> pd.DataFrame:
    """Limpa, decodifica, filtra e enriquece um bloco de registros brutos.

    Args:
        raw: bloco produzido por `read_raw_year`.
        quality: contadores do ano, atualizados com o número de linhas removidas ou corrigidas.

    Returns:
        Bloco apenas com casos prováveis de dengue, nas colunas de `RECORD_COLUMNS`.
    """
    quality["registros_lidos"] += len(raw)

    duplicated = (clean_code(raw["duplicidade"]) == "2").fillna(False).astype(bool)
    quality["removidos_duplicidade"] += int(duplicated.sum())
    raw = raw.loc[~duplicated]

    classification = decode(raw["classificacao"], CLASSIFICATION, default="em_investigacao")
    excluded = classification.isin(EXCLUDED_CLASSES)
    quality["removidos_descartados"] += int((classification == "descartado").sum())
    quality["removidos_chikungunya"] += int((classification == "chikungunya").sum())
    raw = raw.loc[~excluded]
    classification = classification.loc[~excluded]

    records = pd.DataFrame(index=raw.index)
    records["ano_arquivo"] = raw["ano_arquivo"]
    records["dt_notificacao"] = parse_date(raw["dt_notificacao"])
    onset = parse_date(raw["dt_sintomas"])

    delay = (records["dt_notificacao"] - onset).dt.days
    implausible = onset.notna() & records["dt_notificacao"].notna() & ~delay.between(0, MAX_NOTIFICATION_DELAY_DAYS)
    onset = onset.mask(implausible)
    imputed = onset.isna() & records["dt_notificacao"].notna()
    records["dt_sintomas"] = onset.fillna(records["dt_notificacao"])
    records["dt_sintomas_imputada"] = imputed
    quality["dt_sintomas_imputada"] += int(imputed.sum())

    records["ano_epi"], records["semana_epi"] = epidemiological_week(records["dt_sintomas"])
    without_date = records["ano_epi"].isna()
    quality["removidos_sem_data"] += int(without_date.sum())

    legacy_layout = int(raw["ano_arquivo"].iloc[0]) <= LEGACY_LAST_YEAR if len(raw) else False
    sinan_week = normalize_sinan_week(raw["semana_sintomas_sinan"], legacy_layout)
    computed_week = records["ano_epi"].astype("Int32") * 100 + records["semana_epi"].astype("Int32")
    comparable = sinan_week.notna() & computed_week.notna() & ~imputed
    quality["semana_comparada"] += int(comparable.sum())
    quality["semana_divergente"] += int((comparable & (sinan_week != computed_week)).sum())

    records["codigo_uf"] = decode_uf(raw["uf_residencia"])
    quality["uf_residencia_ausente"] += int(records["codigo_uf"].isna().sum())
    records["codigo_municipio"] = decode_municipality(raw["municipio_residencia"])
    quality["municipio_residencia_ausente"] += int(records["codigo_municipio"].isna().sum())

    reference_year = records["dt_sintomas"].dt.year.fillna(records["ano_arquivo"])
    records["idade_anos"] = decode_age(raw["idade_codigo"], raw["ano_nascimento"], reference_year)
    quality["idade_ausente"] += int(records["idade_anos"].isna().sum())
    records["faixa_etaria"] = pd.cut(records["idade_anos"], bins=AGE_BINS, labels=AGE_LABELS, right=False)

    records["sexo"] = decode(raw["sexo"], SEX, "Ignorado", CATEGORY_LEVELS["sexo"])
    records["raca"] = decode(raw["raca"], RACE, "Ignorada", CATEGORY_LEVELS["raca"])
    records["classificacao"] = pd.Categorical(classification, categories=CATEGORY_LEVELS["classificacao"])
    records["criterio"] = decode(raw["criterio"], CRITERION, "ignorado", CATEGORY_LEVELS["criterio"])
    records["evolucao"] = decode(raw["evolucao"], OUTCOME, "ignorado", CATEGORY_LEVELS["evolucao"])
    records["hospitalizacao"] = decode(raw["hospitalizacao"], YES_NO, "ignorado", CATEGORY_LEVELS["hospitalizacao"])
    records["sorotipo"] = decode(raw["sorotipo"], SEROTYPE, None, CATEGORY_LEVELS["sorotipo"])

    records["grave"] = records["classificacao"].isin(SEVERE_CLASSES) & records["criterio"].isin(CONFIRMATION_CRITERIA)
    records["obito"] = (records["evolucao"] == "obito_por_dengue") & records["criterio"].isin(CONFIRMATION_CRITERIA)

    records = records.loc[~without_date]
    quality["casos_provaveis"] += len(records)
    return records[RECORD_COLUMNS].reset_index(drop=True)


QUALITY_COUNTERS = (
    "registros_lidos",
    "removidos_duplicidade",
    "removidos_descartados",
    "removidos_chikungunya",
    "removidos_sem_data",
    "casos_provaveis",
    "dt_sintomas_imputada",
    "semana_comparada",
    "semana_divergente",
    "uf_residencia_ausente",
    "municipio_residencia_ausente",
    "idade_ausente",
)


def records_path(year: int) -> Path:
    """Caminho do arquivo Parquet com os registros tratados de um ano."""
    return config.PROCESSED_DIR / "registros" / f"casos_{year}.parquet"


def quality_path(year: int) -> Path:
    """Caminho do arquivo JSON com as contagens de qualidade de um ano."""
    return records_path(year).with_suffix(".json")


def process_year(year: int) -> dict[str, int]:
    """Processa um arquivo anual completo e grava os registros tratados em Parquet.

    Returns:
        Contadores de qualidade do ano (linhas lidas, removidas e corrigidas por motivo).
    """
    quality = {key: 0 for key in QUALITY_COUNTERS}
    output = records_path(year)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(".parquet.part")

    writer: pq.ParquetWriter | None = None
    try:
        for raw in read_raw_year(year):
            table = pa.Table.from_pandas(transform(raw, quality), preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(partial, table.schema, compression="zstd")
            writer.write_table(table.cast(writer.schema))
    finally:
        if writer is not None:
            writer.close()
    partial.replace(output)
    report = {"ano_arquivo": year, **quality}
    quality_path(year).write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.info(
        "%s: %s lidos, %s casos prováveis", year, f"{quality['registros_lidos']:,}", f"{quality['casos_provaveis']:,}"
    )
    return report


def main() -> None:
    """Ponto de entrada da linha de comando."""
    parser = argparse.ArgumentParser(description="Trata as notificações de dengue do SINAN.")
    parser.add_argument("--anos", type=parse_years, default=list(config.YEARS), help="ex.: 2000-2026 ou 2019,2024")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for year in args.anos:
        process_year(year)


if __name__ == "__main__":
    main()
