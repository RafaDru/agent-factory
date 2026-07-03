# Model Capabilities — Agent Factory Local Squad

## GPU: NVIDIA GeForce RTX 4050 6GB GDDR6

Estratégia de otimização:
- `OLLAMA_FLASH_ATTENTION=1` — reduz VRAM e acelera inferência
- `OLLAMA_KV_CACHE_TYPE=q8_0` — KV cache quantizado (economia de VRAM)
- `OLLAMA_NUM_PARALLEL=2` — até 2 requisições simultâneas
- `OLLAMA_MAX_LOADED_MODELS=3` — mantém até 3 modelos quentes em VRAM
- `OLLAMA_SCHED_SPREAD=1` — distribui carga entre GPUs disponíveis
- `OLLAMA_KEEP_ALIVE=15m` — modelo fica cacheado 15min após último uso

## Installed Models

| Alias | Model | Params | Size | Fits GPU | Role |
|-------|-------|--------|------|----------|------|
| classifier | gemma3:4b | 4.3B | 3.3 GB | ✅ Sim | Classificação, roteamento |
| coder | qwen2.5-coder:7b | 7.6B | 4.7 GB | ✅ Sim | Geração de código, testes |
| validator | gemma4 | 8B | 9.6 GB | ⚠️ Parcial (offload) | Revisão, validação |
| reasoner | qwen3.6 | 36B MoE | 23 GB | ⚠️ Parcial (offload) | Coordenação, arquitetura |

## Capability Registry (src/llm/__init__.py)

```python
CAPABILITIES_REGISTRY = {
    "classifier": {
        "model": "gemma3:4b",
        "prompt_template": "Classifique a tarefa abaixo em UMA das categorias: "
                           "code, review, test, docs, architecture, analysis, planning, config.\n"
                           "Responda apenas com o nome da categoria.\n\nTarefa: {task}\n\nCategoria:",
    },
    "reasoner": { "model": "qwen3.6", "params": {"temperature": 0.3, "max_tokens": 4096} },
    "coder":    { "model": "qwen2.5-coder:7b", "params": {"temperature": 0.2, "max_tokens": 4096} },
    "validator": { "model": "gemma4", "params": {"temperature": 0.1, "max_tokens": 2048} },
}
```

## Usage

### De qualquer lugar do código (console, scripts, agentes)

```python
from src.llm import get_provider
from src.orchestrator.cache import CachedProvider, LLMCache

# Ativa o squad multi-modelo com roteamento inteligente
provider = get_provider("local_multi")

# Ou deixa o auto-detector decidir (groq → ollama → multi → mock)
provider = get_provider("auto")

# Com cache SQLite
cached = CachedProvider(provider, LLMCache(backend="sqlite"))
resp = cached.chat([{"role": "user", "content": "Create a test"}], task_type="coder")
```

### Em agentes

Via LLMAgent:
```python
from src.agents.real import LLMAgent
agent = LLMAgent("dev", "proj", notifier, provider=get_provider("local_multi"))
```

Via AgentBase genérico:
```python
class MeuAgente(AgentBase):
    def __init__(self):
        super().__init__(llm_provider=get_provider("local_multi"))
```

Via `get_provider("auto")` + env var `AGENT_FACTORY_PROVIDER=local_multi` (em breve).

## Routing Flow

```
User Request
    │
    ▼
MultiModelProvider.chat()
    │
    ├── task_type provided? ──► use directly
    │
    └── task_type=None
            │
            ▼
        classifier (gemma3:4b) — detecta categoria
            │
            ▼
        resolve model da CAPABILITIES_REGISTRY
            │
            ▼
        OllamaProvider.chat(model_especialista)
```

## GPU Memory Budget per Scenario

| Scenario | VRAM Used | Models Loaded |
|----------|-----------|---------------|
| Classificação + Código | ~3.3 + ~4.7 = ~8 GB | gemma3 + qwen-coder |
| Apenas código | ~4.7 GB | qwen-coder |
| Raciocínio pesado | ~6 GB (offload) | qwen3.6 (parcial) |
| Validação | ~5 GB (offload) | gemma4 (parcial) |

O Ollama gerencia o offloading automaticamente: carrega na GPU o máximo que couber,
o resto fica em RAM (40GB disponível).
