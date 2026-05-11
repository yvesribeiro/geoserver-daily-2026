# GeoServer Daily 2026

Automação diária para baixar camadas do GeoServer da SEMOB/DF, salvar snapshots e comparar os dados atuais com o último snapshot anterior do mesmo tipo de dia.

A automação diferencia:

- dias úteis;
- sábados;
- domingos.

Assim:

- dia útil compara com o último dia útil disponível;
- sábado compara com o último sábado disponível;
- domingo compara com o último domingo disponível.

## Camadas monitoradas

A versão inicial monitora as seguintes camadas:

1. **Frota por Operadora**
2. **Viagens Programadas por Linha**
3. **Ponto de paradas 2025**
4. **Itinerário Espacial das Linhas**

## Regras de comparação

### Frota por Operadora

Chave única:

```text
numero_veiculo
```

Agrupamento:

```text
operadora
```

A automação identifica:

- veículos adicionados;
- veículos removidos;
- alterações cadastrais em veículos existentes.

O resumo de frota considera:

- `tipo_onibus`;
- `ano_fabrica`.

Exemplo de comunicado:

```text
AUTO VIAÇÃO MARECHAL
- Adicionados 8 veículos.
  - 5 do tipo PADRON: 3 ano 2022, 2 ano 2023.
- Removidos 2 veículos.
```

### Viagens Programadas por Linha

Chave única:

```text
sg_operadora
cd_linha
cs_sentido
hora_prevista
tipo_dia_operacional
```

Agrupamento:

```text
sg_operadora
cd_linha
cs_sentido
```

A automação considera as colunas:

```text
st_domingo
st_segunda
st_terca
st_quarta
st_quinta
st_sexta
st_sabado
```

Para dias úteis, considera viagens ativas em qualquer coluna de segunda a sexta.

Mudança de horário é tratada como:

```text
1 viagem removida + 1 viagem adicionada
```

### Ponto de paradas 2025

Chave única:

```text
cod_parada_v2025
```

A automação identifica:

- paradas adicionadas;
- paradas removidas;
- alterações de geometria;
- alterações cadastrais.

Não há tolerância espacial. Qualquer diferença de geometria é considerada alteração.

### Itinerário Espacial das Linhas

Chave única:

```text
id_linha
lin_sentido
```

A automação identifica:

- itinerários adicionados;
- itinerários removidos;
- alterações de trajeto;
- alterações cadastrais.

Não há agrupamento por operadora nessa camada.

Não há tolerância espacial. Qualquer diferença de geometria é considerada alteração.

## Estrutura do projeto

```text
geoserver_daily_2026/
  config/
    layers.yaml
    teams_webhook.env

  data/
    snapshots/
    normalized/
    diffs/
    reports/
    logs/

  src/
    calendar_utils.py
    comparator_geo.py
    comparator_table.py
    config_loader.py
    downloader.py
    inspect_snapshots.py
    main.py
    normalizer.py
    reporter.py
    teams.py
    validate_config.py

  requirements.txt
  README.md
```

## Instalação

Clone o repositório:

```bash
git clone https://github.com/yvesribeiro/geoserver-daily-2026.git
cd geoserver-daily-2026
```

Crie o ambiente virtual:

```bash
py -m venv .venv
```

Ative o ambiente virtual no Git Bash:

```bash
source .venv/Scripts/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Teste a instalação:

```bash
python -c "import pandas, requests, yaml, geopandas, shapely; print('OK')"
```

## Configuração

As camadas e regras de comparação ficam em:

```text
config/layers.yaml
```

O webhook do Teams deve ficar em:

```text
config/teams_webhook.env
```

Esse arquivo não deve ser versionado no GitHub.

Exemplo:

```env
TEAMS_WEBHOOK_URL=https://sua-url-do-webhook
```

No arquivo `config/layers.yaml`, o envio ao Teams é controlado por:

```yaml
output:
  send_teams: false
```

Para ativar:

```yaml
output:
  send_teams: true
```

## Execução manual

Para rodar a automação:

```bash
python src/main.py
```

A automação irá:

1. baixar as camadas do GeoServer;
2. salvar snapshots brutos;
3. gerar snapshots normalizados;
4. procurar o snapshot anterior do mesmo tipo de dia;
5. comparar os dados;
6. salvar diferenças em `data/diffs`;
7. gerar relatório em `data/reports`;
8. enviar comunicado ao Teams, se ativado.

## Primeira execução

Na primeira execução real, é esperado que a comparação seja ignorada, pois ainda não existe snapshot anterior.

Exemplo:

```text
Comparação: ignorada, pois não há snapshot anterior.
```

A partir da próxima execução do mesmo tipo de dia, a comparação passa a ocorrer automaticamente.

## Saídas geradas

### Snapshots brutos

```text
data/snapshots/
```

### Snapshots normalizados

```text
data/normalized/
```

### Diferenças detalhadas

```text
data/diffs/
```

Exemplos:

```text
frota_operadora_adicionados.csv
frota_operadora_removidos.csv
frota_operadora_alteracoes_atributos.csv

ponto_parada_v2025_adicionados.geojson
ponto_parada_v2025_removidos.geojson
ponto_parada_v2025_alteracoes_geometria.csv
ponto_parada_v2025_alteracoes_atributos.csv
```

### Relatórios

```text
data/reports/
```

Exemplo:

```text
2026-05-11_util.md
```

## Inspecionar snapshots

Para verificar colunas e amostras dos arquivos baixados:

```bash
python src/inspect_snapshots.py
```

## Validar configuração

Para verificar se as colunas configuradas existem nos snapshots:

```bash
python src/validate_config.py
```

## Configurar envio ao Microsoft Teams

A automação usa uma URL de webhook.

No Teams, uma forma recomendada é criar um workflow com gatilho HTTP, por exemplo:

```text
Send webhook alerts to a channel
```

Depois de criar o workflow, copie a URL gerada e cole em:

```text
config/teams_webhook.env
```

Formato:

```env
TEAMS_WEBHOOK_URL=https://...
```

Depois ative no `config/layers.yaml`:

```yaml
send_teams: true
```

Teste:

```bash
python src/main.py
```

Se funcionar, o terminal mostrará:

```text
Mensagem enviada ao Teams: OK
```

## Agendamento no Windows

A automação pode ser agendada pelo **Agendador de Tarefas do Windows**.

Sugestão:

- Rodar diariamente às 08:00;
- Rodar novamente se a execução for perdida;
- Executar com o usuário logado.

Exemplo de comando:

```text
D:\Automacoes\geoserver_daily_2026\.venv\Scripts\python.exe
```

Argumentos:

```text
D:\Automacoes\geoserver_daily_2026\src\main.py
```

Iniciar em:

```text
D:\Automacoes\geoserver_daily_2026
```

## Segurança

Não versionar:

- `config/teams_webhook.env`;
- snapshots;
- relatórios;
- logs;
- ambiente virtual `.venv`.

Esses arquivos e pastas devem estar protegidos pelo `.gitignore`.

## Comandos úteis de Git

Ver status:

```bash
git status
```

Adicionar alterações:

```bash
git add README.md
```

Commitar:

```bash
git commit -m "Adiciona README com instrucoes da automacao"
```

Enviar ao GitHub:

```bash
git push
```

## Licença

Projeto de automação interna.
