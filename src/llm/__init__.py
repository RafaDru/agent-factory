"""
Agent Factory — LLM Integration
================================
Integracao com provedores de LLM para tomada de decisao de agentes.
Suporta 12 provedores (9 cloud gratis + 3 locais) com fallback automatico.

Carrega automaticamente chaves de API do arquivo .env na raiz do projeto.

Provedores implementados:
  Cloud (gratuitos):
    - Groq      (groq)         Llama 4, Qwen3 32B — 30 RPM, sem cartao
    - Gemini    (gemini)       Gemini 2.0 Flash — 1.500 req/dia
    - DeepSeek  (deepseek)     DeepSeek V3 — API compativel OpenAI
    - OpenRouter(openrouter)   Gateway 20+ modelos free — 50 req/dia
    - Cerebras  (cerebras)     Llama 3.1 70B — 1M tokens/dia
    - Mistral   (mistral)      Mistral Small/Nemo — 1B tokens/mes
    - NVIDIA NIM(nvidia)       Modelos NVIDIA — 40 RPM
    - HuggingFace(huggingface) Serverless 300 req/h
    - Cloudflare(cloudflare)   Workers AI — 300K neurons/mes

  Local:
    - Ollama    (ollama)       Modelos locais via Ollama
    - MultiModel(local_multi)  Squad 4 modelos com roteamento inteligente

Uso rapido:
    from src.llm import get_provider

    provider = get_provider("auto")  # tenta cloud -> local -> mock
    resp = provider.chat([{"role": "user", "content": "Gere um teste"}])
"""

import json
import os
import re
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass

# Carregar .env automaticamente se existir
_env_loaded = False
def _load_env():
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass

_load_env()


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


def _has_key(key: Optional[str]) -> bool:
    """True se a chave existe e nao esta vazia."""
    return key is not None and len(key.strip()) > 0


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
        return _has_key(self.api_key)


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


class OpenAICompatibleProvider(LLMProvider):
    """
    Provedor generico para APIs compativeis com OpenAI.
    
    Funciona com DeepSeek, OpenRouter, Together AI, etc.
    
    Uso:
        provider = OpenAICompatibleProvider(
            base_url="https://api.deepseek.com",
            api_key="sk-...",
            model="deepseek-chat",
        )
    """
    
    def __init__(
        self,
        base_url: str = "https://api.deepseek.com",
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_retries = max_retries
        self._client = None
        self._api_key = api_key or os.getenv(
            self._get_env_key_name()
        )
    
    def _get_env_key_name(self) -> str:
        """Retorna nome da env var para API key."""
        return "OPENAI_API_KEY"
    
    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url=self.base_url,
                    api_key=self._api_key,
                    max_retries=self.max_retries,
                    timeout=120,
                )
            except ImportError:
                raise ImportError("openai não instalado. Execute: pip install openai")
        return self._client
    
    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
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
            content=choice.message.content or "",
            model=response.model or model,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
            finish_reason=choice.finish_reason or "stop",
            raw=response.model_dump() if hasattr(response, "model_dump") else None,
        )
    
    def is_available(self) -> bool:
        return _has_key(self._api_key)


class DeepSeekProvider(OpenAICompatibleProvider):
    """
    Provedor DeepSeek (https://deepseek.com).
    
    Modelos:
    - deepseek-chat (V3) - uso geral, codigo, analise
    - deepseek-reasoner (R1) - raciocinio profundo
    
    API Key gratuita em: https://platform.deepseek.com/api_keys
    """
    
    DEEPSEEK_DEFAULTS = {
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
    ):
        super().__init__(
            base_url="https://api.deepseek.com",
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
            model=model,
        )
    
    def _get_env_key_name(self) -> str:
        return "DEEPSEEK_API_KEY"


