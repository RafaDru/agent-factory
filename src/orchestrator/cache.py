"""
Agent Factory — LLM Cache
===========================
Cache de respostas de LLM para evitar chamadas redundantes.

Níveis:
  1. Memória (RAM) — instantâneo, volátil
  2. SQLite — persistente entre sessões
  3. Semântico (opcional) — similaridade por embedding

Uso:
    cache = LLMCache(backend="sqlite", ttl=3600)
    provider = CachedProvider(GroqProvider(), cache)
    response = provider.chat(messages=[...])  # cache hit se já visto
"""

import json
import hashlib
import time
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from ..llm import LLMProvider, LLMResponse


@dataclass
class CacheEntry:
    key: str
    response_json: str
    model: str
    created_at: float
    expires_at: float
    hit_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMCache:
    """
    Cache multi-nível para respostas de LLM.

    Args:
        backend: "memory" | "sqlite"
        ttl: Tempo de vida em segundos (0 = sem expiração)
        db_path: Caminho do arquivo SQLite (apenas backend sqlite)
        max_size: Máximo de entradas em memória
    """

    def __init__(
        self,
        backend: str = "memory",
        ttl: int = 3600,
        db_path: Optional[Path] = None,
        max_size: int = 1000,
    ):
        self.backend = backend
        self.ttl = ttl
        self.max_size = max_size
        self._memory: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

        if backend == "sqlite":
            self._db_path = db_path or Path(".agent-cache/cache.db")
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    key TEXT PRIMARY KEY,
                    response_json TEXT,
                    model TEXT,
                    created_at REAL,
                    expires_at REAL,
                    hit_count INTEGER DEFAULT 0,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON llm_cache(expires_at)")
            conn.commit()
            conn.close()

    def _make_key(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Gera hash único para a requisição."""
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> Optional[LLMResponse]:
        """Retorna resposta cacheada ou None."""
        key = self._make_key(messages, model, temperature, max_tokens, **kwargs)
        entry = self._get_entry(key)
        if entry is None:
            return None

        # Hit — incrementa contador
        self._increment_hit(key)
        data = json.loads(entry.response_json)
        return LLMResponse(
            content=data["content"],
            model=data.get("model", model),
            usage={
                "prompt_tokens": entry.prompt_tokens,
                "completion_tokens": entry.completion_tokens,
                "total_tokens": entry.prompt_tokens + entry.completion_tokens,
                "_cache": "hit",
            },
            finish_reason=data.get("finish_reason", "stop"),
        )

    def set(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        response: LLMResponse,
        **kwargs,
    ):
        """Armazena resposta no cache."""
        key = self._make_key(messages, model, temperature, max_tokens, **kwargs)
        now = time.time()
        entry = CacheEntry(
            key=key,
            response_json=json.dumps({
                "content": response.content,
                "model": response.model,
                "finish_reason": response.finish_reason,
            }),
            model=model,
            created_at=now,
            expires_at=(now + self.ttl) if self.ttl > 0 else (now + 86400 * 365),
            prompt_tokens=response.usage.get("prompt_tokens", 0),
            completion_tokens=response.usage.get("completion_tokens", 0),
        )
        self._set_entry(entry)

    def clear(self):
        """Limpa todo o cache."""
        with self._lock:
            self._memory.clear()
            if self.backend == "sqlite":
                conn = sqlite3.connect(str(self._db_path))
                conn.execute("DELETE FROM llm_cache")
                conn.commit()
                conn.close()

    def stats(self) -> dict:
        """Estatísticas do cache."""
        with self._lock:
            if self.backend == "sqlite":
                conn = sqlite3.connect(str(self._db_path))
                row = conn.execute(
                    "SELECT COUNT(*), COALESCE(SUM(hit_count),0), COALESCE(SUM(prompt_tokens+completion_tokens),0) FROM llm_cache"
                ).fetchone()
                conn.close()
                return {
                    "entries": row[0],
                    "total_hits": row[1],
                    "total_tokens_cached": row[2],
                    "backend": "sqlite",
                }
            return {
                "entries": len(self._memory),
                "total_hits": sum(e.hit_count for e in self._memory.values()),
                "total_tokens_cached": sum(e.prompt_tokens + e.completion_tokens for e in self._memory.values()),
                "backend": "memory",
            }

    # ─── Internal ─────────────────────────────────────────────────

    def _get_entry(self, key: str) -> Optional[CacheEntry]:
        now = time.time()
        with self._lock:
            if self.backend == "sqlite":
                conn = sqlite3.connect(str(self._db_path))
                row = conn.execute(
                    "SELECT response_json, model, created_at, expires_at, hit_count, prompt_tokens, completion_tokens FROM llm_cache WHERE key=? AND expires_at>?",
                    (key, now),
                ).fetchone()
                conn.close()
                if row:
                    return CacheEntry(
                        key=key,
                        response_json=row[0],
                        model=row[1],
                        created_at=row[2],
                        expires_at=row[3],
                        hit_count=row[4],
                        prompt_tokens=row[5],
                        completion_tokens=row[6],
                    )
                return None

            entry = self._memory.get(key)
            if entry and (self.ttl == 0 or entry.expires_at > now):
                return entry
            if entry:
                del self._memory[key]
            return None

    def _set_entry(self, entry: CacheEntry):
        with self._lock:
            if self.backend == "sqlite":
                conn = sqlite3.connect(str(self._db_path))
                conn.execute(
                    "INSERT OR REPLACE INTO llm_cache (key, response_json, model, created_at, expires_at, hit_count, prompt_tokens, completion_tokens) VALUES (?,?,?,?,?,?,?,?)",
                    (entry.key, entry.response_json, entry.model, entry.created_at, entry.expires_at, entry.hit_count, entry.prompt_tokens, entry.completion_tokens),
                )
                conn.commit()
                conn.close()
                return

            # LRU: remove oldest if at capacity
            if len(self._memory) >= self.max_size:
                oldest = min(self._memory.items(), key=lambda x: x[1].created_at)
                del self._memory[oldest[0]]
            self._memory[entry.key] = entry

    def _increment_hit(self, key: str):
        with self._lock:
            if self.backend == "sqlite":
                conn = sqlite3.connect(str(self._db_path))
                conn.execute("UPDATE llm_cache SET hit_count = hit_count + 1 WHERE key=?", (key,))
                conn.commit()
                conn.close()
                return
            entry = self._memory.get(key)
            if entry:
                entry.hit_count += 1


class CachedProvider(LLMProvider):
    """
    Wrapper que adiciona cache a qualquer LLMProvider.

    Uso:
        provider = CachedProvider(GroqProvider(), LLMCache(backend="sqlite"))
        response = provider.chat(messages=[...])  # transparente
    """

    def __init__(self, provider: LLMProvider, cache: LLMCache):
        self._provider = provider
        self._cache = cache

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> LLMResponse:
        # Try cache
        cached = self._cache.get(messages, model or "", temperature, max_tokens, **kwargs)
        if cached is not None:
            return cached

        # Call real provider
        response = self._provider.chat(messages, model, temperature, max_tokens, **kwargs)

        # Cache result
        self._cache.set(messages, model or "", temperature, max_tokens, response, **kwargs)

        return response

    def is_available(self) -> bool:
        return self._provider.is_available()

    @property
    def _provider_inner(self):
        return self._provider
