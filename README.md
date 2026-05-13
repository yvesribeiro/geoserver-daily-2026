# Auditor automático dos dados STPC/DF - SEMOB

Automação em Python para monitorar diariamente camadas públicas do GeoServer da SEMOB/DF, salvar snapshots locais, comparar a base atual com a última base equivalente e gerar um comunicado objetivo para acompanhamento de alterações cadastrais e operacionais relevantes.

O projeto foi pensado para uma rotina de auditoria simples: baixar os dados, normalizar os arquivos, comparar com o histórico local e informar se houve mudança nas camadas acompanhadas.

## O que a automação faz

A cada execução, o sistema:

1. identifica a data atual no fuso `America/Sao_Paulo`;
2. classifica o dia como `util`, `sabado` ou `domingo`;
3. baixa as camadas configuradas via WFS do GeoServer;
4. salva os snapshots brutos em `data/snapshots/`;
5. gera versões normalizadas em `data/normalized/`;
6. procura o snapshot anterior do mesmo tipo de dia;
7. compara a base atual com a base anterior equivalente;
8. salva os arquivos detalhados de diferença em `data/diffs/`;
9. gera um relatório em Markdown em `data/reports/`;
10. envia o resumo ao Microsoft Teams, se essa opção estiver habilitada.

A comparação por tipo de dia evita comparar bases que naturalmente têm comportamento diferente. Assim, um dia útil é comparado com o último dia útil disponível, um sábado com o último sábado disponível e um domingo com o último domingo disponível.

## Camadas monitoradas

Atualmente, o arquivo `config/layers.yaml` monitora quatro camadas:

| Camada | Origem GeoServer | Tipo de arquivo | Principal objetivo |
|---|---|---:|---|
| Frota por Operadora | `semob:Frota por Operadora` | CSV | Verificar inclusão, remoção e alteração cadastral de veículos |
| Viagens Programadas por Linha | `semob:Viagens Programadas por Linha` | CSV | Verificar inclusão e remoção de viagens programadas |
| Ponto de paradas 2025 | `semob:ponto_parada_v2025` | GeoJSON | Verificar inclusão, remoção, alteração cadastral e mudança de localização de pontos |
| Itinerário Espacial das Linhas | `semob:itinerario_espacial` | GeoJSON | Verificar inclusão, remoção, alteração cadastral e mudança de trajeto de linhas |

## Regras de comparação

As regras ficam centralizadas no arquivo:

```text
config/layers.yaml
```

### Frota por Operadora

A chave de comparação é:

```text
numero_veiculo
```

A automação identifica:

- veículos adicionados;
- veículos removidos;
- veículos com alteração cadastral.

No relatório, o resumo de frota é agrupado por operadora e detalhado por:

- `tipo_onibus`;
- `ano_fabrica`.

Algumas colunas são ignoradas na comparação cadastral para evitar falso positivo, como `FID`, `id_frota` e `data_referencia`.

### Viagens Programadas por Linha

A chave de comparação é composta por:

```text
sg_operadora
cd_linha
cs_sentido
hora_prevista
tipo_dia_operacional
```

Antes da comparação, a base é filtrada conforme o tipo de dia da execução:

- dia útil: considera viagens ativas em `st_segunda`, `st_terca`, `st_quarta`, `st_quinta` ou `st_sexta`;
- sábado: considera viagens ativas em `st_sabado`;
- domingo: considera viagens ativas em `st_domingo`.

Como o horário faz parte da chave, uma mudança de horário aparece operacionalmente como uma viagem removida e uma viagem adicionada. O relatório apresenta os totais por operadora, linha e sentido.

### Ponto de paradas 2025

A chave de comparação é:

```text
cod_parada_v2025
```

A automação identifica:

- pontos adicionados;
- pontos removidos;
- pontos com localização alterada;
- pontos com dados cadastrais alterados.

A comparação de geometria é feita pela representação WKT da geometria normalizada. Como a tolerância configurada é zero, qualquer diferença geométrica entre os snapshots é considerada alteração.

### Itinerário Espacial das Linhas

A chave de comparação é composta por:

```text
id_linha
lin_sentido
```

A automação identifica:

- itinerários adicionados;
- itinerários removidos;
- itinerários com trajeto alterado;
- itinerários com dados cadastrais alterados.

A comparação de geometria também usa tolerância zero. Portanto, qualquer diferença no traçado salvo no GeoJSON é considerada alteração de trajeto.

## Estrutura do projeto

