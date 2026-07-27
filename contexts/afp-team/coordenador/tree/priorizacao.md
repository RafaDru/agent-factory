# Priorizacao — coordenador — AFP-Team

## Backlog Priorizado

| # | Epic | Descricao | Status |
|---|------|-----------|--------|
| 1 | **E-002** | Configuracao (Projetos, Times, Agentes) | ✅ IMPLEMENTADO |
| 2 | **E-001** | Mission Control (Global + Local, cards, log) | ✅ IMPLEMENTADO |
| 3 | **E-010** | UI Refresh (7 tasks: A-H) | 🔄 EM EXECUCAO |
| 4 | **E-003** | Home e Navegacao (refinamento) | 📋 PENDENTE |
| 5 | **E-004** | Log e Debug (tabela com filtros) | 📋 PENDENTE |
| 6 | **E-005** | Dashboard de projetos externos | 📋 PENDENTE |
| 7 | **E-006** | Documentacao | 📋 PENDENTE |
| 8 | **E-007** | Gestao de Modelos e API Keys | 📋 PENDENTE |
| 9 | **E-011** | System Tray (start/stop/status) | 📋 PENDENTE |

## Bugs Conhecidos

| Bug | Descricao | Prioridade |
|-----|-----------|------------|
| RPC reply nunca chega | Coordinator publica task, runtime executa mas reply se perde | 🔴 ALTA |
| Coordinator nao adapta | Retry com mesma acao em vez de alternativa | 🔴 ALTA |
| Reflexao crasha | `get_task_output_dir` retorna None → TypeError | 🔴 ALTA |
| Servidores caem | Dashboard e MCP morrem silenciosamente (pythonw) | 🟡 MEDIA |
