"""Métricas epidemiológicas e estatísticas usadas na análise exploratória.

Todas as funções recebem e devolvem estruturas do pandas ou do numpy e não alteram os dados
de entrada.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy import stats

POR_100_MIL = 100_000
Z_95 = stats.norm.ppf(0.975)
LIMITE_IQR = 1.5
LIMITE_ROBUSTO = 3.5
CONSTANTE_MAD = 0.6745


def incidencia(casos: pd.Series | float, populacao: pd.Series | float) -> pd.Series | float:
    """Calcula a incidência por 100 mil habitantes.

    Populações nulas ou ausentes resultam em valor ausente, nunca em divisão por zero.
    """
    if np.ndim(casos) == 0 and np.ndim(populacao) == 0:
        return float(casos) / populacao * POR_100_MIL if pd.notna(populacao) and populacao > 0 else np.nan
    populacao = pd.Series(populacao).astype("float64")
    casos = pd.Series(casos).astype("float64") if not np.ndim(casos) == 0 else float(casos)
    return casos / populacao.where(populacao > 0) * POR_100_MIL


def proporcao_com_ic(eventos: pd.Series | int, total: pd.Series | int, z: float = Z_95) -> pd.DataFrame:
    """Calcula uma proporção e seu intervalo de confiança pelo método de Wilson.

    O intervalo de Wilson é adequado para proporções muito pequenas, como a letalidade da
    dengue, em que o intervalo usual (aproximação normal) pode produzir limites negativos.

    Returns:
        Tabela com as colunas `proporcao`, `ic_inferior` e `ic_superior`, em escala de 0 a 1.
    """
    eventos = np.atleast_1d(np.asarray(eventos, dtype="float64"))
    total = np.atleast_1d(np.asarray(total, dtype="float64"))
    with np.errstate(divide="ignore", invalid="ignore"):
        p = eventos / total
        denominador = 1 + z**2 / total
        centro = (p + z**2 / (2 * total)) / denominador
        margem = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominador
    valido = total > 0
    return pd.DataFrame(
        {
            "proporcao": np.where(valido, p, np.nan),
            "ic_inferior": np.where(valido, np.where(eventos > 0, np.clip(centro - margem, 0, 1), 0.0), np.nan),
            "ic_superior": np.where(valido, np.clip(centro + margem, 0, 1), np.nan),
        }
    )


def curva_lorenz(valores: Sequence[float], pesos: Sequence[float] | None = None) -> pd.DataFrame:
    """Calcula a curva de Lorenz (ou curva de concentração quando há pesos).

    As unidades são ordenadas da menor para a maior razão valor/peso. Com a população como peso,
    a curva mostra que fração dos casos se concentra em que fração da população.

    Returns:
        Tabela com `pop_acumulada` e `valor_acumulado`, ambas de 0 a 1, começando em (0, 0).
    """
    valores = np.asarray(valores, dtype="float64")
    pesos = np.ones_like(valores) if pesos is None else np.asarray(pesos, dtype="float64")
    validos = np.isfinite(valores) & np.isfinite(pesos) & (pesos > 0) & (valores >= 0)
    valores, pesos = valores[validos], pesos[validos]
    if valores.sum() == 0:
        raise ValueError("A soma dos valores precisa ser positiva para calcular a curva de Lorenz.")

    ordem = np.argsort(valores / pesos, kind="stable")
    pop_acumulada = np.concatenate([[0.0], np.cumsum(pesos[ordem]) / pesos.sum()])
    valor_acumulado = np.concatenate([[0.0], np.cumsum(valores[ordem]) / valores.sum()])
    return pd.DataFrame({"pop_acumulada": pop_acumulada, "valor_acumulado": valor_acumulado})


def gini(valores: Sequence[float], pesos: Sequence[float] | None = None) -> float:
    """Calcula o índice de Gini a partir da área sob a curva de Lorenz.

    Varia de 0 (casos distribuídos exatamente como a população) a 1 (todos os casos em uma
    única unidade). Unidades sem casos devem ser incluídas com valor zero.
    """
    curva = curva_lorenz(valores, pesos)
    area = np.trapezoid(curva["valor_acumulado"], curva["pop_acumulada"])
    return float(1 - 2 * area)


def canal_endemico(
    serie: pd.DataFrame,
    anos_base: Sequence[int],
    coluna: str = "incidencia",
    excluir_semana_53: bool = True,
) -> pd.DataFrame:
    """Constrói o canal endêmico (diagrama de controle) por semana epidemiológica.

    Para cada semana, calcula o primeiro quartil, a mediana e o terceiro quartil da série nos
    anos de referência. Semanas acima do terceiro quartil indicam incidência acima do esperado
    (zona de alerta ou epidemia), conforme a metodologia usada pela vigilância epidemiológica.

    Args:
        serie: tabela com `ano_epi`, `semana_epi` e a coluna de valores.
        anos_base: anos usados como referência do comportamento esperado.
        coluna: nome da coluna de valores.
        excluir_semana_53: descarta a semana 53, que só existe em alguns anos.

    Returns:
        Tabela indexada pela semana com `q1`, `mediana` e `q3`.
    """
    base = serie[serie["ano_epi"].isin(anos_base)]
    if excluir_semana_53:
        base = base[base["semana_epi"] <= 52]
    quartis = base.groupby("semana_epi")[coluna].quantile([0.25, 0.5, 0.75]).unstack()
    quartis.columns = ["q1", "mediana", "q3"]
    return quartis


def atipicos_iqr(serie: pd.Series, limite: float = LIMITE_IQR) -> pd.Series:
    """Marca valores atípicos pela regra do intervalo interquartil (regra de Tukey).

    Um valor é atípico quando fica abaixo de Q1 - 1,5 × IQR ou acima de Q3 + 1,5 × IQR.
    """
    q1, q3 = serie.quantile([0.25, 0.75])
    amplitude = q3 - q1
    return (serie < q1 - limite * amplitude) | (serie > q3 + limite * amplitude)


def escore_robusto(serie: pd.Series) -> pd.Series:
    """Calcula o escore-z modificado, baseado na mediana e no desvio absoluto mediano (MAD).

    Ao contrário do escore-z comum, não é distorcido pelos próprios valores extremos.
    """
    mediana = serie.median()
    mad = (serie - mediana).abs().median()
    if mad == 0:
        return pd.Series(0.0, index=serie.index)
    return CONSTANTE_MAD * (serie - mediana) / mad


def atipicos_robustos(serie: pd.Series, limite: float = LIMITE_ROBUSTO) -> pd.Series:
    """Marca valores atípicos com escore-z modificado acima de 3,5 em módulo (Iglewicz e Hoaglin)."""
    return escore_robusto(serie).abs() > limite


def resumo_descritivo(serie: pd.Series) -> pd.Series:
    """Resume a distribuição: posição, dispersão e forma."""
    return pd.Series(
        {
            "n": serie.count(),
            "media": serie.mean(),
            "mediana": serie.median(),
            "desvio_padrao": serie.std(),
            "coef_variacao": serie.std() / serie.mean() if serie.mean() else np.nan,
            "minimo": serie.min(),
            "q1": serie.quantile(0.25),
            "q3": serie.quantile(0.75),
            "maximo": serie.max(),
            "assimetria": serie.skew(),
        }
    )


def risco_relativo(eventos_a: int, total_a: int, eventos_b: int, total_b: int, z: float = Z_95) -> dict[str, float]:
    """Calcula o risco relativo do grupo A em relação ao grupo B, com intervalo de confiança de 95%.

    O intervalo é obtido na escala logarítmica (método de Katz).
    """
    risco_a, risco_b = eventos_a / total_a, eventos_b / total_b
    rr = risco_a / risco_b
    erro = np.sqrt(1 / eventos_a - 1 / total_a + 1 / eventos_b - 1 / total_b)
    return {
        "risco_relativo": rr,
        "ic_inferior": float(np.exp(np.log(rr) - z * erro)),
        "ic_superior": float(np.exp(np.log(rr) + z * erro)),
    }
