# Agent Factory — TODO

**Última atualização:** 23/06/2026 (v1.0.0)

---

## Status Atual (v1.0.0)

O Agent Factory está **estável e funcional** na v1.0.0.

### Concluído na v1.0.0

| Item | Status | Detalhes |
|------|--------|----------|
| Agentes Reais | ✅ | `SubprocessAgent` executa código via subprocess |
| Integração LLM | ✅ | Groq, Ollama, Mock providers |
| Persistência Contexto | ✅ | SQLite via `ContextStore` |
| Testes Unitários | ✅ | 28 testes, pytest + coverage |

### Pendências para v1.1.0+

| # | Item | Prioridade | Descrição |
|---|------|------------|-----------|
| 1 | Retry automático | Média | Retry em falhas de execução |
| 2 | Limpeza de eventos | Média | Política de retenção (ex: últimos 1000) |
| 3 | Export de relatórios | Média | Gerar HTML/Markdown do histórico |
| 4 | Notificações desktop | Baixa | Integrar com Windows toast |
| 5 | Auth no dashboard | Baixa | Senha básica (ambiente local) |
| 6 | CLI | Baixa | `agent-factory run <project>` |
| 7 | Métricas | Baixa | Dashboard de métricas por agente |
| 8 | Streaming de output | Baixa | Output em tempo real durante execução |
| 9 | Logs estruturados | Baixa | JSON logs para análise |
| 10 | Rate limiting | Baixa | Controle de concorrência |

---

## Decisões Pendentes

| Questão | Opções | Recomendação |
|---------|--------|--------------|
| Como agentes executam código real? | Subprocess (feito) | ✅ Resolvido v1.0 |
| Onde armazenar contexto? | SQLite (feito) | ✅ Resolvido v1.0 |
| Dashboard deve ter auth? | Sim/Não | Não (ambiente local) |

---

## Roadmap

### v1.0.0 (Atual) ✅
- Agentes reais (subprocess)
- Integração LLM
- Persistência SQLite
- Testes unitários

### v1.1.0 (Próximo)
- Retry automático
- Limpeza de eventos
- Export de relatórios

### v1.2.0 (Futuro)
- CLI
- Métricas avançadas
- Streaming de output

---

## Como Retomar

Para continuar a evolução do Agent Factory:

1. Ler este TODO
2. Escolher um item de prioridade média
3. Criar branch dedicada
4. Implementar e testar
5. Atualizar CHANGELOG.md e este arquivo

**Recomendação:** O Agent Factory é infraestrutura estática. Evoluir apenas quando necessário. O foco principal deve ser o PTA (produto).
