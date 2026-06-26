# Refatoração: Agent Factory — Separação de Responsabilidades

**Data**: 2026-06-26
**Sessão**: Interface (Compliance Officer)
**Status**: Concluída

---

## Contexto

O Agent Factory foi criado como framework de orquestração de agentes. Inicialmente, os agentes PTA eram definidos DENTRO do projeto Factory (`agent-factory/projects/pta/agents/`).

Isso violava o princípio de separação de responsabilidades:
- **Agent Factory** deveria ser apenas plataforma de execução
- **Projetos** deveriam manter seus próprios agentes

---

## Problema Identificado

| Issue | Impacto |
|-------|---------|
| Agentes acoplados ao Factory | Mudança no agente = mudança no Factory |
| Contextos misturados | CONTEXTO.md do PTA dentro do Factory |
| Baixa reusabilidade | Agentes não servem para outros projetos |
| Manutenção difícil | Dois repositórios para atualizar |

---

## Solução Proposta

### Princípio
> **Agent Factory é plataforma de execução agêntica, não repositório de agentes.**

### Arquitetura

```
agent-factory/                    ← Só infraestrutura
├── src/agents/base.py            ← ABC (permanece)
├── src/loader.py                 ← Carrega agentes sob demanda
├── src/registry.py               ← Armazena REFERÊNCIAS
└── ...

pta-mobile/                       ← Projeto PTA
├── src/pose/                     ← Código do produto
├── agentes/                      ← Agentes PTA aqui
│   ├── __init__.py
│   └── ...
```

### Fluxo de Execução

1. **Registry** armazena REFERÊNCIA ao agente (path + classe)
2. **Loader** carrega módulo sob demanda via import dinâmico
3. **Agente** é instanciado com context tracking
4. **Factory** executa `agent.run(task)`
5. **Resultado** é retornado

---

## Alterações Realizadas

### 1. AgentLoader (`agent-factory/src/loader.py`)
- Nova classe `AgentReference` — armazena path, classe, context_file
- Nova classe `AgentLoader` — importa módulos dinamicamente
- Cache de módulos carregados
- Suporte a reload

### 2. ProjectRegistry (`agent-factory/src/registry.py`)
- Novo método `add_agent_ref()` — adiciona referência
- Novo método `get_agent_ref()` — obtém referência
- Novo método `load_agent()` — carrega agente sob demanda
- Persistência em `agents.json` por projeto

### 3. Agentes PTA (`pta-mobile/agentes/__init__.py`)
- Todos os agentes movidos para o projeto PTA
- Imports ajustados para usar base do Factory via sys.path
- `**kwargs` adicionado para context_file e context_limit_kb
- Agentes independentes do Factory

### 4. Referências (`agent-factory/.agent-factory/projects/pta/agents.json`)
- 7 agentes registrados com paths e classes
- Context files apontando para o projeto PTA
- Limites de contexto definidos por agente

### 5. Remoção
- Diretório `agent-factory/projects/pta/agents/` removido

---

## Vantagens

| Antes | Depois |
|-------|--------|
| Agentes no Factory | Agentes no projeto |
| Instâncias registradas | Referências registradas |
| Carregamento no startup | Carregamento sob demanda |
| Acoplamento forte | Baixo acoplamento |
| Difícil reusar | Fácil reusar |

---

## Como Usar (para o agente da outra sessão)

### Criar referência de agente
```python
from src.loader import AgentReference

ref = AgentReference(
    agent_id="meu-agente",
    module_path="C:/Users/rafae/MeuProjeto/agentes",
    class_name="MeuAgente",
    context_file="C:/Users/rafae/MeuProjeto/agentes/CONTEXTO.md",
    context_limit_kb=10.0,
)

registry.add_agent_ref("meu-projeto", ref)
```

### Carregar e executar
```python
# Sob demanda
agent = registry.load_agent("meu-projeto", "meu-agente")
result = agent.run({"task_id": "tarefa-01", "action": "fazer_algo"})
```

### Atualizar contexto
- Edite o arquivo `CONTEXTO.md` no projeto
- O Factory detecta automaticamente via `get_context_usage()`

---

## Context Tracking

### ContextManager (`agent-factory/src/agents/base.py`)