class OpenRouterProvider(OpenAICompatibleProvider):
    """
    Provedor OpenRouter (https://openrouter.ai).
    
    Agrega centenas de modelos, incluindo varios gratuitos:
    - google/gemma-7b:free
    - mistralai/mistral-7b:free
    - meta-llama/llama-3-8b:free
    - cognitivecomputations/dolphin-mixtral:free
    
    API Key em: https://openrouter.ai/keys
    """
    
    OPENROUTER_DEFAULTS = {
        "model": "cognitivecomputations/dolphin-mixtral-8x7b:free",
        "base_url": "https://openrouter.ai/api",
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "cognitivecomputations/dolphin-mixtral-8x7b:free",
    ):
        super().__init__(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
            model=model,
        )
    
    def _get_env_key_name(self) -> str:
        return "OPENROUTER_API_KEY"


class GeminiProvider(LLMProvider):
    """
    Provedor Google Gemini (AI Studio).

    Modelos:
    - gemini-2.0-flash    (rapido, 1M tokens contexto)
    - gemini-2.0-flash-lite (mais rapido, custo zero)

    API Key gratuita: https://aistudio.google.com/apikey
    Free tier: 1.500 req/dia, 1M tokens contexto, sem cartao
    """

    GEMINI_DEFAULTS = {
        "model": "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                raise ImportError("google-generativeai nao instalado. Execute: pip install google-generativeai")
        return self._client

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        client = self._get_client()
        model_name = model or self.model

        # Converter formato OpenAI para Gemini
        system_prompt = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_prompt += m["content"] + "\n"
            else:
                role = "model" if m["role"] == "assistant" else "user"
                chat_messages.append({"role": role, "parts": [m["content"]]})

        gen_model = client.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt.strip() or None,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        response = gen_model.generate_content(chat_messages)

        return LLMResponse(
            content=response.text,
            model=model_name,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                "total_tokens": (response.usage_metadata.prompt_token_count + response.usage_metadata.candidates_token_count)
                if response.usage_metadata else 0,
            },
            finish_reason=response.candidates[0].finish_reason.name if response.candidates else "stop",
            raw=response.to_dict() if hasattr(response, "to_dict") else None,
        )

    def is_available(self) -> bool:
        return _has_key(self.api_key)


class CerebrasProvider(OpenAICompatibleProvider):
    """
    Provedor Cerebras (inferencia em wafer-scale silicon).

    Modelos (disponiveis na chave atual):
    - gpt-oss-120b     (120B params, uso geral)
    - gemma-4-31b      (Google Gemma 4, 31B)
    - zai-glm-4.7      (GLM, 4.7B params)

    API Key: https://inference.cerebras.ai/
    Free tier: 30 RPM, 1M tokens/dia, sem cartao
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-oss-120b",
    ):
        super().__init__(
            base_url="https://api.cerebras.ai/v1",
            api_key=api_key or os.getenv("CEREBRAS_API_KEY"),
            model=model,
        )

    def _get_env_key_name(self) -> str:
        return "CEREBRAS_API_KEY"


class MistralProvider(OpenAICompatibleProvider):
    """
    Provedor Mistral AI (La Plateforme).

    Modelos:
    - mistral-small-latest    (uso geral)
    - open-mistral-nemo       (aberto, 12B)
    - codestral-latest        (codigo)

    API Key: https://console.mistral.ai/api-keys/
    Free tier: 1B tokens/mes (Experiment plan), sem cartao
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistral-small-latest",
    ):
        super().__init__(
            base_url="https://api.mistral.ai/v1",
            api_key=api_key or os.getenv("MISTRAL_API_KEY"),
            model=model,
        )

    def _get_env_key_name(self) -> str:
        return "MISTRAL_API_KEY"


