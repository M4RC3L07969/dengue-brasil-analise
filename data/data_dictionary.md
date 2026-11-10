# Dicionário de dados

Este documento descreve as fontes, as variáveis originais utilizadas, as regras de tratamento e cada coluna dos conjuntos de dados processados do projeto.

## 1. Fontes e recorte

| Item | Descrição |
|---|---|
| Fonte primária | Sistema de Informação de Agravos de Notificação (SINAN) — Dengue, Ministério da Saúde. [Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue) |
| Dicionário oficial | [dic_dados_dengue.pdf](https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/dic_dados_dengue.pdf) |
| Fonte complementar | População residente — IBGE, SIDRA: tabelas 200 (Censos 2000 e 2010), 4709 (Censo 2022) e 6579 (estimativas anuais). Unidades da federação — API de Localidades do IBGE |
| Granularidade original | Uma linha por notificação individual de caso suspeito de dengue |
| Período | Anos epidemiológicos 2000 a 2026 (2026 parcial, dados até a data de extração) |
| Abrangência | Brasil — 27 unidades da federação e municípios de residência |
| Formato original | CSV (separador vírgula, codificação UTF-8) compactado em ZIP, um arquivo por ano de notificação |

## 2. Leiautes e variáveis originais

O SINAN mudou o leiaute dos arquivos ao longo do período. As colunas usadas no projeto são lidas sempre como texto, para preservar códigos com zeros à esquerda e letras, e recebem nomes padronizados.

| Anos | Nº de colunas | Particularidades |
|---|---|---|
| 2000–2006 | 107 | Sistema antigo: classificação, critério e evolução com prefixo `CON_`; UF gravada como sigla; idade com letra de unidade (`A046` = 46 anos); semana no formato SSAAAA |
| 2007–2008 | 63 | Novo leiaute do SINAN Net; UF como código IBGE; idade com dígito de unidade (`4046`) |
| 2009–2013 | 66 | Inclusão de exames NS1 e do campo `TP_SISTEMA`. Em 2008 e 2012 os códigos foram gravados com sufixo decimal (`4025.0`) |
| 2014–2026 | 119 a 121 | Nova classificação de casos (2014): dengue, dengue com sinais de alarme e dengue grave; sinais clínicos, doenças pré-existentes e ano de nascimento |

| Variável original (2007–2026) | Variável original (2000–2006) | Nome padronizado | Descrição |
|---|---|---|---|
| `DT_NOTIFIC` | `DT_NOTIFIC` | `dt_notificacao` | Data da notificação |
| `DT_SIN_PRI` | `DT_SIN_PRI` | `dt_sintomas` | Data dos primeiros sintomas |
| `SEM_PRI` | `SEM_PRI` | `semana_sintomas_sinan` | Semana epidemiológica dos primeiros sintomas calculada pelo SINAN (usada apenas para validação) |
| `SG_UF` | `SG_UF` | `uf_residencia` | UF de residência (código IBGE; sigla até 2006) |
| `ID_MN_RESI` | `ID_MN_RESI` | `municipio_residencia` | Município de residência (código IBGE) |
| `NU_IDADE_N` | `NU_IDADE` | `idade_codigo` | Idade codificada: 1º caractere = unidade (1/H hora, 2/D dia, 3/M mês, 4/A ano), demais = valor |
| `ANO_NASC` | — | `ano_nascimento` | Ano de nascimento (disponível em parte dos anos a partir de 2014) |
| `CS_SEXO` | `CS_SEXO` | `sexo` | M masculino, F feminino, I ignorado |
| `CS_RACA` | `CS_RACA` | `raca` | 1 branca, 2 preta, 3 amarela, 4 parda, 5 indígena, 9 ignorado |
| `CLASSI_FIN` | `CON_CLASSI` | `classificacao` | Classificação final do caso (ver seção 4) |
| `CRITERIO` | `CON_CRITER` | `criterio` | 1 laboratorial, 2 clínico-epidemiológico, 3 clínico/em investigação |
| `EVOLUCAO` | `CON_EVOLUC` | `evolucao` | 1 cura, 2 óbito pelo agravo, 3 óbito por outras causas, 4 óbito em investigação, 9 ignorado |
| `HOSPITALIZ` | `HOSPITALIZ` | `hospitalizacao` | 1 sim, 2 não, 9 ignorado |
| `SOROTIPO` | — | `sorotipo` | 1 DENV-1, 2 DENV-2, 3 DENV-3, 4 DENV-4 |
| `NDUPLIC_N` | `NDUPLIC` | `duplicidade` | 2 = registro duplicado (não deve ser contado) |

## 3. Regras de tratamento

