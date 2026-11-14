"""Identidade visual comum às figuras estáticas (Matplotlib/Seaborn) e interativas (Plotly).

Centraliza paleta, tipografia, formatação de números em português e a exportação das figuras
para `docs/assets`, garantindo que todas as visualizações do artigo sigam o mesmo padrão.

A paleta categórica foi validada para daltonismo (protanopia, deuteranopia e tritanopia) na
ordem em que as cores são atribuídas; por isso cada entidade (região, sexo, sorotipo) tem cor
fixa, que não muda entre gráficos.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

from src import config

FIGURAS_DIR = config.ASSETS_DIR / "figuras"
INTERATIVOS_DIR = config.ASSETS_DIR / "interativos"
DPI = 200
MARGEM_INFERIOR_PADRAO = 50
MARGEM_SUPERIOR_INCORPORADA = 24

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_SUAVE = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
NEUTRO = "#c3c2b7"
DESTAQUE = "#e34948"

CATEGORICA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQUENCIAL = ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
CORES_REGIAO = dict(zip(REGIOES, CATEGORICA[: len(REGIOES)], strict=True))
CORES_SEXO = {"Feminino": CATEGORICA[0], "Masculino": CATEGORICA[1]}
SOROTIPOS = ["DENV-1", "DENV-2", "DENV-3", "DENV-4"]
CORES_SOROTIPO = dict(zip(SOROTIPOS, CATEGORICA[: len(SOROTIPOS)], strict=True))

FONTE_SINAN = "Fonte: Ministério da Saúde — SINAN/Dengue; IBGE — população residente. Elaboração própria."

MAPA_SEQUENCIAL = LinearSegmentedColormap.from_list("dengue_azul", SEQUENCIAL)
ESCALA_PLOTLY = [[i / (len(SEQUENCIAL) - 1), cor] for i, cor in enumerate(SEQUENCIAL)]


def formatar_numero(valor: float, casas: int = 0) -> str:
    """Formata um número no padrão brasileiro: ponto como separador de milhar e vírgula decimal."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def formatar_compacto(valor: float) -> str:
    """Abrevia números grandes em português: 6.564.941 vira "6,6 mi" e 12.500 vira "12,5 mil"."""
    absoluto = abs(valor)
    if absoluto >= 1e6:
        return f"{formatar_numero(valor / 1e6, 1)} mi"
    if absoluto >= 1e3:
        return f"{formatar_numero(valor / 1e3, 1 if absoluto < 1e5 else 0)} mil"
    return formatar_numero(valor, 0)


def formatar_percentual(valor: float, casas: int = 1) -> str:
    """Formata uma proporção já em escala de 0 a 100 como percentual em português."""
    return f"{formatar_numero(valor, casas)}%"


EIXO_NUMERICO = FuncFormatter(lambda valor, _: formatar_numero(valor, 0))
EIXO_COMPACTO = FuncFormatter(lambda valor, _: formatar_compacto(valor))
EIXO_PERCENTUAL = FuncFormatter(lambda valor, _: formatar_percentual(valor, 0))


def configurar_matplotlib() -> None:
    """Aplica o tema visual do projeto às figuras do Matplotlib e do Seaborn."""
    mpl.rcParams.update(
        {
            "figure.facecolor": SUPERFICIE,
            "axes.facecolor": SUPERFICIE,
            "savefig.facecolor": SUPERFICIE,
            "figure.dpi": 110,
            "savefig.dpi": DPI,
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
            "font.size": 10,
            "text.color": TINTA,
            "axes.labelcolor": TINTA_SECUNDARIA,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.titlepad": 12,
            "axes.labelsize": 10,
            "axes.edgecolor": EIXO,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "axes.prop_cycle": mpl.cycler(color=CATEGORICA),
            "grid.color": GRADE,
            "grid.linewidth": 0.6,
            "grid.linestyle": "-",
            "xtick.color": TINTA_SUAVE,
            "ytick.color": TINTA_SUAVE,
            "xtick.labelcolor": TINTA_SECUNDARIA,
            "ytick.labelcolor": TINTA_SECUNDARIA,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "lines.linewidth": 2,
            "axes.formatter.use_locale": False,
        }
    )