class MimoProvider(OpenAICompatibleProvider):
    """
    Provedor Xiaomi MiMo (plataforma de IA da Xiaomi).

    Modelos:
    - mimo-v2.5-pro         (MiMo-V2.5-Pro, 1T params, 42B active, 1M ctx)
    - mimo-v2-flash         (MoE high-speed, 56K ctx, mais rapido)
    - mimo-v2.5-omni        (multimodal: visao/audio/texto)

    API Key: https://platform.xiaomimimo.com/
    Base URL: https://api.xiaomimimo.com/v1
    Free tier: 10 RPM, 50K TPM, sem cartao
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mimo-v2-flash",
    ):
        super().__init__(
            base_url="https://api.xiaomimimo.com/v1",
            api_key=api_key or os.getenv("MIMO_API_KEY"),
            model=model,
        )

    def _get_env_key_name(self) -> str:
        return "MIMO_API_KEY"


class NVIDIAProvider(OpenAICompatibleProvider):
    """
    Provedor NVIDIA NIM (inferencia acelerada por GPU NVIDIA).

    Modelos gratuitos:
    - meta/llama-3.1-8b-instruct
    - mistralai/mistral-7b-instruct-v0.3
    - google/gemma-2-27b-it

    API Key: https://build.nvidia.com/
    Free tier: 40 RPM, sem cartao (requer phone verification)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "meta/llama-3.1-8b-instruct",
    ):
        super().__init__(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key or os.getenv("NVIDIA_API_KEY"),
            model=model,
        )

    def _get_env_key_name(self) -> str:
        return "NVIDIA_API_KEY"


class HuggingFaceProvider(LLMProvider):
    """
    Provedor HuggingFace Inference API (serverless).

    Modelos gratuitos (huge selection):
    - meta-llama/Llama-3.2-11B-Vision-Instruct
    - Qwen/Qwen2.5-72B-Instruct
    - google/gemma-2-9b-it
    - mistralai/Mistral-7B-Instruct-v0.3

    Token: https://huggingface.co/settings/tokens
    Free tier: 300 req/hora, sem cartao
    """

    HF_API_BASE = "https://api-inference.huggingface.co/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "Qwen/Qwen2.5-72B-Instruct",
    ):
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.model = model

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        import requests as req

        model_name = model or self.model
        url = f"{self.HF_API_BASE}/{model_name}/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        resp = req.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice["message"]["content"] or "",
            model=data.get("model", model_name),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
            raw=data,
        )

    def is_available(self) -> bool:
        return _has_key(self.api_key)


class CloudflareProvider(LLMProvider):
    """
    Provedor Cloudflare Workers AI.

    Modelos gratuitos:
    - @cf/meta/llama-3.1-8b-instruct
    - @cf/mistral/mistral-7b-instruct-v0.1
    - @hf/google/gemma-2b-it

    API Token: https://dash.cloudflare.com/profile/api-tokens
    Account ID: https://dash.cloudflare.com/ (url: /{account_id}/)
    Free tier: ~300K neurons/mes, sem cartao
    """

    CF_API_BASE = "https://api.cloudflare.com/client/v4/accounts"

    def __init__(
        self,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        model: str = "@cf/meta/llama-3.1-8b-instruct",
    ):
        self.api_key = api_key or os.getenv("CLOUDFLARE_API_KEY")
        self.account_id = account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.model = model

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        import requests as req

        model_name = model or self.model
        account_id = self.account_id or ""
        url = f"{self.CF_API_BASE}/{account_id}/ai/run/{model_name}"

        prompt_parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt = "\n".join(prompt_parts) + "\nAssistant:"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = req.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        result = data.get("result", {})
        content = result.get("response", "")

        return LLMResponse(
            content=content,
            model=model_name,
            usage={
                "prompt_tokens": result.get("prompt_tokens", 0),
                "completion_tokens": result.get("completion_tokens", 0),
                "total_tokens": result.get("total_tokens", 0),
            },
            finish_reason="stop",
            raw=data,
        )

    def is_available(self) -> bool:
        return _has_key(self.api_key) and _has_key(self.account_id)


DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"