| Regra | Descrição |
|---|---|
| Duplicidades | Registros com `duplicidade = 2` são removidos |
| Caso provável | Todo caso notificado, exceto os descartados (classificação 5) e os reclassificados como chikungunya (13), conforme definição do Ministério da Saúde. Alguns arquivos anuais já são publicados sem os descartados |
| Datas | Convertidas de AAAA-MM-DD; datas inválidas ou fora de 1999–2026 tornam-se ausentes |
| Data dos sintomas | Quando ausente, inválida, posterior à notificação ou mais de 365 dias anterior a ela, é substituída pela data de notificação, e o registro é marcado em `dt_sintomas_imputada` |
| Semana epidemiológica | Calculada a partir da data dos sintomas: semanas de domingo a sábado; a semana 1 é a que contém 4 de janeiro. Conferida com a semana gravada pelo SINAN |
| Idade | Convertida para anos a partir do código do SINAN; se inválida, usa-se o ano dos sintomas menos o ano de nascimento; idades acima de 110 anos são consideradas erro |
| Códigos | Espaços, sufixo decimal `.0` e zeros à esquerda são removidos antes da decodificação; códigos fora do dicionário viram "ignorado" |
| Município | Reduzido a 6 dígitos (o SINAN não usa o dígito verificador); códigos cuja UF não existe viram ausentes |
| Caso grave | Classificação "dengue com sinais de alarme" ou "dengue grave" (e os equivalentes antigos: dengue com complicações, febre hemorrágica e síndrome do choque) **e** critério laboratorial ou clínico-epidemiológico |
| Óbito | Evolução "óbito pelo agravo" **e** critério laboratorial ou clínico-epidemiológico |
| População | Anos sem dado do IBGE (2007 e 2023) são interpolados linearmente; valores interpolados são marcados em `populacao_interpolada` |
| Rastreabilidade | Toda remoção, imputação e ausência é contada por ano e motivo em `etl_log.csv` |

## 4. Classificação final

| Código | Período | Rótulo padronizado |
|---|---|---|
| 1 | até 2013 | `dengue` (dengue clássico) |
| 10 | desde 2014 | `dengue` |
| 2 | até 2013 | `dengue_com_sinais_de_alarme` (dengue com complicações) |
| 11 | desde 2014 | `dengue_com_sinais_de_alarme` |
| 3, 4 | até 2013 | `dengue_grave` (febre hemorrágica e síndrome do choque da dengue) |
| 12 | desde 2014 | `dengue_grave` |
| 8 | todo o período | `inconclusivo` |
| vazio, 0, 9 | todo o período | `em_investigacao` |
| 5 | todo o período | descartado — excluído |
| 13 | desde 2014 | chikungunya — excluído |

## 5. Registros tratados — `data/processed/registros/casos_AAAA.parquet`

