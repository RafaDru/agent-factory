# Coordenador — CR-10 SE

## Proposito
Orquestrador do projeto cr10se. Recebe objetivos em linguagem natural para melhorias na Creality CR-10 SE, gera planos via LLM (Groq/Ollama) e delega para klipper, pipeline, visao, resume e qa.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| delegate | Delega tarefa para klipper, pipeline, visao, resume ou qa |
| plan_and_execute | Gera plano via LLM ou recebe tasks manuais e executa DAG |
| get_capabilities | Retorna acoes disponiveis |

## Modo 1: Geracao Automatica (LLM)

```json
{
  "action": "plan_and_execute",
  "goal": "Executar diagnostico completo da CR-10 SE e gerar relatorio",
  "context": "Verificar temperaturas, conexoes e logs de erro"
}
```

## Modo 2: Tasks Manuais (sem LLM)

```json
{
  "action": "plan_and_execute",
  "goal": "Verificar estado da impressora",
  "tasks": [
    {"name": "check-conn", "agent_id": "qa", "task": {"action": "check_connection"}, "depends_on": []},
    {"name": "check-cfg", "agent_id": "qa", "task": {"action": "check_config"}, "depends_on": ["check-conn"]},
    {"name": "check-err", "agent_id": "qa", "task": {"action": "check_errors"}, "depends_on": ["check-cfg"]}
  ]
}
```

## Delegacao Direta

```json
{
  "action": "delegate",
  "agent_id": "klipper",
  "task": {"action": "send_gcode", "gcode": "M106 S128"}
}
```

## Subordinados
- **klipper**: comunicacao SSH/WebSocket/UDS com a CR-10 SE
- **pipeline**: pipeline de impressao (STL -> slice -> optimize -> upload -> start)
- **visao**: monitoramento por visao computacional
- **resume**: retomada de impressoes apos falha
- **qa**: qualidade e diagnostico

## Contexto da Impressora
- Modelo: Creality CR-10 SE (F003), Klipper v1.1.0.28
- IP: 192.168.18.200, SSH: root/Creality2023
- WebSocket: 9999, Camera MJPG: 8080
- Config: /usr/data/printer_data/config/printer.cfg
- Scripts: C:\Users\rafae\Documents\Impressao 3D

## Provedor LLM
- Usa `get_provider("auto")`: Groq -> DeepSeek -> OpenRouter -> Ollama -> Mock
