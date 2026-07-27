#!/usr/bin/env python3
"""Configure Cursor BYOK API keys from Windows environment variables."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

APP_USER_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl."
    "persistentStorage.applicationUser"
)
STATE_DB = Path(os.environ["APPDATA"]) / "Cursor" / "User" / "globalStorage" / "state.vscdb"

# OpenRouter endpoint compatible with Cursor tool calls
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/cursor"

# Custom models (OpenRouter IDs). Enable via aiSettings.modelOverrideEnabled.
OPENROUTER_MODELS = [
    "meta-llama/llama-4-maverick:free",
    "qwen/qwen3-235b-a22b:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "google/gemini-2.0-flash-exp:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "deepseek/deepseek-chat",
    "google/gemini-2.5-flash-preview",
    "mistralai/mistral-small-latest",
]

# OpenCode Zen free models (require openAIBaseUrl=https://opencode.ai/zen/v1)
OPENCODE_ZEN_MODELS = [
    "deepseek-v4-flash-free",
    "mimo-v2.5-free",
    "north-mini-code-free",
]


def first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def merge_models(existing: list[str] | None, models: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for name in list(existing or []) + models:
        if name and name not in seen:
            seen.add(name)
            merged.append(name)
    return merged


def configure() -> dict[str, object]:
    openrouter = first_env("OPENROUTER_API_KEY")
    claude = first_env("CLAUDE_API_KEY", "ANTHROPIC_API_KEY")
    google = first_env("GEMINI_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY")
    opencode_zen = first_env("OPENCODEGO_API_KEY")

    if not STATE_DB.exists():
        raise FileNotFoundError(f"Cursor state database not found: {STATE_DB}")

    backup = STATE_DB.with_name(
        f"state.vscdb.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    shutil.copy2(STATE_DB, backup)

    con = sqlite3.connect(STATE_DB)
    cur = con.cursor()

    # Provider keys (legacy plaintext path; Cursor migrates to secret storage on load)
    key_writes: list[tuple[str, str]] = []
    if openrouter:
        key_writes.append(("cursorAuth/openAIKey", openrouter))
    if claude:
        key_writes.append(("cursorAuth/claudeKey", claude))
    if google:
        key_writes.append(("cursorAuth/googleKey", google))

    for storage_key, value in key_writes:
        cur.execute(
            "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
            (storage_key, value),
        )

    row = cur.execute(
        "SELECT value FROM ItemTable WHERE key = ?", (APP_USER_KEY,)
    ).fetchone()
    if not row:
        raise RuntimeError("applicationUser persistent storage not found in state.vscdb")

    app_user = json.loads(row[0])

    if openrouter:
        app_user["useOpenAIKey"] = True
        app_user["openAIBaseUrl"] = OPENROUTER_BASE_URL
    if claude:
        app_user["useClaudeKey"] = True
    if google:
        app_user["useGoogleKey"] = True

    ai_settings = app_user.setdefault("aiSettings", {})
    enabled = ai_settings.setdefault("modelOverrideEnabled", [])
    ai_settings["modelOverrideEnabled"] = merge_models(enabled, OPENROUTER_MODELS)

    # Keep Zen model IDs registered for quick switch (OpenAI slot + override URL)
    ai_settings["modelOverrideEnabled"] = merge_models(
        ai_settings["modelOverrideEnabled"], OPENCODE_ZEN_MODELS
    )

    cur.execute(
        "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
        (APP_USER_KEY, json.dumps(app_user, ensure_ascii=False)),
    )

    con.commit()
    con.close()

    return {
        "backup": str(backup),
        "configured": {
            "openrouter": bool(openrouter),
            "anthropic": bool(claude),
            "google": bool(google),
            "opencode_zen_in_env": bool(opencode_zen),
        },
        "openrouter_base_url": OPENROUTER_BASE_URL if openrouter else None,
        "custom_models": len(ai_settings["modelOverrideEnabled"]),
        "note_opencode_zen": (
            "Para usar OpenCode Zen no Cursor: Settings > Models > "
            "Override OpenAI Base URL = https://opencode.ai/zen/v1 "
            "e cole OPENCODEGO_API_KEY no campo OpenAI."
        )
        if opencode_zen
        else None,
        "providers_in_env_not_direct_byok": [
            name
            for name, present in {
                "GROQ": bool(first_env("GROQ_API_KEY")),
                "DEEPSEEK": bool(first_env("DEEPSEEK_API_KEY")),
                "CEREBRAS": bool(first_env("CEREBRAS_API_KEY")),
                "MISTRAL": bool(first_env("MISTRAL_API_KEY")),
                "HUGGINGFACE": bool(first_env("HUGGINGFACE_API_KEY")),
                "MIMO": bool(first_env("MIMO_API_KEY")),
            }.items()
            if present
        ],
    }


if __name__ == "__main__":
    result = configure()
    print(json.dumps(result, indent=2, ensure_ascii=False))