```text
geoserver-daily-2026/
  config/
    layers.yaml
    teams_webhook.env          # arquivo local, não versionado

  data/
    snapshots/                 # snapshots brutos baixados do GeoServer
    normalized/                # snapshots tratados para comparação
    diffs/                     # arquivos detalhados das diferenças
    reports/                   # relatórios em Markdown
    logs/                      # pasta reservada para logs locais

  src/
    calendar_utils.py          # data, tipo de dia e busca de snapshot anterior
    comparator_geo.py          # comparação de camadas GeoJSON
    comparator_table.py        # comparação de camadas CSV
    config_loader.py           # leitura do layers.yaml
    downloader.py              # download WFS das camadas
    inspect_snapshots.py       # inspeção dos snapshots baixados
    main.py                    # orquestração da rotina diária
    normalizer.py              # limpeza e padronização dos dados
    reporter.py                # geração do relatório textual
    teams.py                   # envio do relatório ao Microsoft Teams
    validate_config.py         # validação das colunas configuradas

  requirements.txt
  README.md
```

## Requisitos

- Python 3.10 ou superior;
- Windows, Linux ou macOS;
- acesso à internet para consultar o GeoServer;
- dependências listadas em `requirements.txt`.

Principais bibliotecas utilizadas:

- `pandas`;
- `requests`;
- `PyYAML`;
- `python-dotenv`;
- `geopandas`;
- `shapely`;
- `pyogrio`.

## Instalação no Windows com Git Bash

Entre na pasta onde deseja manter a automação. Exemplo:

```bash
cd /d/Automacoes
```

Clone o repositório ou acesse a pasta do projeto:

```bash
git clone <URL_DO_REPOSITORIO>
cd geoserver-daily-2026
```

Crie o ambiente virtual:

```bash
py -m venv .venv
```

Ative o ambiente virtual:

```bash
source .venv/Scripts/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Teste se as principais bibliotecas foram instaladas:

```bash
python -c "import pandas, requests, yaml, geopandas, shapely; print('OK')"
```

Se o terminal imprimir `OK`, a instalação básica está funcionando.

## Configuração

### 1. Configurar camadas

As camadas, chaves, agrupamentos e regras de comparação ficam em:

```text
config/layers.yaml
```

Esse arquivo controla:

- nome da camada no GeoServer;
- formato de download (`csv` ou `geojson`);
- colunas de chave;
- colunas de agrupamento;
- colunas ignoradas na comparação;
- regras específicas por camada;
- envio ou não do relatório ao Teams.

### 2. Configurar envio ao Teams

O envio ao Teams é opcional.

Crie o arquivo local:

```text
config/teams_webhook.env
```

Com o conteúdo:

```env
TEAMS_WEBHOOK_URL=https://sua-url-do-webhook
```

Esse arquivo não deve ser enviado ao GitHub, pois contém uma URL sensível.

No arquivo `config/layers.yaml`, controle o envio por meio de:

```yaml
output:
  send_teams: true
```

Para rodar sem enviar mensagem ao Teams, altere para:

```yaml
output:
  send_teams: false
```

> Observação: se `send_teams` estiver como `true` e o arquivo `config/teams_webhook.env` não existir ou estiver vazio, a rotina ainda gera o relatório local, mas exibirá erro no envio ao Teams.

## Execução manual

Com o ambiente virtual ativado, execute:

```bash
python src/main.py
```

Durante a execução, o terminal mostra:

- camada processada;
- URL WFS chamada;
- caminho do snapshot bruto;
- caminho do snapshot normalizado;
- snapshot anterior usado na comparação;
- totais de adicionados, removidos e alterados;
- caminho do relatório final;
- status do envio ao Teams.

## Primeira execução

Na primeira execução, é normal a comparação ser ignorada, porque ainda não existe snapshot anterior do mesmo tipo de dia.

Exemplo:

```text
Comparação: ignorada, pois não há snapshot anterior.
```

A comparação começa a funcionar quando houver pelo menos dois snapshots do mesmo tipo de dia para a mesma camada.

## Arquivos gerados

### Snapshots brutos

Ficam em:

```text
data/snapshots/<camada>/
```

Exemplo:

```text
data/snapshots/frota_operadora/2026-05-13_util.csv
```

### Snapshots normalizados

Ficam em:

```text
data/normalized/<camada>/
```

Esses arquivos são os usados na comparação. A normalização reduz falso positivo causado por espaços, valores nulos, duplicidades simples e ordenação instável.

### Diferenças detalhadas

Ficam em:

```text
data/diffs/<data>_<tipo_dia>/<camada>/
```

Exemplos para camadas tabulares:

```text
frota_operadora_adicionados.csv
frota_operadora_removidos.csv
frota_operadora_alteracoes_atributos.csv
```

Exemplos para camadas espaciais:

```text
ponto_parada_v2025_adicionados.geojson
ponto_parada_v2025_removidos.geojson
ponto_parada_v2025_alteracoes_geometria.csv
ponto_parada_v2025_alteracoes_atributos.csv
```

### Relatórios

Ficam em:

```text
data/reports/
```

Exemplo:

```text
2026-05-13_util.md
```

O relatório é formatado para leitura executiva e pode ser enviado ao Teams.

## Relatório enviado ao Teams

O relatório tem o seguinte foco:

```text
Auditor automático dos dados STPC/DF - SEMOB
Data