Nova classe `ContextManager` com suporte completo a:

| Feature | Descrição |
|---------|-----------|
| **Contagem de Tokens** | Estima tokens (1 token ≈ 4 chars) |
| **Auto-compressão** | Comprime quando > 80% do limite |
| **Métricas Completas** | KB + tokens + percentuais |
| **Histórico de Crescimento** | Últimos 100 registros |
| **Análise de Tendência** | growing/stable/shrinking |

### Métricas de Uso

```python
agent.get_context_usage() → {
    "used_kb": 12.5,
    "limit_kb": 15.0,
    "tokens": 3125,
    "token_limit": 128000,
    "percentage": 83.3,
    "token_percentage": 2.4,
    "kb_percentage": 83.3,
    "status": "warning",  # ok | warning | exhausted
    "needs_compression": True,
}
```

### Contagem de Tokens

```python
# Estimativa: 1 token ≈ 4 chars
tokens = agent.count_tokens("Olá mundo")  # → 3 tokens
```

### Análise de Tendência

```python
trend = agent.get_growth_trend() → {
    "trend": "growing",  # growing | stable | shrinking
    "tokens_per_hour": 500,
    "hours_until_full": 249.0,
    "current_tokens": 3125,
    "limit_tokens": 128000,
}
```

### Auto-compressão

Quando o contexto atinge **80%** do limite:
1. Cria backup do arquivo original (`.bak.md`)
2. Comprime o conteúdo (remove seções longas, mantém estrutura)
3. Salva versão comprimida

```python
# Compressão manual
agent.compress_context(target_percentage=60.0)

# Auto-compressão (executada automaticamente no run())
# Configurar via: auto_compress=True no construtor
```

### Métricas nos Eventos

Métricas são incluídas automaticamente em todos os eventos do dashboard:

```json
{
    "metrics": {
        "duration_seconds": 1.5,
        "context": {
            "used_kb": 12.5,
            "tokens": 3125,
            "percentage": 83.3,
            "status": "warning"
        }
    }
}
```

### Limites Configurados por Agente

| Agente | Limite KB | Limite Tokens |
|--------|-----------|---------------|
| coordenador | 15.0 | 128000 |
| frontend-mobile | 10.0 | 128000 |
| visao-computacional | 12.0 | 128000 |
| ui-ux | 8.0 | 128000 |
| qa | 8.0 | 128000 |
| renderizacao | 10.0 | 128000 |
| agent-factory-dev | 10.0 | 128000 |

---

## Status das Implementações

| Item | Status |
|------|--------|
| AgentLoader (load sob demanda) | ✅ Concluído |
| Agentes PTA em pta-mobile/agentes/ | ✅ Concluído |
| Registry com referências | ✅ Concluído |
| Context Tracking (KB) | ✅ Concluído |
| Contagem de Tokens | ✅ Concluído |
| Auto-compressão | ✅ Concluído |
| Testes unitários | ✅ Concluído |
| Documentação no histórico | ✅ Concluído |

## Próximos Passos

1. **Documentar** no LLM_INSTRUCOES.md
2. **Comunicar** ao agente da outra sessão via histórico
3. **Integrar** com dashboard (mostrar tokens)

---

## Nota para o Agente da Outra Sessão

Ao ler este histórico:

### Arquitetura
1. **NÃO** crie agentes dentro do `agent-factory/projects/`
2. **SEMPRE** crie agentes dentro do projeto (`pta-mobile/agentes/`)
3. **REGISTRE** a referência no `agents.json`
4. **USE** `registry.load_agent()` para carregar sob demanda
5. **TESTE** antes de commitar

### Context Tracking
6. **USE** `agent.get_context_usage()` para verificar uso
7. **USE** `agent.count_tokens(text)` para contar tokens
8. **USE** `agent.get_growth_trend()` para análise de tendência
9. **CONFIGURE** `auto_compress=True` para compressão automática
10. **MONITORE** `needs_compression` para saber quando comprimir

### Limites
- Limite padrão: 128000 tokens (compatível com LLMs)
- Warning em 80% de uso
- Auto-compressão cria backup (`.bak.md`)

O Factory é infraestrutura. O projeto é dono dos agentes.