Uma linha por caso provável de dengue. Um arquivo por ano de notificação (arquivo de origem), acompanhado de `casos_AAAA.json` com as contagens de qualidade do ano.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano_arquivo` | int16 | Ano do arquivo do SINAN de origem (ano de notificação) |
| `dt_notificacao` | data | Data da notificação |
| `dt_sintomas` | data | Data dos primeiros sintomas (após correção) |
| `dt_sintomas_imputada` | booleano | Verdadeiro quando a data dos sintomas foi substituída pela da notificação |
| `ano_epi` | int16 | Ano epidemiológico dos primeiros sintomas |
| `semana_epi` | int8 | Semana epidemiológica dos primeiros sintomas (1 a 53) |
| `codigo_uf` | int8 | Código IBGE da UF de residência |
| `codigo_municipio` | int32 | Código IBGE do município de residência, 6 dígitos |
| `idade_anos` | float32 | Idade em anos (frações para menores de 1 ano) |
| `faixa_etaria` | categoria | `<1`, `1-4`, `5-9`, `10-14`, `15-19`, `20-29`, `30-39`, `40-49`, `50-59`, `60-69`, `70-79`, `80+` |
| `sexo` | categoria | `Masculino`, `Feminino`, `Ignorado` |
| `raca` | categoria | `Branca`, `Preta`, `Amarela`, `Parda`, `Indígena`, `Ignorada` |
| `classificacao` | categoria | Ver seção 4 |
| `criterio` | categoria | `laboratorial`, `clinico_epidemiologico`, `clinico_ou_em_investigacao`, `ignorado` |
| `evolucao` | categoria | `cura`, `obito_por_dengue`, `obito_por_outras_causas`, `obito_em_investigacao`, `ignorado` |
| `hospitalizacao` | categoria | `sim`, `nao`, `ignorado` |
| `sorotipo` | categoria | `DENV-1` a `DENV-4`; ausente quando não identificado |
| `grave` | booleano | Caso grave (seção 3) |
| `obito` | booleano | Óbito por dengue (seção 3) |

## 6. Tabelas agregadas — `data/processed/`

Todas as tabelas são gravadas em Parquet (`.parquet`, preserva os tipos) e em CSV compactado (`.csv.gz`, UTF-8, separador vírgula). As tabelas consideram apenas casos com ano epidemiológico entre 2000 e 2026.

### Medidas comuns

| Coluna | Tipo | Descrição |
|---|---|---|
| `casos` | inteiro | Casos prováveis |
| `casos_graves` | inteiro | Casos graves |
| `obitos` | inteiro | Óbitos por dengue |
| `hospitalizados` | inteiro | Casos com hospitalização = sim |
| `hospitalizacao_informada` | inteiro | Casos com hospitalização preenchida (sim ou não), denominador para proporções |
| `confirmados_laboratorio` | inteiro | Casos com critério laboratorial |

### `casos_semana_uf`

Série semanal por UF. Chave: `ano_epi`, `semana_epi`, `codigo_uf`. Inclui `sigla_uf` (texto) e `regiao` (categoria: Norte, Nordeste, Sudeste, Sul, Centro-Oeste) e as medidas comuns.

### `casos_ano_uf`

Totais anuais por UF com taxas. Chave: `ano_epi`, `codigo_uf`.

| Coluna | Tipo | Descrição |
|---|---|---|
| `sigla_uf`, `nome_uf`, `regiao` | texto | Identificação da UF |
| medidas comuns | inteiro | Ver acima |
| `populacao` | inteiro | População residente (IBGE) |
| `populacao_interpolada` | booleano | População obtida por interpolação |
| `incidencia_100mil` | real | Casos por 100 mil habitantes |
| `letalidade_casos_provaveis` | real | Óbitos / casos prováveis × 100 (%) |
| `letalidade_casos_graves` | real | Óbitos / casos graves × 100 (%) |
| `ano_parcial` | booleano | Ano ainda não encerrado (2026) |

### `casos_ano_municipio`

Totais anuais por município de residência. Chave: `ano_epi`, `codigo_municipio`. Inclui `codigo_uf`, medidas comuns, `populacao`, `populacao_interpolada`, `incidencia_100mil`, letalidades e `ano_parcial` (mesmas definições de `casos_ano_uf`).

### `perfil_demografico`

Chave: `ano_epi`, `codigo_uf`, `faixa_etaria`, `sexo`, com as medidas comuns. Faixa etária ausente quando a idade não pôde ser determinada.

### `casos_raca_cor`

Chave: `ano_epi`, `raca`, com as medidas comuns.

### `sorotipos`

Casos com sorotipo identificado. Chave: `ano_epi`, `codigo_uf`, `sorotipo`; medida: `casos`.

### `completude`

Percentual de preenchimento dos campos-chave por ano epidemiológico.

| Coluna | Descrição |
|---|---|
| `ano_epi` | Ano epidemiológico |
| `registros` | Casos prováveis no ano |
| `pct_idade`, `pct_sexo`, `pct_raca`, `pct_municipio_residencia`, `pct_criterio`, `pct_evolucao`, `pct_hospitalizacao` | Percentual de registros com o campo preenchido (diferente de ignorado ou ausente) |
| `pct_dt_sintomas_original` | Percentual de registros com data de sintomas original (sem imputação) |

### `etl_log.csv`

Rastreabilidade do tratamento, uma linha por arquivo anual do SINAN.

| Coluna | Descrição |
|---|---|
| `ano_arquivo` | Ano do arquivo de origem |
| `registros_lidos` | Linhas lidas do arquivo bruto |
| `removidos_duplicidade` | Linhas removidas por duplicidade |
| `removidos_descartados` | Linhas removidas por serem casos descartados |
| `removidos_chikungunya` | Linhas removidas por reclassificação para chikungunya |
| `removidos_sem_data` | Linhas removidas por não terem nenhuma data válida |
| `casos_provaveis` | Linhas mantidas |
| `dt_sintomas_imputada` | Datas de sintomas substituídas pela data de notificação |
| `semana_comparada`, `semana_divergente` | Registros em que a semana calculada foi comparada à do SINAN e quantos divergiram |
| `uf_residencia_ausente`, `municipio_residencia_ausente`, `idade_ausente` | Registros mantidos sem UF, município ou idade válidos |
| `fora_do_periodo` | Casos com ano epidemiológico fora de 2000–2026 (ex.: sintomas em 1999 notificados em 2000), não incluídos nas tabelas agregadas |
| `casos_no_periodo` | Casos prováveis incluídos nas tabelas agregadas |
