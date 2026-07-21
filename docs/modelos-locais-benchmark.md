# Benchmark de Modelos Locais (Ollama)

**Data:** 20/07/2026
**Hardware:** GPU 6 GB VRAM | RAM 40 GB
**Prompt padrão:** "Explique o que é uma closure em Python com exemplo"

---

## Resultados

### 1️⃣ deepseek-r1:8b ⭐ Recomendado para uso geral

| Métrica | Valor |
|---------|-------|
| Tamanho | 5.2 GB |
| Tempo médio | ~84s |
| VRAM | 4.7 GB (✅ cabe na GPU) |
| RAM | 60 MB |
| Reasoning | Sim (chain-of-thought visível) |
| Qualidade | Excelente — explicações didáticas, código funcional |

**Melhor para:** Tarefa principal do dia-a-dia. Código, debug, arquitetura, reasoning, explicações técnicas. Melhor custo-benefício.

**Comando:** `ollama run deepseek-r1:8b`

---

### 2️⃣ dolphin3 ⚡ Mais rápido

| Métrica | Valor |
|---------|-------|
| Tamanho | 4.9 GB |
| Tempo médio | ~20s 🏆 |
| VRAM | 4.8 GB (✅ cabe na GPU) |
| RAM | 60 MB |
| Qualidade | Boa — respostas diretas, sem filtros |

**Melhor para:** Tarefas rápidas, prototipagem, rascunhos, cenários que exigem respostas sem censura.

**Comando:** `ollama run dolphin3`

---

### 3️⃣ phi4 ⭐ Qualidade superior

| Métrica | Valor |
|---------|-------|
| Tamanho | 9.1 GB |
| Tempo médio | ~116s |
| VRAM | 4.9 GB (⚠️ roda misto GPU+CPU) |
| RAM | 51 MB |
| Qualidade | Excelente — Microsoft, muito preciso |

**Melhor para:** Tarefas complexas onde tempo não é crítico. Matemática, raciocínio profundo, código complexo.

**Comando:** `ollama run phi4`

---

### 4️⃣ qwen3-vl:8b 🏆 Melhor visão

| Métrica | Valor |
|---------|-------|
| Tamanho | 6.1 GB |
| Tempo médio | ~107s (visão) / ~35s (texto simples) |
| VRAM | 5.6 GB (⚠️ quase no limite) |
| Qualidade visão | Excelente — leu textos, descreveu formas geométricas, cores e posicionamento |
| Qualidade texto | Boa, mas visão é o forte |

**Melhor para:** Análise de imagens, OCR, descrição de cenas. Não usar para texto puro (muito lento).

**Comando:** `ollama run qwen3-vl:8b`

---

### 5️⃣ gemma4 ⚠️ Versátil mas visão fraca

| Métrica | Valor |
|---------|-------|
| Tamanho | 9.6 GB |
| Tempo médio | ~48s (texto) / ~16s (visão) |
| VRAM | 5.0 GB (⚠️ roda misto GPU+CPU) |
| RAM | 86 MB |
| Qualidade visão | Fraca — detecta imagem mas descrição vaga, não lê textos |
| Qualidade texto | Muito boa — Google, suporte a tool calling |

**Melhor para:** Tool calling, tarefas multimodais leves. Visão prefira qwen3-vl:8b.

**Comando:** `ollama run gemma4`

---

## Tabela Comparativa

| Modelo | Tamanho | Cabe VRAM? | Tempo | Visão | Uso principal |
|--------|---------|-----------|-------|-------|--------------|
| **deepseek-r1:8b** | 5.2 GB | ✅ Sim | ~84s | ❌ | **Uso geral / código** |
| **dolphin3** | 4.9 GB | ✅ Sim | ~20s | ❌ | Tarefas rápidas |
| **phi4** | 9.1 GB | ❌ Misto | ~116s | ❌ | Qualidade máxima |
| **qwen3-vl:8b** | 6.1 GB | ⚠️ Borda | ~107s | ✅🥇 | Visão / imagens |
| **gemma4** | 9.6 GB | ❌ Misto | ~48s | ⚠️ Fraca | Tool calling |

## Dicas de Uso no OpenCode

- **Modelo padrão:** `ollama/deepseek-r1:8b`
- **Para respostas rápidas:** `ollama/dolphin3:latest`
- **Para visão:** `ollama/qwen3-vl:8b`
- **Atalho no TUI:** Ctrl+P para trocar de modelo

## Espaço em Disco

Modelos removidos (liberados ~50 GB):
- deepseek-r1:32b (19 GB) — muito lento, 8b faz o mesmo papel na VRAM
- qwen3.6 (23 GB) — muito lento para uso interativo
- gemma3:4b (3.3 GB) — obsoleto (gemma4 é superior)
- qwen2.5-coder:7b (4.7 GB) — desatualizado
- deepseek-coder-v2 (8.9 GB) — muito lento, não respondeu em 3min
