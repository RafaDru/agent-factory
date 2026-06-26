# Agent Factory - Changelog

## v1.1.0 (24/06/2026)

### Atualização Completa

#### 1. Renomeação do Projeto
- **Antes**: `agent-orchestrator`
- **Depois**: `agent-factory`
- Todos os caminhos e referências atualizados

#### 2. Dashboard - Event Log Tabulado
- Event Log exibe em formato de tabela
- Colunas: Data | Hora | Agente | Tarefa | Status | Descrição
- Eventos mais recentes aparecem no topo (inverted)
- Header fixo (sticky) durante scroll
- Status badges coloridos (running=azul, completed=verde, failed=vermelho)

#### 3. Dashboard - Cards de Agentes
- Cada card mostra: nome, status, eventos, papel
- **Novo**: Exibe nome da tarefa atual (`lastTask`)
- **Novo**: Exibe data/hora da última execução (`lastTime`)
- Última mensagem exibida no card

#### 4. Dashboard - Atualização Automática
- Polling simples a cada 1 segundo via HTTP
- Sem SSE (Server-Sent Events) - simplificado
- Frontend busca `/api/events` e `/api/status` periodicamente
- Apenas eventos novos são processados (incremental)

#### 5. Fix: CoordenadorAgent Input Validation
- **Problema**: Tarefas sem `task_type` e `payload` falhavam
- **Solução**: `validate_input` aceita formato simples (apenas `task_id`)
- **Inferência automática**: Coordenador infere `task_type` pelo conteúdo
- **Tarefas genéricas**: Retorna confirmação quando não consegue delegar

#### 6. Novas Ações para VisaoComputacionalAgent
- `update_python_scripts`: Atualiza scripts Python com constantes
- `generate_filtered_video`: Gera vídeo filtrado com parâmetros

#### 7. Atualização dos Scripts Python
- `generate_filtered_video.py`: Cores por tipo de landmark
- `validate_combined.py`: Filtros diferenciados por tipo
- `render_comparative.py`: Cores e raios por tipo

### Parâmetros Calibrados por Tipo

| Tipo | Cor | Outlier | Alpha | Raio |
|------|-----|---------|-------|------|
| Joint (articulações) | Verde #00ff88 | 3.0 | 0.5 | 6px |
| Static (estáticos) | Azul #4488ff | 2.0 | 0.7 | 4px |
| Limb (membros) | Laranja #ff8800 | 2.5 | 0.6 | 3px |

## v1.0.1 (23/06/2026)

### Labels nos Agentes
- Campos `title`, `observation`, `description` na classe `AgentBase`
- Nova classe `TaskInput` com campos padronizados
- Correlação com GitHub Issues via `github_issue` e `github_pr`

### Inicialização com Windows
- Script `start_agent_factory.bat` para inicialização manual
- Script `install_startup.ps1` para configuração automática
- Tarefa agendada no Windows Task Scheduler

## Como Usar

### Iniciar Agent Factory
```bash
cd C:\Users\rafae\agent-factory
python start_dashboard.py
```

### Configurar Inicialização Automática
```powershell
# PowerShell como administrador
.\install_startup.ps1
```

### Acessar Dashboard
```
http://localhost:8080?project=pta
```

## Arquivos Principais
- `src/agents/base.py` - Classe base dos agentes
- `src/protocols/schema.py` - Schema de eventos e tarefas
- `src/dashboard/server.py` - Servidor HTTP
- `src/dashboard/index.html` - Dashboard UI
- `projects/pta/agents/__init__.py` - Agentes específicos do PTA
