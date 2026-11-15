# Dengue no Brasil (2000–2026): análise e visualização de dados do SINAN

[![Artigo](https://img.shields.io/badge/artigo-GitHub%20Pages-1e3a8a)](https://m4rc3l07969.github.io/dengue-brasil-analise/)
[![Python](https://img.shields.io/badge/python-3.12%2B-2a78d6)](requirements.txt)
[![Código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-2a78d6)](LICENSE)
[![Dados e texto: CC BY 4.0](https://img.shields.io/badge/dados%20e%20texto-CC%20BY%204.0-2a78d6)](LICENSE-CC-BY-4.0.md)
[![Fonte: SINAN](https://img.shields.io/badge/fonte-SINAN%20%2F%20IBGE-4b5563)](https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue)
[![FAIR](https://img.shields.io/badge/FAIR-F%C2%B7A%C2%B7I%C2%B7R-4b5563)](#princípios-fair)

- **Autor:** Marcelo de Moura Maia Júnior
- **Instituição:** Centro Universitário La Salle do Rio de Janeiro (Unilasalle-RJ)
- **Curso:** Bacharelado em Sistemas de Informação — 6º período
- **Disciplina:** Linguagens de Programação (Análise e Visualização de Dados com Python) — 2026.2

**Artigo completo, com gráficos interativos: <https://m4rc3l07969.github.io/dengue-brasil-analise/>**

## Resumo

A dengue é a arbovirose de maior impacto no Brasil, e 2024 registrou a maior epidemia da série histórica. Este projeto analisa todas as notificações de dengue do Sistema de Informação de Agravos de Notificação (SINAN) entre 2000 e 2026, combinadas à população residente do IBGE. Um pipeline reprodutível em Python lê 32,5 milhões de registros publicados em quatro leiautes diferentes, padroniza códigos, trata datas e idades inconsistentes com registro de cada remoção e gera 26,4 milhões de casos prováveis, tabelas analíticas em Parquet e CSV, um notebook de análise exploratória e um artigo acadêmico em HTML.

**Palavras-chave:** dengue; vigilância epidemiológica; SINAN; análise exploratória de dados; ciência aberta.

## Perguntas de pesquisa

- **RQ1 — Tempo:** como a incidência de dengue evoluiu entre 2000 e 2026, qual é o padrão sazonal ao longo do ano e em que medida a epidemia de 2024 se afasta do comportamento histórico?
- **RQ2 — Espaço:** como os casos se distribuem entre regiões, estados e municípios, quão concentrada é essa distribuição e houve expansão para áreas antes pouco afetadas?
- **RQ3 — Pessoas e gravidade:** como idade e sexo se relacionam com a ocorrência, a hospitalização, a gravidade e o óbito, e quais sorotipos circularam no período?

## Principais resultados

- **2024 foi um ponto fora da curva:** 6.564.941 casos prováveis e incidência de 3.088 por 100 mil habitantes, 3,8 vezes o recorde anterior (2015). O pico, porém, ocorreu na janela sazonal de sempre: 63,3% dos casos de todo o período se concentram entre as semanas epidemiológicas 8 e 20 (fevereiro a meados de maio).
- **Expansão para o Sul:** a região passou de 0,3% dos casos do país em 2004 para 29,4% em 2020 e, em 2023, teve pela primeira vez a maior incidência entre as cinco regiões.
- **Menos concentração:** o índice de Gini dos casos entre municípios caiu de 0,89 (2000) para 0,62 (2024), e a proporção de municípios com casos subiu de 30,5% para 98,5%.
- **Idosos concentram os óbitos:** o risco de óbito aos 80 anos ou mais foi 56 vezes o da faixa de 20 a 29 anos; pessoas com 60 anos ou mais somaram 12,7% dos casos e 57,8% dos óbitos (2014–2025).
- **Retorno do DENV-3:** o sorotipo, praticamente ausente desde 2010, passou de 0,9% dos casos tipados em 2024 para 29,8% em 2026.

Os números são gerados pelo notebook e ficam registrados em [`docs/assets/dados/metricas.json`](docs/assets/dados/metricas.json).

## Fontes dos dados

| Dado | Fonte | Acesso |
|---|---|---|
| Notificações de dengue, 2000–2026 (um arquivo CSV por ano) | Ministério da Saúde — SINAN, [Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue) | Arquivos `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBRAA.csv.zip` |
| Dicionário oficial das variáveis | Ministério da Saúde — SINAN | [dic_dados_dengue.pdf](https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/dic_dados_dengue.pdf) |
| População residente por UF e município | IBGE — [SIDRA](https://sidra.ibge.gov.br), tabelas 200, 4709 e 6579 | [API de Agregados](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3) |
| Unidades da federação e malha geográfica | IBGE | [API de Localidades](https://servicodados.ibge.gov.br/api/docs/localidades) e [API de Malhas](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3) |

Todas as fontes são públicas e acessadas sem cadastro ou chave. Os dados brutos não são versionados (somam cerca de 8 GB) e são baixados por `python -m src.download`.

## Estrutura do repositório

```
dengue-brasil-analise/
├── README.md
├── LICENSE                    # MIT (código)
├── LICENSE-CC-BY-4.0.md       # CC BY 4.0 (dados processados e texto)
├── CITATION.cff               # metadados de citação
├── requirements.txt           # dependências com versões fixas
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

O download completo (27 arquivos anuais do SINAN, 2000–2026) soma cerca de 800 MB compactados e 8 GB descompactados. Os arquivos são lidos em blocos, sem descompactar em disco, e o tratamento completo leva alguns minutos em um computador comum. Para trabalhar com parte do período: `python -m src.download --anos 2023-2025` e `python -m src.etl --anos 2023-2025`.

A reprodução foi verificada a partir de um clone limpo, em um ambiente virtual novo: o tratamento e o notebook regeneraram registros, tabelas, figuras e métricas idênticos aos versionados.

As regras de limpeza, as definições de caso provável, caso grave e óbito e a descrição de cada coluna estão no [dicionário de dados](data/data_dictionary.md).

## Princípios FAIR

| Princípio | Como é atendido |
|---|---|
| **Findable** (localizável) | Este README com resumo, palavras-chave, perguntas de pesquisa e autoria; links permanentes para as fontes oficiais; metadados de citação em [`CITATION.cff`](CITATION.cff) |
| **Accessible** (acessível) | Repositório e artigo públicos; dados brutos baixados das fontes oficiais por script, sem cadastro, chave ou dependência paga |
| **Interoperable** (interoperável) | [Dicionário de dados](data/data_dictionary.md) com cada variável, tipo e formato; dados processados em Apache Parquet e CSV compactado; métricas em JSON |
| **Reusable** (reutilizável) | Licenças MIT (código) e CC BY 4.0 (dados, figuras e texto); `requirements.txt` com versões fixas; rastreabilidade de cada linha removida em [`etl_log.csv`](data/processed/etl_log.csv) |

## Como citar

> MAIA JÚNIOR, Marcelo de Moura. *Dengue no Brasil (2000–2026): evolução temporal, expansão geográfica e perfil de gravidade a partir de 26 milhões de notificações do SINAN*. Rio de Janeiro: Centro Universitário La Salle do Rio de Janeiro (Unilasalle-RJ), 2026. Disponível em: <https://m4rc3l07969.github.io/dengue-brasil-analise/>.

O GitHub também gera a citação em outros formatos pelo botão **Cite this repository**, a partir do arquivo [`CITATION.cff`](CITATION.cff).

## Licença

Código sob licença [MIT](LICENSE). Dados processados, figuras e texto sob [CC BY 4.0](LICENSE-CC-BY-4.0.md). Os dados brutos pertencem às fontes oficiais e seguem os respectivos termos de uso.
