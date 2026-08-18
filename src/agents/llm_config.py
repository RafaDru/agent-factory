"""Carrega overrides de LLM de .agent-factory/agent_config.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(".agent-factory/agent_config.json")


def load_agent_llm_provider(agent_id: str) -> Optional[str]:
    """Retorna string provider (ex: opencode:deepseek-v4-flash) ou None."""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        entry = data.get(agent_id, {})
        return entry.get("llm_provider") or None
    except (json.JSONDecodeError, OSError):
        return None


def apply_llm_config(agent: Any, agent_id: str) -> None:
    """Aplica provider do agent_config.json ao agente (runtime/MCP)."""
    provider_str = load_agent_llm_provider(agent_id)
    if not provider_str:
        return
    try:
        from src.llm import get_provider

        prov = get_provider(provider_str)
        if hasattr(agent, "_llm"):
            agent._llm = prov
        if hasattr(agent, "_llm_provider"):
            agent._llm_provider = prov
        logger.info("LLM %s -> %s", agent_id, provider_str)
    except Exception as exc:
        logger.warning("Falha ao aplicar LLM %s (%s): %s", agent_id, provider_str, exc)
