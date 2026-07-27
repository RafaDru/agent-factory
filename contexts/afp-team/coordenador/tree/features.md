# Features — coordenador — AFP-Team

## Implementadas

### Console AFP (src/dashboard/index.html)
- E-002 Configuracao: 3 abas — Projetos, Agentes, LLM Providers
- E-001 Mission Control: Global (#/mission-control), Local (#/project/{id}/mission-control)
- URL Routing via hash: #/projects, #/project/{id}/{tab}, #/mission-control, #/config
- LLM Modal: tarefas indicadas, execucao, consumo, benchmark
- Agent Cards: status badge, LLM provider, contexto, ultima execucao
- Botao "Log Details": tabela de metadados (timestamp, agente, status, taskId, mensagem)

### Modelos LLM Configurados
| Agente | Provedor | Modelo |
|--------|----------|--------|
| coordenador | opencode_zen | deepseek-v4-flash-free |
| dev | opencode_zen | deepseek-v4-flash-free |
| qa | opencode_zen | deepseek-v4-flash-free |
| designer | opencode_zen | deepseek-v4-flash-free |
| arquiteto | opencode_zen | deepseek-v4-flash-free |
| negocios | opencode_zen | deepseek-v4-flash-free |
