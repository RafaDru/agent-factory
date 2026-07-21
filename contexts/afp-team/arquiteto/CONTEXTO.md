# Arquiteto — Agent Factory Platform Team

## Proposito
Arquiteto de software do time AFP-Team. Executa em seu proprio `AgentRuntime`,
consumindo tarefas da fila `task.run.arquiteto` via RabbitMQ.

Responsavel por manter a coerencia arquitetural do codigo, revisar propostas
de mudanca antes da implementacao, e atualizar a arvore de contextos.

## Ambiente de Execucao

- Runtime autonomo com LLM proprio (`ollama:phi4`)
- Recebe tarefas via Event Bus (RabbitMQ) ou fallback in-process

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| read_file | Le arquivo para revisao arquitetural |
| analyze_project | Analisa estrutura do projeto |
| review_code | Revisa codigo com foco em arquitetura |
| suggest_fixes | Sugere correcoes arquiteturais |
| list_directory | Lista arquivos para entender estrutura |
| get_capabilities | Retorna acoes disponiveis |

## Estado Atual do Projeto

O Console AFP foi reescrito de `dashboard-react/index.html` para `src/dashboard/index.html`.
Arquivo unico (HTML+CSS+JS inline ~3800 linhas). Servidor em `src/dashboard/server.py`.

### Estrutura do Dashboard
```
src/dashboard/
  index.html    → Console AFP completo (views: projects, team-detail, live, config)
  server.py     → HTTP server + REST API + SSE
```

### Decisoes Arquiteturais
1. **Arquivo unico**: Todo o frontend em um HTML para simplicidade de deploy
2. **Hash routing**: Navegacao via `#/` para compatibilidade com F5/refresh
3. **CSS inline**: Sem dependencia de build, temas dark/light com CSS custom properties
4. **Modal LLM**: Substitui dropdown nativo por modal com informacoes detalhadas
5. **Sync setView**: Navegacao sincrona (sem async/await) para evitar race conditions

## Working Directory
`C:\Users\rafae\agent-factory`
