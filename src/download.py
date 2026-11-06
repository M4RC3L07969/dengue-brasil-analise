"""Aquisição dos dados brutos: notificações de dengue (SINAN) e população residente (IBGE).

Todas as fontes são públicas e não exigem cadastro, chave de acesso ou autenticação.

Uso:
    python -m src.download                 # baixa tudo (SINAN 2000-2026 e IBGE)
    python -m src.download --anos 2023-2025
    python -m src.download --fonte ibge
    python -m src.download --forcar        # baixa novamente arquivos já existentes
"""

from __future__ import annotations

import argparse
import logging
import zipfile
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src import config

logger = logging.getLogger(__name__)


def build_session() -> requests.Session:
    """Cria uma sessão HTTP com novas tentativas automáticas para falhas temporárias de rede."""
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = "dengue-brasil-analise/1.0 (projeto academico)"
    return session


def remote_size(session: requests.Session, url: str) -> int | None:
    """Consulta o tamanho do arquivo remoto, em bytes, sem baixá-lo."""
    response = session.head(url, timeout=config.HTTP_TIMEOUT_SECONDS, allow_redirects=True)
    response.raise_for_status()
    length = response.headers.get("Content-Length")
    return int(length) if length else None


def is_valid_zip(path: Path) -> bool:
    """Verifica se o arquivo é um ZIP íntegro com ao menos um CSV dentro."""
    try:
        with zipfile.ZipFile(path) as archive:
            return any(name.lower().endswith(".csv") for name in archive.namelist())
    except zipfile.BadZipFile:
        return False


def download_file(session: requests.Session, url: str, destination: Path, force: bool = False) -> Path:
    """Baixa um arquivo em partes, gravando primeiro em um arquivo temporário.

    O arquivo final só é criado quando o download termina por completo, evitando que uma
    interrupção deixe um arquivo corrompido com o nome definitivo. Arquivos já baixados com o
    mesmo tamanho do servidor são reaproveitados.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected = remote_size(session, url)

    if destination.exists() and not force:
        if expected is None or destination.stat().st_size == expected:
            logger.info("Já existe, mantido: %s", destination.name)
            return destination
        logger.warning("Tamanho divergente, baixando novamente: %s", destination.name)

    partial = destination.with_suffix(destination.suffix + ".part")
    written = 0
    with session.get(url, stream=True, timeout=config.HTTP_TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=config.HTTP_CHUNK_BYTES):
                handle.write(chunk)
                written += len(chunk)

    if expected is not None and written != expected:
        raise OSError(f"Download incompleto de {url}: {written} de {expected} bytes")

    partial.replace(destination)
    logger.info("Baixado: %s (%.1f MB)", destination.name, written / 1e6)
    return destination


def download_sinan(session: requests.Session, years: list[int], force: bool = False) -> list[Path]:
    """Baixa os arquivos anuais de notificações de dengue e confere a integridade de cada ZIP."""
    paths = []
    for year in years:
        path = download_file(session, config.sinan_url(year), config.sinan_zip_path(year), force)
        if not is_valid_zip(path):
            raise OSError(f"Arquivo ZIP inválido ou sem CSV: {path}")
        paths.append(path)
    return paths


def fetch_population(session: requests.Session, level: str) -> pd.DataFrame:
    """Consulta a população residente do IBGE para todos os anos e fontes configurados.

    Args:
        session: sessão HTTP.
        level: "uf" para unidades da federação ou "municipio" para municípios.

    Returns:
        Tabela com código IBGE, nome da localidade, ano, população e origem do número.
    """
    territorial_level = config.TERRITORIAL_LEVELS[level]
    rows = []
    for source in config.POPULATION_SOURCES:
        for period in source.periods:
            url = (
                f"{config.IBGE_AGGREGATES_URL}/{source.table}/periodos/{period}"
                f"/variaveis/{source.variable}?localidades={territorial_level}[all]"
            )
            response = session.get(url, timeout=config.HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            for series in response.json()[0]["resultados"][0]["series"]:
                value = series["serie"].get(str(period))
                rows.append(
                    {
                        "codigo_ibge": series["localidade"]["id"],
                        "nome": series["localidade"]["nome"],
                        "ano": period,
                        "populacao": pd.to_numeric(value, errors="coerce"),
                        "fonte_populacao": source.label,
                        "tabela_sidra": source.table,
                    }
                )
            logger.info("População IBGE (%s) %s: tabela %s", level, period, source.table)
    return pd.DataFrame(rows).sort_values(["codigo_ibge", "ano"]).reset_index(drop=True)


def fetch_states(session: requests.Session) -> pd.DataFrame:
    """Consulta a lista oficial de unidades da federação com sigla, nome e região."""
    response = session.get(f"{config.IBGE_LOCALITIES_URL}/estados", timeout=config.HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    return pd.DataFrame(
        {
            "codigo_uf": state["id"],
            "sigla_uf": state["sigla"],
            "nome_uf": state["nome"],
            "regiao": state["regiao"]["nome"],
        }
        for state in response.json()
    ).sort_values("codigo_uf").reset_index(drop=True)


def download_ibge(session: requests.Session, force: bool = False) -> list[Path]:
    """Baixa e salva em CSV a população por UF e por município, além da tabela de UFs."""
    config.IBGE_RAW_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        config.IBGE_RAW_DIR / "estados.csv": lambda: fetch_states(session),
        config.IBGE_RAW_DIR / "populacao_uf.csv": lambda: fetch_population(session, "uf"),
        config.IBGE_RAW_DIR / "populacao_municipio.csv": lambda: fetch_population(session, "municipio"),
    }
    for path, fetch in outputs.items():
        if path.exists() and not force:
            logger.info("Já existe, mantido: %s", path.name)
            continue
        fetch().to_csv(path, index=False, encoding="utf-8")
        logger.info("Salvo: %s", path.name)
    return list(outputs)


def parse_years(text: str) -> list[int]:
    """Converte "2020-2023" ou "2019,2024" em lista de anos dentro do recorte do projeto."""
    years: set[int] = set()
    for part in text.split(","):
        if "-" in part:
            start, end = (int(value) for value in part.split("-", 1))
            years.update(range(start, end + 1))
        else:
            years.add(int(part))
    invalid = years - set(config.YEARS)
    if invalid:
        raise argparse.ArgumentTypeError(f"Anos fora do recorte {config.FIRST_YEAR}-{config.LAST_YEAR}: {sorted(invalid)}")
    return sorted(years)


def main() -> None:
    """Ponto de entrada da linha de comando."""
    parser = argparse.ArgumentParser(description="Baixa os dados brutos do projeto.")
    parser.add_argument("--anos", type=parse_years, default=list(config.YEARS), help="ex.: 2000-2026 ou 2019,2024")
    parser.add_argument("--fonte", choices=("todas", "sinan", "ibge"), default="todas")
    parser.add_argument("--forcar", action="store_true", help="baixa novamente arquivos existentes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    session = build_session()

    if args.fonte in ("todas", "ibge"):
        download_ibge(session, args.forcar)
    if args.fonte in ("todas", "sinan"):
        download_sinan(session, args.anos, args.forcar)


if __name__ == "__main__":
    main()
