"""
Agent Factory — LLM Integration
================================
Integração com provedores de LLM para tomada de decisão de agentes.
Suporta Groq (API) e Ollama (local).
"""

import json
import os
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
        provider_name: "groq", "ollama", "mock", ou "auto"
        **kwargs: Argumentos passados ao provedor
    
    Returns:
        Instância do provedor
    """
    if provider_name == "groq":
        return GroqProvider(**kwargs)
    elif provider_name == "ollama":
        return OllamaProvider(**kwargs)
    elif provider_name == "mock":
        return MockProvider(**kwargs)
    elif provider_name == "auto":
        # Tenta Groq primeiro, depois Ollama
        groq = GroqProvider()
        if groq.is_available():
            return groq
        
        ollama = OllamaProvider()
        if ollama.is_available():
            return ollama
        
        # Fallback para mock
        return MockProvider()
    else:
        raise ValueError(f"Provedor desconhecido: {provider_name}")