def configurar_plotly() -> None:
    """Registra e ativa o tema visual do projeto para os gráficos do Plotly."""
    eixo = {
        "gridcolor": GRADE,
        "linecolor": EIXO,
        "zeroline": False,
        "ticks": "",
        "tickfont": {"color": TINTA_SECUNDARIA},
        "title": {"font": {"color": TINTA_SECUNDARIA}, "standoff": 10},
        "automargin": True,
    }
    pio.templates["dengue"] = go.layout.Template(
        layout={
            "font": {"family": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif", "color": TINTA, "size": 13},
            "paper_bgcolor": SUPERFICIE,
            "plot_bgcolor": SUPERFICIE,
            "colorway": CATEGORICA,
            "separators": ",.",
            "title": {"x": 0, "xanchor": "left", "font": {"size": 16}},
            "xaxis": eixo,
            "yaxis": eixo,
            "hoverlabel": {"bgcolor": "#ffffff", "bordercolor": EIXO, "font": {"color": TINTA}},
            "hovermode": "x unified",
            "legend": {"orientation": "h", "y": -0.18, "x": 0, "title": {"text": ""}},
            "margin": {"l": 60, "r": 20, "t": 70, "b": MARGEM_INFERIOR_PADRAO},
        }
    )
    pio.templates.default = "dengue"


def adicionar_fonte(fig: plt.Figure, texto: str = FONTE_SINAN) -> None:
    """Escreve a fonte dos dados logo abaixo de todo o conteúdo da figura do Matplotlib.

    A posição é calculada a partir da área efetivamente ocupada (incluindo rótulos de eixo
    girados e legendas externas), para que o texto nunca se sobreponha ao gráfico.
    """
    area = fig.get_tightbbox(fig.canvas.get_renderer())
    largura, altura = fig.get_size_inches()
    fig.text(area.x0 / largura, (area.y0 - 0.1) / altura, texto, fontsize=7.5, color=TINTA_SUAVE, ha="left", va="top")


def salvar_figura(fig: plt.Figure, nome: str, fonte: str | None = FONTE_SINAN) -> Path:
    """Adiciona a fonte, ajusta margens e salva a figura estática em PNG de alta resolução."""
    FIGURAS_DIR.mkdir(parents=True, exist_ok=True)
    if fonte:
        adicionar_fonte(fig, fonte)
    caminho = FIGURAS_DIR / f"{nome}.png"
    fig.savefig(caminho, dpi=DPI, bbox_inches="tight", pad_inches=0.25, metadata={"Software": None})
    return caminho


def salvar_interativo(fig: go.Figure, nome: str, fonte: str | None = FONTE_SINAN) -> Path:
    """Salva um gráfico do Plotly como página HTML leve (plotly.js carregado por CDN).

    A página ocupa toda a largura disponível e se ajusta ao tamanho da tela, para ser incorporada
    ao artigo por meio de um iframe. O título é retirado da versão exportada, porque no artigo ele
    aparece na legenda da figura, o que evita títulos cortados em telas de celular. A fonte dos
    dados é escrita como texto HTML abaixo do gráfico, para quebrar linha em telas estreitas.
    """
    INTERATIVOS_DIR.mkdir(parents=True, exist_ok=True)
    fig = go.Figure(fig)
    fig.update_layout(title=None, margin_t=MARGEM_SUPERIOR_INCORPORADA)
    caminho = INTERATIVOS_DIR / f"{nome}.html"
    html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=True,
        default_width="100%",
        config={"responsive": True, "displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
    )
    estilo = (
        f"<style>html,body{{margin:0;background:{SUPERFICIE};}}"
        f".fonte{{font:12px system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;color:{TINTA_SUAVE};margin:4px 12px 8px;}}</style>"
    )
    rodape = f'<p class="fonte">{fonte}</p>' if fonte else ""
    html = html.replace("<head>", f'<head><meta name="viewport" content="width=device-width, initial-scale=1">{estilo}', 1)
    html = html.replace("</body>", f"{rodape}</body>", 1)
    caminho.write_text(html, encoding="utf-8")
    return caminho
