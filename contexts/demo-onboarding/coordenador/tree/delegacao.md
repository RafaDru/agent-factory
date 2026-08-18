# Delegacao — coordenador — demo-onboarding

## Event Bus (Standard)

- Routing key: `task.run.{agent_id}`
- RPC reply via `agent.reply.{queue}`
- Fallback in-process se RabbitMQ indisponivel

## Agentes deste projeto

| Agente | Papel |
|--------|-------|
| dev | Implementacao e arquivos |
