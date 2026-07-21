# Console AFP — Schema Canonico

## 1. Conceitos Fundamentais

### Console AFP
Nome definitivo do dashboard. Interface unificada para configurar, monitorar
e depurar a Agent Factory Platform.

### Projeto
Entidade de nivel mais alto. Agrupa times e agentes em torno de um objetivo.
```
Projeto {
  id: string           // "AFP-Team"
  nome: string         // "Agent Factory Platform"
  descricao: string
  working_dir: string
  times: Time[]
}
```

### Time
Agrupa agentes por funcao. Um projeto pode ter 1 ou mais times.
```
Time {
  id: string           // "AFP-Team"
  nome: string         // "Agent Factory Platform Team"
  agentes: Agente[]
}
```

### Agente
Membro individual do time com capacidades definidas por CONTEXTO.md.
```
Agente {
  id: string                    // "dev"
  nome: string                  // "Desenvolvedor"
  papel: string                 // "desenvolvedor"
  emoji: string                 // "💻"
  contexto: string              // path para CONTEXTO.md
  contexto_preview: string      // preview formatado do .md
  llm_provider: string          // "auto" | "opencode_zen" | "groq" | ...
  llm_model: string             // "deepseek-v4-pro" | "llama-3.3-70b" | ...
  module_path: string           // "src/agents/worker.py"
  class_name: string            // "DeclarativeWorker"
  acoes: string[]               // ["read_file", "write_file", ...]
  status: enum                  // ready | running | completed | failed
  ultima_execucao: Timestamp
}
```

### Missao
Conjunto coordenado de tarefas com um objetivo humanizado.
```
Missao {
  id: string                    // task_id unico
  titulo: string                // "Implementar logging nos agentes" (humanizado)
  projeto_id: string
  status: enum                  // planning | running | completed | failed
  iniciada_em: Timestamp
  concluida_em: Timestamp
  tarefas: Tarefa[]
  delegacoes: Delegacao[]
}
```

### Tarefa
Unidade atomica de trabalho dentro de uma missao.
```
Tarefa {
  id: string
  missao_id: string
  agente_id: string
  acao: string                  // "read_file" | "edit_file" | ...
  params: object
  status: enum                  // pending | running | completed | failed | skipped
  dependencias: string[]        // ids de tarefas que devem preceder esta
  iniciada_em: Timestamp
  concluida_em: Timestamp
  duracao_ms: number
  resultado: object
  erro: StructuredError
}
```

### Delegacao
Relacionamento entre agentes durante uma missao.
```
Delegacao {
  id: string
  missao_id: string
  de_agente_id: string          // coordenador
  para_agente_id: string        // dev
  tarefa_id: string
  status: enum                  // running | completed | failed
  mensagem: string              // "Delegando 'read_file' para dev"
  resultado: object
  iniciada_em: Timestamp
  concluida_em: Timestamp
}
```

### Interacao
Comunicacao direta entre agentes (pergunta, resposta, dialogo).
```
Interacao {
  id: string
  missao_id: string
  de_agente_id: string
  para_agente_id: string
  tipo: enum                    // pergunta | resposta | decisao | alerta
  mensagem: string
  payload: object
  timestamp: Timestamp
}
```

---

## 2. Fluxo de Vida

```
Missao (criada pelo coordenador)
  │
  ├── Tarefa 1 (coordenador → dev)
  │     └── Delegacao
  │           ├── Interacao: dev pergunta esclarecimento
  │           └── Interacao: coordenador responde
  │
  ├── Tarefa 2 (coordenador → qa)
  │     └── Delegacao
  │
  └── Missao concluida → vai para Historico
```

---

## 3. Distincao Live Stream vs Log

| Aspecto | Live Stream | Log |
|---------|-------------|-----|
| Proposito | O que esta acontecendo AGORA | O que ACONTECEU (tracing) |
| Atualizacao | Em tempo real, estado atual | Historico completo |
| Cards | 1 por agente, estado unico | Multiplas linhas por evento |
| Detalhes | Expansivel sob demanda | Tabela completa |
| Visao | Grafica, interacoes visuais | Tabular, filtros, busca |
| Retencao | So o estado atual + ultimas N missoes no historico | Tudo (eventos persistidos) |

---

## 4. Regras de Exibicao

1. **Card do agente no Live Stream**: mostra 1 estado por vez
   - running → animacao pulsante, timer, tarefa atual
   - completed → flash verde, depois volta a idle
   - failed → destaque vermelho, mensagem de erro
   - idle → estatico, sem destaque
   - NUNCA criar um segundo card quando o estado muda

2. **Historico do Live Stream**: missoes concluidas compactas
   - Titulo humanizado
   - Duracao total
   - Status final
   - Clicavel → expande para "foto final" do Live Stream

3. **Log**: tela separada, tabela com colunas
   - Timestamp | Agente | Status | Tarefa | Mensagem
   - Filtros por agente, tipo, periodo
   - Busca textual
