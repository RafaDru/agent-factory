"""
Agent Factory — Context Injector
==================================
Pré-processa e enriquece o contexto entre etapas de um pipeline,
evitando estouro da janela de contexto e preservando acordos contratuais.

Estratégias:
- select:   Mantém apenas chaves relevantes do estado
- truncate: Corta por contagem de tokens/caracteres
- summarize: Usa LLM para resumir o contexto
- compress:  Usa ContextManager para compressão automática
"""

import re
import json
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class InjectorConfig:
    strategy: str = "select"
    max_tokens: int = 4000
    max_chars: int = 16000
    keep_keys: Optional[list[str]] = None
    drop_keys: Optional[list[str]] = None
    summary_prompt: str = "Resuma o contexto abaixo mantendo todos os acordos e decisões importantes:"
    llm_provider: Optional[Any] = None


class ContextInjector:
    """
    Injeta e prepara contexto entre workers de um pipeline.

    Uso:
        injector = ContextInjector()
        state = injector.inject(state, {"strategy": "select", "keep_keys": ["spec", "contract"]})
        
        # Com sumarização via LLM
        injector = ContextInjector(llm_provider=my_llm)
        state = injector.inject(state, {"strategy": "summarize", "max_tokens": 2000})
    """

    def __init__(self, llm_provider: Optional[Any] = None):
        self._llm = llm_provider

    def inject(self, state: dict, config: Optional[dict] = None) -> dict:
        cfg = InjectorConfig(**(config or {}))
        if self._llm:
            cfg.llm_provider = self._llm

        strategy = cfg.strategy
        if strategy == "select":
            return self._select(state, cfg)
        elif strategy == "truncate":
            return self._truncate(state, cfg)
        elif strategy == "summarize":
            return self._summarize(state, cfg)
        elif strategy == "compress":
            return self._compress(state, cfg)
        return state

    def _select(self, state: dict, cfg: InjectorConfig) -> dict:
        """Mantém apenas chaves explicitamente listadas (ou remove as listadas)."""
        if cfg.keep_keys:
            return {k: v for k, v in state.items() if k in cfg.keep_keys}
        if cfg.drop_keys:
            return {k: v for k, v in state.items() if k not in cfg.drop_keys}
        return state

    def _truncate(self, state: dict, cfg: InjectorConfig) -> dict:
        """Corta campos de texto por caracteres/tokens."""
        truncated = {}
        total_chars = 0
        for k, v in state.items():
            if isinstance(v, str) and len(v) > cfg.max_chars // max(len(state), 1):
                v = v[:cfg.max_chars // max(len(state), 1)] + "..."
            elif isinstance(v, (dict, list)):
                serialized = json.dumps(v, default=str)
                if len(serialized) > cfg.max_chars // max(len(state), 1):
                    v = {"_truncated": True, "_preview": serialized[:200]}
            truncated[k] = v
            if isinstance(v, str):
                total_chars += len(v)
        # Se ainda estourou, corta por igual
        if total_chars > cfg.max_chars:
            ratio = cfg.max_chars / total_chars
            for k in truncated:
                if isinstance(truncated[k], str):
                    truncated[k] = truncated[k][:int(len(truncated[k]) * ratio)] + "..."
        return truncated

    def _summarize(self, state: dict, cfg: InjectorConfig) -> dict:
        """Usa LLM para resumir o estado."""
        if not cfg.llm_provider:
            return self._truncate(state, cfg)

        summary_input = f"{cfg.summary_prompt}\n\n{json.dumps(state, indent=2, default=str)[:cfg.max_chars]}"
        response = cfg.llm_provider.chat(
            messages=[
                {"role": "system", "content": "Você é um compressor de contexto. Mantenha acordos, decisões e dados críticos. Seja conciso."},
                {"role": "user", "content": summary_input},
            ],
            max_tokens=cfg.max_tokens,
        )
        return {
            "_strategy": "summarize",
            "_summary": response.content,
            "_original_size_chars": len(json.dumps(state, default=str)),
            "_summarized": True,
        }

    def _compress(self, state: dict, cfg: InjectorConfig) -> dict:
        """Aplica compressão via ContextManager em cada campo de texto."""
        from ..agents.base import ContextManager

        cm = ContextManager(limit_kb=cfg.max_chars / 1024)
        compressed = {}
        for k, v in state.items():
            if isinstance(v, str):
                compressed[k] = cm.compress_text(v) if hasattr(cm, 'compress_text') else v
            elif isinstance(v, (dict, list)):
                text = json.dumps(v, default=str)
                compressed_text = cm.compress_text(text) if hasattr(cm, 'compress_text') else text
                try:
                    compressed[k] = json.loads(compressed_text)
                except (json.JSONDecodeError, TypeError):
                    compressed[k] = compressed_text
            else:
                compressed[k] = v
        return compressed
