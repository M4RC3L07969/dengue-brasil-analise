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
│   └── data_dictionary.md     # dicionário de variáveis
├── notebooks/
│   └── analise_exploratoria.ipynb
├── src/
│   ├── __init__.py
│   └── etl.py
└── docs/                      # artigo publicado no GitHub Pages
    ├── index.html
    └── assets/
```

## Licença

Código sob licença [MIT](LICENSE). Dados processados, figuras e texto sob [CC BY 4.0](LICENSE-CC-BY-4.0.md).
