# Agent Factory - Atualização 23/06/2026

## Mudanças Implementadas

### 1. Labels nos Agentes (Event Log)
- Adicionados campos `title`, `observation`, `description` na classe `AgentBase`
- Campos são exibidos no Event Log durante a execução
- Correlação com GitHub Issues via `github_issue` e `github_pr`

### 2. Schema Atualizado
- Nova classe `TaskInput` com campos padronizados
- Campos de label para Event Log
- Correlação com GitHub Projects

### 3. Inicialização com Windows
- Script `start_agent_factory.bat` para inicialização manual
- Script `install_startup.ps1` para configuração automática
- Tarefa agendada no Windows Task Scheduler

### 4. Event Log Tabulado (Dashboard)
- Event Log agora exibe em formato de tabela
- Colunas: Data | Hora | Agente | Tarefa | Status | Descrição
- Eventos mais recentes aparecem no topo (inverted)
- Header fixo (sticky) durante scroll

### 5. Fix: CoordenadorAgent Input Validation
- **Problema**: Tarefas enviadas sem `task_type` e `payload` falhavam com "Input inválido"
- **Solução**: `validate_input` agora aceita formato simples (apenas `task_id`)
- **Inferência automática**: Coordenador tenta inferir `task_type` baseado no conteúdo da mensagem
- **Tarefas genéricas**: Retorna confirmação de recebimento quando não consegue delegar

## Como Usar

### Iniciar Agent Factory
```bash
cd C:\Users\rafae\agent-orchestrator
python start_dashboard.py
```

### Configurar Inicialização Automática
```powershell
# PowerShell como administrador
.\install_startup.ps1
```

### Executar Tarefa com Labels
```python
from src.agents.base import AgentBase
from src.protocols.schema import TaskInput

# Criar tarefa com labels
task = TaskInput(
    task_id="melhoria-identificacao-v1",
    title="Classificar Landmarks por Tipo",
    observation="Adicionar constantes e cores",
    description="Implementar JOINT_LANDMARKS, STATIC_LANDMARKS, LIMB_LANDMARKS no WebView",
    github_issue="PTA-123",
    payload={...}
)

# Executar agente
result = agent.run(task.dict())
```

## Correlação com GitHub Projects

### Estrutura de Labels
```
Título: "Classificar Landmarks por Tipo"
Observação: "Adicionar constantes e cores"  
Descrição: "Implementar JOINT_LANDMARKS, STATIC_LANDMARKS, LIMB_LANDMARKS no WebView"
GitHub Issue: PTA-123
```

### Exemplo de Event Log
```
[14:30:00] frontend-mobile: Iniciando: Classificar Landmarks por Tipo - Adicionar constantes e cores
[14:30:05] frontend-mobile: Executando: Classificar Landmarks por Tipo - Adicionar constantes e cores
[14:31:00] frontend-mobile: Concluído: Classificar Landmarks por Tipo - Adicionar constantes e cores
```

## Arquivos Modificados
- `src/agents/base.py` - Adicionados campos de label
- `src/protocols/schema.py` - Nova classe TaskInput
- `start_agent_factory.bat` - Script de inicialização
- `install_startup.ps1` - Configuração de inicialização automática
- `src/dashboard/index.html` - Event Log tabulado com formato de tabela
- `projects/pta/agents/__init__.py` - Fix: CoordenadorAgent input validation