def get_provider(
    provider_name: str = "auto",
    **kwargs
) -> LLMProvider:
    """
    Factory para obter provedor de LLM.

    Args:
        provider_name:
            "smart" (recomendado) — roteia por eficacia + fallback automatico
            "groq", "gemini", "deepseek", "openrouter", "cerebras",
            "mistral", "mimo", "nvidia", "huggingface", "cloudflare",
            "ollama", "mock", "local_multi", ou "auto" (alias para smart)
        **kwargs: Argumentos passados ao provedor

    Returns:
        Instancia do provedor

    Nota:
        "smart" / "auto": usa SmartRouterProvider com ranking por task_type
            coder:     mimo → deepseek → groq → mistral → cerebras → hf → ollama
            reasoner:  groq → deepseek → mimo → mistral → cerebras → ollama
            analysis:  groq → deepseek → openrouter → mistral → hf → ollama
            fast:      groq → cerebras
            planner:   groq → deepseek → mimo → mistral → ollama
            default:   groq → deepseek → mimo → openrouter → cerebras → mistral → hf → ollama

        "local_multi": squad de 4 modelos locais com roteamento inteligente
    """
    PROVIDER_MAP = {
        "groq": (GroqProvider, []),
        "gemini": (GeminiProvider, []),
        "deepseek": (DeepSeekProvider, ["api_key", "model"]),
        "openrouter": (OpenRouterProvider, ["api_key", "model"]),
        "cerebras": (CerebrasProvider, ["api_key", "model"]),
        "mistral": (MistralProvider, ["api_key", "model"]),
        "mimo": (MimoProvider, ["api_key", "model"]),
        "nvidia": (NVIDIAProvider, ["api_key", "model"]),
        "huggingface": (HuggingFaceProvider, ["api_key", "model"]),
        "cloudflare": (CloudflareProvider, ["api_key", "model", "account_id"]),
        "ollama": (OllamaProvider, ["base_url", "model"]),
        "mock": (MockProvider, ["responses"]),
        "local_multi": (MultiModelProvider, ["base_url", "capabilities", "classifier_model", "default_model"]),
        "smart": (SmartRouterProvider, ["verbose"]),
    }

    if provider_name == "auto":
        provider_name = "smart"

    if provider_name == "smart":
        return SmartRouterProvider(**kwargs)

    if provider_name in PROVIDER_MAP:
        cls, param_names = PROVIDER_MAP[provider_name]
        init_kwargs = {k: v for k, v in kwargs.items() if k in param_names}
        return cls(**init_kwargs)

    raise ValueError(
        f"Provedor desconhecido: {provider_name}. "
        f"Opcoes: {', '.join(PROVIDER_MAP.keys())}"
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


class SmartRouterProvider(LLMProvider):
    """
    Roteia chamadas para o melhor provedor baseado no tipo de tarefa,
    com fallback automatico em caso de erro de consumo (rate limit, overload).

    Ranking de eficacia por task_type (melhor primeiro):
      coder:     mimo → deepseek → groq → mistral → cerebras → hf → ollama-coder
      reasoner:  groq → deepseek → mimo → mistral → cerebras → ollama
      analysis:  groq → deepseek → openrouter → mistral → hf → ollama
      fast:      groq → cerebras → ollama-fast
      planner:   groq → deepseek → mimo → mistral → ollama
      default:   groq → deepseek → mimo → openrouter → cerebras → mistral → hf → ollama
    """

    _PROVIDER_CACHE: dict[str, LLMProvider] = {}

    # Ranking: melhor modelo primeiro (atualizado Jul/2026)
    RANKINGS: dict[str, list[str]] = {
        "coder": ["groq", "mimo", "deepseek", "mistral", "cerebras", "huggingface"],
        "reasoner": ["groq", "deepseek", "mimo", "mistral", "cerebras"],
        "analysis": ["groq", "deepseek", "openrouter", "mistral", "huggingface"],
        "fast": ["groq", "cerebras"],
        "planner": ["groq", "deepseek", "mimo", "mistral"],
        "review": ["groq", "deepseek", "mistral", "huggingface"],
        "default": ["groq", "deepseek", "mimo", "openrouter", "cerebras", "mistral", "huggingface"],
    }

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._fallback_log: list[dict] = []

    @staticmethod
    def _make_provider(name: str) -> Optional[LLMProvider]:
        """Cria um provider pelo nome (com cache)."""
        if name in SmartRouterProvider._PROVIDER_CACHE:
            return SmartRouterProvider._PROVIDER_CACHE[name]
        try:
            p = get_provider(name)
            SmartRouterProvider._PROVIDER_CACHE[name] = p
            return p
        except Exception:
            return None

    def _detect_task_type(self, messages: list[dict]) -> str:
        """Detecta tipo de tarefa baseado na mensagem."""
        text = ""
        for m in reversed(messages):
            if m.get("content"):
                text = m["content"].lower()
                break

        keywords = {
            "coder": ["codigo", "código", "implement", "função", "classe", "def ", "sql", "python", "script",
                      "programa", "algoritmo", "api", "endpoint", "rota", "refator"],
            "reasoner": ["raciocínio", "raciocinar", "logica", "logica", "deduç", "inferencia",
                         "por que", "explique", "justifique", "analise profunda"],
            "analysis": ["analise", "análise", "comparar", "relatorio", "relatório", "resumo",
                         "metricas", "métricas", "dashboard", "kpi", "estatistic"],
            "planner": ["plano", "planejar", "planejamento", "roadmap", "etapa", "passo",
                        "decompor", "strategia", "estratégia", "organizar"],
            "review": ["revisar", "revisão", "review", "code review", "validar", "validacao",
                       "validacao", "testar", "teste", "qualidade", "qa"],
            "fast": ["classificar", "categorizar", "sim", "não", "verdadeiro", "falso",
                     "curto", "rapido", "rápido", "resposta curta"],
        }

        scores = {}
        for ttype, words in keywords.items():
            score = sum(1 for w in words if w in text)
            if score > 0:
                scores[ttype] = score

        if scores:
            return max(scores, key=scores.get)
        return "default"

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        task_type: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        # Se modelo explicito, usa direto sem roteamento
        if model:
            for name in self.RANKINGS.get("default", []):
                p = self._make_provider(name)
                if p and p.is_available():
                    try:
                        return p.chat(messages, model=model, temperature=temperature,
                                      max_tokens=max_tokens, **kwargs)
                    except Exception:
                        continue
            raise RuntimeError(f"Nenhum provider disponivel para modelo: {model}")

        # Detectar tipo da tarefa
        if task_type is None:
            task_type = self._detect_task_type(messages)

        rank = self.RANKINGS.get(task_type, self.RANKINGS["default"])
        errors = []

        for provider_name in rank:
            p = self._make_provider(provider_name)
            if not p or not p.is_available():
                continue

            try:
                resp = p.chat(messages=messages, temperature=temperature,
                              max_tokens=max_tokens, **kwargs)

                # Anotar resposta com dados do provider
                resp.model = f"{provider_name}/{resp.model}"
                if self.verbose:
                    print(f"  [SmartRouter] task_type={task_type} provider={provider_name} "
                          f"model={resp.model} tokens={resp.usage.get('total_tokens', 0)}")

                self._fallback_log.append({
                    "task_type": task_type,
                    "provider": provider_name,
                    "model": resp.model,
                    "tokens": resp.usage,
                    "fallbacks": len(errors),
                    "errors": errors[:],
                })
                if len(self._fallback_log) > 100:
                    self._fallback_log = self._fallback_log[-100:]

                return resp

            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}"
                errors.append({"provider": provider_name, "error": err_msg})
                if self.verbose:
                    print(f"  [SmartRouter] fallback: {provider_name} falhou -> {err_msg[:100]}")
                continue

        # Todos falharam — tenta fallback local
        local = self._make_provider("local_multi")
        if local and local.is_available():
            if self.verbose:
                print(f"  [SmartRouter] fallback final: local_multi (apos {len(errors)} falhas)")
            return local.chat(messages=messages, temperature=temperature,
                              max_tokens=max_tokens, **kwargs)

        raise RuntimeError(
            f"Todos os providers falharam para task_type={task_type}. "
            f"Erros: {json.dumps(errors, ensure_ascii=False)}"
        )

    def is_available(self) -> bool:
        """Disponivel se pelo menos um provider cloud estiver disponivel."""
        for name in self.RANKINGS["default"]:
            p = self._make_provider(name)
            if p and p.is_available():
                return True
        return MultiModelProvider().is_available()

    def get_fallback_log(self) -> list[dict]:
        """Retorna historico de fallbacks."""
        return self._fallback_log