Frota por Operadora
Viagens programadas por linha
Pontos de parada
Itinerário espacial
```

A mensagem foi desenhada para ser objetiva. Ela informa o que mudou, sem transformar o comunicado em análise técnica extensa. Quando houver necessidade de auditoria detalhada, os arquivos completos ficam salvos em `data/diffs/`.

## Comandos auxiliares

### Inspecionar snapshots baixados

Use este comando para ver colunas e primeiras linhas dos snapshots do dia:

```bash
python src/inspect_snapshots.py
```

Ele é útil quando uma camada muda de estrutura ou quando é necessário confirmar o nome real das colunas retornadas pelo GeoServer.

### Validar configuração

Use este comando para verificar se as colunas configuradas em `layers.yaml` existem nos snapshots baixados:

```bash
python src/validate_config.py
```

Ele deve ser executado depois de já existir snapshot bruto do dia em `data/snapshots/`.

## Agendamento no Windows

A automação pode ser executada diariamente pelo Agendador de Tarefas do Windows.

Configuração sugerida:

- frequência: diária;
- horário: 08:00;
- marcar a opção para executar assim que possível caso o agendamento seja perdido;
- executar usando o usuário do Windows que possui acesso à pasta do projeto.

Exemplo de programa/script:

```text
D:\Automacoes\geoserver-daily-2026\.venv\Scripts\python.exe
```

Exemplo de argumento:

```text
D:\Automacoes\geoserver-daily-2026\src\main.py
```

Exemplo de pasta inicial:

```text
D:\Automacoes\geoserver-daily-2026
```

## GitHub Actions

Este projeto pode ser versionado no GitHub, mas a execução via GitHub Actions exige cuidado. Como a automação salva histórico local em `data/snapshots/` e compara com snapshots anteriores, o agendamento em nuvem só funciona corretamente se os snapshots também forem persistidos em algum lugar entre as execuções.

Para uso operacional simples, a recomendação principal é executar em uma máquina interna ou servidor com armazenamento persistente. O GitHub Actions é mais adequado para validação de código, testes ou execução com upload/download de artefatos.

## Segurança e arquivos não versionados

Não envie ao GitHub:

- `config/teams_webhook.env`;
- `.env`;
- `.venv/`;
- `data/snapshots/`;
- `data/normalized/`;
- `data/diffs/`;
- `data/reports/`;
- `data/logs/`.

Esses itens já estão previstos no `.gitignore` do projeto.

## Solução de problemas

### O Teams não recebeu mensagem

Verifique:

1. se `output.send_teams` está como `true` em `config/layers.yaml`;
2. se o arquivo `config/teams_webhook.env` existe;
3. se a variável `TEAMS_WEBHOOK_URL` está preenchida;
4. se o workflow/webhook do Teams ainda está ativo.

### A comparação foi ignorada

Isso acontece quando não existe snapshot anterior do mesmo tipo de dia.

Exemplo: se hoje é sábado, o sistema procura um snapshot anterior terminado em `_sabado`. Se não encontrar, ele baixa e salva a base atual, mas não compara.

### Apareceram muitas alterações inesperadas

Possíveis causas:

- a camada mudou de estrutura no GeoServer;
- alguma coluna volátil não foi incluída em `ignore_attribute_columns`;
- a geometria foi regravada com pequenas diferenças;
- houve mudança real em massa na base de origem;
- o snapshot anterior usado na comparação não representa a referência esperada.

Nesses casos, confira os arquivos em `data/diffs/` e rode:

```bash
python src/inspect_snapshots.py
python src/validate_config.py
```

### O GeoServer retornou erro

O script possui uma proteção para evitar salvar XML/HTML de erro como se fosse CSV ou GeoJSON. Quando isso acontece, o terminal mostra a camada afetada e o início da resposta recebida.

Verifique se:

- o nome da camada em `geoserver_name` está correto;
- o GeoServer está disponível;
- a camada ainda existe;
- o formato configurado é compatível com a camada.

## Comandos úteis de Git

Verificar alterações:

```bash
git status
```

Adicionar arquivos alterados:

```bash
git add README.md config/layers.yaml src/
```

Criar commit:

```bash
git commit -m "Atualiza documentacao da automacao GeoServer"
```

Enviar para o GitHub:

```bash
git push
```

## Licença

Projeto de automação interna para acompanhamento de dados operacionais e cadastrais do STPC/DF.
