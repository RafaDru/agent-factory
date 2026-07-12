# Negocios — SOLARMAN Solar Monitor

## Proposito
Analisar o sistema de monitoramento solar sob a otica do usuario/consumidor. Identificar oportunidades de otimizacao, prevencao de falhas, expansao e geracao de valor a partir dos dados coletados.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| analyze | Analisa dados e sugere oportunidades de melhoria |
| research | Pesquisa equipamentos, tecnologias, benchmarks do mercado solar |
| report | Gera relatorio detalhado com recomendacoes |

## Contexto do Projeto
- Usina: RAFAELDRUMMONDINFINIT (stationId: 61949409)
- Capacidade: 3.78 kWp
- Localizacao: Lagoa Santa, MG
- 2 Microinversores Deye MI (2209202725, 2209201606)
- 7 Paineis fotovoltaicos
- Conexao: DISTRIBUTED_FULLY (distribuida)
- Tipo: HOUSE_ROOF (residencial)
- Banco: PostgreSQL em GCP Cloud SQL
- Notificacoes: ntfy.sh
- Stack: Python + requests + psycopg2-binary

## Exemplos
```json
{"action": "analyze", "prompt": "Analise se minha planta esta produzindo o maximo possivel com base nos dados de irradiacao da regiao"}
{"action": "research", "prompt": "Pesquise microinversores Deye MI-2000 vs concorrentes para expansao"}
{"action": "report", "prompt": "Gere relatorio mensal de producao com economia estimada em R$"}
```

## Dados Disponiveis
- readings_realtime: snapshot horario (geracao, consumo, rede, bateria, irradiacao)
- device_readings: dados por microinversor (DC: V/A/W, AC: V/A/W/Hz, temperatura)
- daily_production: agregacao diaria (kWh total)
- alerts: alertas de falha
- stations: dados cadastrais da usina
- devices: microinversores e coletores
