"""
Agent Factory — LLM Integration
================================
Integração com provedores de LLM para tomada de decisão de agentes.
Suporta Groq (API), Ollama (local), e MultiModelProvider (roteamento inteligente).

Uso rápido (console):
    from src.llm import get_provider, MultiModelProvider

    # Ativa squad multi-modelo local
    provider = get_provider("local_multi")
    resp = provider.chat([{"role": "user", "content": "Gere um teste"}], task_type="coder")

    # Ou deixa o "auto" decidir (groq → ollama → multi → mock)
    provider = get_provider("auto")

    # Cache integrado
    from src.orchestrator.cache import CachedProvider, LLMCache
    provider = CachedProvider(get_provider("local_multi"), LLMCache("sqlite"))
"""

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Resposta padronizada de um LLM."""
    content: str
    model: str
    usage: dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    finish_reason: str
    raw: Optional[dict] = None


class LLMProvider(ABC):
    """Classe base abstrata para provedores de LLM."""
    
    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        """Envia mensagem para o LLM e retorna resposta."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provedor está disponível."""
        pass


class GroqProvider(LLMProvider):
    """
    Provedor Groq (API cloud).
    
    Requer: GROQ_API_KEY no ambiente ou via parâmetro.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Inicializa o cliente Groq (lazy)."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise ImportError("groq não instalado. Execute: pip install groq")
        return self._client
    
    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        """Envia mensagem para o Groq."""
        client = self._get_client()
        model = model or self.model
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        choice = response.choices[0]
        usage = response.usage
        
        return LLMResponse(
            content=choice.message.content,
            model=response.model,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
            finish_reason=choice.finish_reason,
            raw=response.model_dump(),
        )
    
    def is_available(self) -> bool:
        """Verifica se o Groq está disponível."""
        return self.api_key is not None


class OllamaProvider(LLMProvider):
    """
    Provedor Ollama (local).
    
    Requer: Ollama rodando localmente (default: http://localhost:11434).
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Inicializa o cliente Ollama (lazy)."""
        if self._client is None:
            try:
                import ollama
                self._client = ollama.Client(host=self.base_url)
            except ImportError:
                raise ImportError("ollama não instalado. Execute: pip install ollama")
        return self._client
    
    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        """Envia mensagem para o Ollama."""
        client = self._get_client()
        model = model or self.model
        
        response = client.chat(
            model=model,
            messages=messages,
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            **kwargs
        )
        
        return LLMResponse(
            content=response["message"]["content"],
            model=response["model"],
            usage={
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "completion_tokens": response.get("eval_count", 0),
                "total_tokens": response.get("prompt_eval_count", 0) + response.get("eval_count", 0),
            },
            finish_reason="stop",
            raw=response,
        )
    
    def is_available(self) -> bool:
        """Verifica se o Ollama está disponível."""
        try:
            import urllib.request
            urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=2)
            return True
        except Exception:
            return False


class MockProvider(LLMProvider):
    """
    Provedor mock para testes.
    
    Retorna respostas predefinidas sem chamar API real.
    """
    
    def __init__(self, responses: Optional[list[str]] = None):
        self.responses = responses or ["Resposta mock do LLM."]
        self._call_count = 0
        self.history: list[dict] = []
    
    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> LLMResponse:
        """Retorna resposta mock."""
        self.history.append({
            "messages": messages,
            "model": model,
            "temperature": temperature,
        })
        
        content = self.responses[self._call_count % len(self.responses)]
        self._call_count += 1
        
        return LLMResponse(
            content=content,
            model="mock-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
        )
    
    def is_available(self) -> bool:
        """Sempre disponível."""
        return True


def get_provider(
    provider_name: str = "auto",
    **kwargs
) -> LLMProvider:
    """
    Factory para obter provedor de LLM.
    
    Args:
        provider_name: "groq", "ollama", "mock", "local_multi", ou "auto"
        **kwargs: Argumentos passados ao provedor
    
    Returns:
        Instância do provedor
    
    Nota:
        "auto" tenta groq → ollama → local_multi → mock
        "local_multi" ativa o squad de 4 modelos locais com roteamento inteligente
    """
    if provider_name == "groq":
        return GroqProvider(**kwargs)
    elif provider_name == "ollama":
        return OllamaProvider(**kwargs)
    elif provider_name == "mock":
        return MockProvider(**kwargs)
    elif provider_name == "local_multi":
        return MultiModelProvider(**kwargs)
    elif provider_name == "auto":
        # Tenta cloud primeiro, depois local
        groq = GroqProvider()
        if groq.is_available():
            return groq
        
        ollama = OllamaProvider()
        if ollama.is_available():
            # Se Ollama está rodando, ativa squad multi-modelo
            return MultiModelProvider()
        
        # Fallback para mock
        return MockProvider()
    else:
        raise ValueError(
            f"Provedor desconhecido: {provider_name}. "
            f"Opções: groq, ollama, mock, local_multi, auto"
        )


CAPABILITIES_REGISTRY = {
    "classifier": {
        "model": "gemma3:4b",
        "label": "Classificador rápido",
        "description": "Classifica tipo de tarefa, prioridade, roteamento",
        "fits_gpu": True,
        "params": {"temperature": 0.1, "max_tokens": 256},
        "prompt_template": (
            "Classifique a tarefa abaixo em UMA das categorias: "
            "code, review, test, docs, architecture, analysis, planning, config.\n"
            "Responda apenas com o nome da categoria.\n\nTarefa: {task}\n\nCategoria:"
        ),
    },
    "reasoner": {
        "model": "qwen3.6",
        "label": "Raciocínio e coordenação",
        "description": "Decomposição de tarefas, planejamento, decisões arquiteturais",
        "fits_gpu": False,
        "params": {"temperature": 0.3, "max_tokens": 4096},
    },
    "coder": {
        "model": "qwen2.5-coder:7b",
        "label": "Especialista em código",
        "description": "Geração de código, testes, refatoração",
        "fits_gpu": True,
        "params": {"temperature": 0.2, "max_tokens": 4096},
    },
    "validator": {
        "model": "gemma4",
        "label": "Validador de saída",
        "description": "Revisão de código, verificação de segurança, validação",
        "fits_gpu": False,
        "params": {"temperature": 0.1, "max_tokens": 2048},
    },
}


class MultiModelProvider(LLMProvider):
    """
    Provedor que roteia requisições para o melhor modelo local
    baseado no tipo da tarefa.

    Modelos:
      - classifier (gemma3:4b):   classificação rápida (~1s, cabe na GPU)
      - reasoner   (qwen3.6):      raciocínio pesado (~23GB, offload parcial)
      - coder      (qwen2.5-coder:7b): geração de código (~4.7GB, cabe na GPU)
      - validator  (gemma4):       revisão e validação (~9.6GB, offload)

    Uso:
        provider = MultiModelProvider()
        resp = provider.chat(messages, task_type="coder")
        # ou deixa o classifier detectar automaticamente:
        resp = provider.chat(messages)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        capabilities: Optional[dict] = None,
        classifier_model: str = "gemma3:4b",
        default_model: str = "qwen3.6",
    ):
        self.base_url = base_url
        self.capabilities = capabilities or CAPABILITIES_REGISTRY
        self.classifier_model = classifier_model
        self.default_model = default_model
        self._providers: dict[str, OllamaProvider] = {}

    def _get_provider(self, model_name: str) -> OllamaProvider:
        """Retorna (ou cria) provider para um modelo."""
        if model_name not in self._providers:
            self._providers[model_name] = OllamaProvider(
                base_url=self.base_url, model=model_name
            )
        return self._providers[model_name]

    def _classify_task(self, messages: list[dict]) -> str:
        """
        Usa o classificador (gemma3:4b) pra detectar o tipo da tarefa
        a partir da mensagem do usuário.
        """
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") in ("user", "system") and m.get("content"):
                user_msg = m["content"][:1000]
                break

        prompt = self.capabilities["classifier"]["prompt_template"].format(task=user_msg)
        classifier = self._get_provider(self.classifier_model)
        try:
            resp = classifier.chat(
                messages=[{"role": "user", "content": prompt}],
                **self.capabilities["classifier"]["params"],
            )
            category = resp.content.strip().lower()
            # Valida se é uma categoria conhecida
            if category in self.capabilities:
                return category
            # Tenta extrair por regex
            for known in self.capabilities:
                if known in category:
                    return known
            return self.default_model
        except Exception:
            return self.default_model

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        task_type: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Envia mensagem para o melhor modelo.

        Args:
            messages: Histórico da conversa
            model: Nome específico do modelo (sobrepõe roteamento)
            task_type: "coder" | "reasoner" | "validator" | "classifier"
                       Se None, usa o classifier pra detectar.
        """
        # Se modelo explícito, usa diretamente
        if model:
            provider = self._get_provider(model)
            return provider.chat(messages, model, temperature, max_tokens, **kwargs)

        # Descobre o tipo de tarefa
        if task_type is None:
            task_type = self._classify_task(messages)

        # Resolve o modelo a partir das capacidades
        cap = self.capabilities.get(task_type)
        if cap is None:
            # Fallback: procura por substring no nome
            for key, val in self.capabilities.items():
                if task_type in key or key in task_type:
                    cap = val
                    break
        if cap is None:
            cap = self.capabilities.get(self.default_model, {})

        model_name = cap.get("model", self.default_model)
        params = {**cap.get("params", {})}
        params.setdefault("temperature", temperature)
        params.setdefault("max_tokens", max_tokens)
        params.update(kwargs)

        provider = self._get_provider(model_name)
        return provider.chat(messages, model_name, **params)

    def is_available(self) -> bool:
        """Verifica se pelo menos um modelo local está disponível."""
        for name in list(self.capabilities.keys()):
            provider = self._get_provider(self.capabilities[name]["model"])
            if provider.is_available():
                return True
        return False
