# Dados brutos

Os arquivos originais não ficam versionados no repositório porque somam vários gigabytes, acima do limite de 50 MB por arquivo adotado no projeto. Eles são baixados diretamente das fontes oficiais com:

```bash
python -m src.download
```

| Pasta / arquivo | Conteúdo | Fonte |
|---|---|---|
| `sinan/DENGBRAA.csv.zip` | Notificações individuais de dengue do ano 20AA (um arquivo por ano, de 2000 a 2026) | [Portal de Dados Abertos do SUS — Sinan/Dengue](https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue) |
| `ibge/estados.csv` | Código, sigla, nome e região de cada unidade da federação | [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades) |
| `ibge/populacao_uf.csv` | População residente por UF e ano | [IBGE/SIDRA](https://sidra.ibge.gov.br) — tabelas 200, 4709 e 6579 |
| `ibge/populacao_municipio.csv` | População residente por município e ano | [IBGE/SIDRA](https://sidra.ibge.gov.br) — tabelas 200, 4709 e 6579 |

O dicionário oficial das variáveis do SINAN está disponível em <https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/dic_dados_dengue.pdf>.
