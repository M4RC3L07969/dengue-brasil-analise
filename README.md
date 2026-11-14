# Dengue no Brasil (2000–2026): análise e visualização de dados do SINAN

- **Autor:** Marcelo de Moura Maia Júnior
- **Instituição:** Centro Universitário La Salle do Rio de Janeiro (Unilasalle-RJ)
- **Curso:** Bacharelado em Sistemas de Informação — 6º período
- **Disciplina:** Linguagens de Programação (Análise e Visualização de Dados com Python) — 2026.2

Estudo exploratório das notificações de dengue registradas no Sistema de Informação de Agravos de Notificação (SINAN) entre 2000 e 2026, combinadas com a população residente do IBGE, com foco na evolução temporal, na distribuição geográfica e na gravidade dos casos.

> Projeto em desenvolvimento.

## Estrutura do repositório

```
dengue-brasil-analise/
├── README.md
├── LICENSE                    # MIT (código)
├── LICENSE-CC-BY-4.0.md       # CC BY 4.0 (dados processados e texto)
├── requirements.txt
├── data/
│   ├── raw/                   # dados brutos (baixados por script, não versionados)
│   ├── processed/             # dados tratados prontos para análise
│   │   ├── registros/         # casos prováveis por ano (Parquet)
│   │   └── etl_log.csv        # rastreabilidade de remoções e correções
│   └── data_dictionary.md     # dicionário de variáveis
├── notebooks/
│   └── analise_exploratoria.ipynb
├── src/
│   ├── __init__.py
│   ├── config.py              # caminhos, recorte temporal e endereços das fontes
│   ├── download.py            # aquisição dos dados brutos (SINAN e IBGE)
│   ├── etl.py                 # leitura, limpeza, padronização e agregação
│   ├── metricas.py            # incidência, intervalos de confiança, Gini, canal endêmico
│   ├── populacao.py           # população residente usada nas taxas
│   └── visualizacao.py        # paleta, tema e exportação das figuras
└── docs/                      # artigo publicado no GitHub Pages
    ├── index.html
    └── assets/
        ├── figuras/           # figuras estáticas (PNG, 200 dpi)
        ├── interativos/       # gráficos interativos (Plotly, HTML)
        └── dados/metricas.json  # números-chave citados no artigo
```

## Como reproduzir

Requisitos: Python 3.12 ou superior e Git.

```bash
git clone https://github.com/M4RC3L07969/dengue-brasil-analise.git
cd dengue-brasil-analise
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.download           # baixa os dados brutos do SINAN e do IBGE
python -m src.etl                # trata os dados e gera as tabelas em data/processed/
jupyter nbconvert --to notebook --execute --inplace notebooks/analise_exploratoria.ipynb
```

O último comando executa a análise exploratória do início ao fim e regenera todas as figuras em `docs/assets/`. Para explorar o notebook de forma interativa: `jupyter notebook notebooks/analise_exploratoria.ipynb`.

O download completo (27 arquivos anuais do SINAN, 2000–2026) soma cerca de 800 MB compactados e 7 GB descompactados. Os arquivos são lidos em blocos, sem descompactar em disco, e o tratamento completo leva alguns minutos em um computador comum. Para trabalhar com parte do período: `python -m src.download --anos 2023-2025` e `python -m src.etl --anos 2023-2025`.

As regras de limpeza, as definições de caso provável, caso grave e óbito e a descrição de cada coluna estão no [dicionário de dados](data/data_dictionary.md).

## Licença

Código sob licença [MIT](LICENSE). Dados processados, figuras e texto sob [CC BY 4.0](LICENSE-CC-BY-4.0.md).
