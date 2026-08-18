#!/usr/bin/env python3
"""
AFP System Tray — controle rapido na bandeja do Windows.

Menu: status, agentes running, abrir dashboard, start/stop/restart, notificacoes de missao.
"""

from __future__ import annotations

import ctypes
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from PIL import Image
import pystray

try:
    from winotify import Notification, audio
except ImportError:  # pragma: no cover
    Notification = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from afp_brand_hive import make_tray_icon  # noqa: E402

PID_FILE = ROOT / ".agent-factory" / "afp.pid"
NOTIFIED_FILE = ROOT / ".agent-factory" / "tray_notified.json"
START_SCRIPT = ROOT / "start_afp.ps1"
POLL_INTERVAL_SEC = 4
ASSETS_DIR = ROOT / "opendesign" / "assets" / "tray"

API_BASE = os.environ.get("AFP_API_URL", "http://localhost:8080")
MCP_BASE = os.environ.get("AFP_MCP_URL", "http://localhost:8081")
DASHBOARD_REACT = os.environ.get("AFP_DASHBOARD_REACT", "http://localhost:5173")
DASHBOARD_LEGACY = os.environ.get("AFP_DASHBOARD_LEGACY", "http://localhost:8080")

ICON_MODES = ("online", "active", "degraded", "offline")


@dataclass
class TrayState:
    server_online: bool = False
    mcp_online: bool = False
    processes_alive: int = 0
    processes_total: int = 0
    running_agents: int = 0
    status_label: str = "Verificando..."
    tooltip: str = "AFP — verificando..."
    active_mission: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)
    notified_completions: set[str] = field(default_factory=set)
    events_bootstrapped: bool = False
    tray_started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    icon_ref: pystray.Icon | None = None


state = TrayState()


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_host_port(base_url: str, default_port: int) -> tuple[str, int]:
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    return host, port


def _mcp_reachable() -> bool:
    host, port = _parse_host_port(MCP_BASE, 8081)
    return _port_open(host, port)


def _http_get(url: str, timeout: float = 3.0) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def _url_reachable(url: str, timeout: float = 1.5) -> bool:
    try:
        _http_get(url, timeout=timeout)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _read_pids() -> list[int]:
    if not PID_FILE.exists():
        return []
    pids: list[int] = []
    for line in PID_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip().strip("\ufeff")
        if line.isdigit():
            pids.append(int(line))
    return pids


def _count_alive_pids(pids: list[int]) -> int:
    if not pids or sys.platform != "win32":
        return len(pids)
    kernel32 = ctypes.windll.kernel32
    alive = 0
    for pid in pids:
        handle = kernel32.OpenProcess(0x0400, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            alive += 1
    return alive


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _count_running_agents(events: list[dict[str, Any]]) -> int:
    latest: dict[str, dict[str, Any]] = {}
    for evt in events:
        aid = evt.get("agent_id")
        if not aid:
            continue
        if aid not in latest:
            latest[aid] = evt

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    count = 0
    for evt in latest.values():
        if str(evt.get("status", "")).lower() != "running":
            continue
        ts = _parse_ts(evt.get("timestamp"))
        if ts is None or ts >= cutoff:
            count += 1
    return count


def _load_notified() -> set[str]:
    try:
        if NOTIFIED_FILE.exists():
            data = json.loads(NOTIFIED_FILE.read_text(encoding="utf-8"))
            return set(data.get("keys") or [])
    except (json.JSONDecodeError, OSError):
        pass
    return set()


def _save_notified(keys: set[str]) -> None:
    try:
        NOTIFIED_FILE.parent.mkdir(parents=True, exist_ok=True)
        trimmed = list(keys)[-400:]
        NOTIFIED_FILE.write_text(
            json.dumps({"keys": trimmed, "updated": datetime.now(timezone.utc).isoformat()}, indent=0),
            encoding="utf-8",
        )
    except OSError:
        pass


def _event_key(evt: dict[str, Any]) -> str:
    return (
        f"{evt.get('project_id', '')}:{evt.get('mission_id', '')}:{evt.get('task_id', '')}:"
        f"{evt.get('agent_id', '')}:{evt.get('status', '')}:{evt.get('timestamp', '')}"
    )


_MISSION_TERMINAL = frozenset({"completed", "partial", "failed", "cancelled"})


def _mission_outcome_from_status(status: str) -> str | None:
    s = status.lower()
    if s in ("failed", "cancelled"):
        return "failed"
    if s in ("completed", "partial"):
        return "completed"
    return None


def _is_mission_terminal_event(evt: dict[str, Any]) -> bool:
    """Evento de termino canonico de missao (nao tarefa de agente)."""
    payload = evt.get("payload") or {}
    ms = str(payload.get("mission_status", "")).lower()
    if ms in _MISSION_TERMINAL:
        return True
    msg = str(evt.get("message", "")).lower()
    return any(
        phrase in msg
        for phrase in ("missao concluida:", "missao parcial:", "missao falhou:")
    )


def _detect_mission_completions_from_events(
    events: list[dict[str, Any]],
    *,
    notify: bool,
) -> list[tuple[str, str, str]]:
    """Terminos de missao via stream de eventos."""
    completions: list[tuple[str, str, str]] = []

    for evt in events:
        if not _is_mission_terminal_event(evt):
            continue

        key = _event_key(evt)
        if key in state.notified_completions:
            continue
        state.notified_completions.add(key)

        if not notify:
            continue

        payload = evt.get("payload") or {}
        ms = str(payload.get("mission_status", "")).lower()
        msg = str(evt.get("message", "")).lower()
        mission_id = evt.get("mission_id") or evt.get("task_id") or "?"
        project_id = evt.get("project_id") or "AFP"

        if ms == "failed" or "missao falhou:" in msg:
            outcome = "failed"
        else:
            outcome = "completed"

        completions.append((project_id, str(mission_id), outcome))

    if state.notified_completions:
        _save_notified(state.notified_completions)
    if len(state.notified_completions) > 500:
        state.notified_completions = set(list(state.notified_completions)[-200:])

    return completions


def _detect_mission_completions_from_api() -> list[tuple[str, str, str]]:
    """Terminos via /api/missions (status.json canonico)."""
    completions: list[tuple[str, str, str]] = []
    try:
        code, body = _http_get(f"{API_BASE}/api/missions")
        if code != 200:
            return completions
        missions = json.loads(body).get("missions") or []
    except (json.JSONDecodeError, urllib.error.URLError, KeyError):
        return completions

    for m in missions:
        mid = m.get("id") or m.get("mission_id") or ""
        status = str(m.get("status", "")).lower()
        outcome = _mission_outcome_from_status(status)
        if not mid or not outcome:
            continue
        key = f"mission-api:{mid}:{status}:{m.get('updated_at', '')}"
        if key in state.notified_completions:
            continue
        state.notified_completions.add(key)
        completions.append((m.get("project_id") or "AFP", str(mid), outcome))

    if completions:
        _save_notified(state.notified_completions)
    return completions


def _find_active_mission(events: list[dict[str, Any]]) -> str:
    for evt in events:
        st = str(evt.get("status", "")).lower()
        if st == "running":
            mid = evt.get("mission_id")
            if mid:
                return str(mid)
            msg = str(evt.get("message", ""))
            if "missao" in msg.lower():
                return msg[:80]
    return ""


def poll_status() -> None:
    pids = _read_pids()
    alive = _count_alive_pids(pids)
    server_ok = False
    mcp_ok = False
    running = 0
    events: list[dict[str, Any]] = []

    try:
        code, body = _http_get(f"{API_BASE}/api/projects")
        server_ok = code == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        server_ok = False

    try:
        mcp_ok = _mcp_reachable()
    except OSError:
        mcp_ok = False

    if server_ok:
        try:
            _, body = _http_get(f"{API_BASE}/api/events?limit=120")
            payload = json.loads(body)
            events = payload.get("events") or []
            running = _count_running_agents(events)
        except (json.JSONDecodeError, urllib.error.URLError, KeyError):
            pass

    total_pids = len(pids)
    if not server_ok:
        label = "Servidor offline"
    elif alive == 0:
        label = "Parcial — API ok, processos AFP parados"
    elif not mcp_ok:
        label = "Degradado — MCP indisponivel"
    elif alive < total_pids and total_pids > 0:
        label = f"Degradado — {alive}/{total_pids} processos"
    elif running > 0:
        label = f"Servidor online — {running} agente(s) em execucao"
    else:
        label = "Servidor online — standby"

    active = _find_active_mission(events)

    # Primeiro poll: marca historico como visto (evita spam ao reiniciar tray)
    notify = state.events_bootstrapped
    completions = _detect_mission_completions_from_events(events, notify=notify)
    if notify:
        completions.extend(_detect_mission_completions_from_api())
    if not state.events_bootstrapped:
        _detect_mission_completions_from_api()  # bootstrap API keys sem toast
        state.events_bootstrapped = True

    with state.lock:
        state.server_online = server_ok
        state.mcp_online = mcp_ok
        state.processes_alive = alive
        state.processes_total = len(pids)
        state.running_agents = running
        state.status_label = label
        state.active_mission = active
        state.tooltip = (
            f"AFP — {label}\n"
            f"Processos: {alive}/{len(pids) or '?'}\n"
            f"Agentes em execucao: {running}"
        )
        if active:
            state.tooltip += f"\nMissao: {active[:60]}"

    for project_id, mission_id, outcome in completions:
        _notify_mission_end(project_id, mission_id, outcome)

    icon = state.icon_ref
    if icon is not None:
        icon.icon = _make_icon(_icon_mode())
        icon.title = state.tooltip


def _icon_mode() -> str:
    """Platform health only — agent failures do not change tray color."""
    with state.lock:
        if not state.server_online:
            return "offline"
        total = state.processes_total
        alive = state.processes_alive
        if alive == 0:
            return "degraded"
        if not state.mcp_online:
            return "degraded"
        if total > 0 and alive < total:
            return "degraded"
        if state.running_agents > 0:
            return "active"
        return "online"


def _make_icon(mode: str) -> Image.Image:
    return make_tray_icon(mode, 64)


def export_tray_assets() -> None:
    """Gera PNGs em opendesign/assets/tray/ (1 celula, quadrado)."""
    from afp_brand_hive import make_app_icon_square  # noqa: E402

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    brand_dir = ROOT / "opendesign" / "assets" / "brand"
    brand_dir.mkdir(parents=True, exist_ok=True)
    for mode in ICON_MODES:
        for px in (16, 32, 64, 256):
            icon = make_tray_icon(mode, px) if px <= 64 else make_app_icon_square(mode, px)
            icon.save(ASSETS_DIR / f"afp-hive-tray-{mode}-{px}.png")
    # Referencia online 256 tambem em brand/
    make_app_icon_square("online", 256).save(brand_dir / "afp-hive-cell-square-256.png")


def _notify_mission_end(project_id: str, mission_id: str, outcome: str) -> None:
    if outcome == "failed":
        title = "AFP — Missao falhou"
    else:
        title = "AFP — Missao concluida"
    body = f"[{project_id}] {mission_id}"
    if Notification is None:
        return
    try:
        toast = Notification(app_id="Agent Factory Platform", title=title, msg=body, duration="short")
        if outcome == "completed":
            toast.set_audio(audio.Default, loop=False)
        else:
            toast.set_audio(audio.Reminder, loop=False)
        toast.show()
    except OSError:
        pass


def _run_powershell(script_args: list[str]) -> None:
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(START_SCRIPT),
        *script_args,
    ]
    subprocess.run(
        cmd,
        cwd=str(ROOT),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )


def _start_afp(_icon: pystray.Icon | None = None, _item: Any = None) -> None:
    def work() -> None:
        _run_powershell([])
        time.sleep(5)
        poll_status()

    threading.Thread(target=work, daemon=True).start()


def _stop_afp(_icon: pystray.Icon | None = None, _item: Any = None) -> None:
    def work() -> None:
        _run_powershell(["-Stop"])
        time.sleep(2)
        poll_status()

    threading.Thread(target=work, daemon=True).start()


def _restart_afp(_icon: pystray.Icon | None = None, _item: Any = None) -> None:
    def work() -> None:
        _run_powershell(["-Stop"])
        time.sleep(3)
        _run_powershell([])
        time.sleep(5)
        poll_status()

    threading.Thread(target=work, daemon=True).start()


def _open_dashboard(_icon: pystray.Icon | None = None, _item: Any = None) -> None:
    if _url_reachable(DASHBOARD_REACT):
        webbrowser.open(DASHBOARD_REACT)
    elif _url_reachable(DASHBOARD_LEGACY):
        webbrowser.open(DASHBOARD_LEGACY)
    else:
        webbrowser.open(DASHBOARD_REACT)


def _status_text(_item: pystray.MenuItem) -> str:
    with state.lock:
        return f"Status: {state.status_label}"


def _running_text(_item: pystray.MenuItem) -> str:
    with state.lock:
        return f"Agentes em execucao: {state.running_agents}"


def _process_text(_item: pystray.MenuItem) -> str:
    with state.lock:
        total = state.processes_total or "?"
        return f"Processos AFP: {state.processes_alive}/{total}"


def _mission_text(_item: pystray.MenuItem) -> str:
    with state.lock:
        if state.active_mission:
            return f"Missao ativa: {state.active_mission[:50]}"
        return "Missao ativa: —"


def _poll_loop() -> None:
    while True:
        try:
            poll_status()
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SEC)


def _build_menu() -> pystray.Menu:
    return pystray.Menu(
        pystray.MenuItem(_status_text, None, enabled=False),
        pystray.MenuItem(_running_text, None, enabled=False),
        pystray.MenuItem(_process_text, None, enabled=False),
        pystray.MenuItem(_mission_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Abrir Dashboard no navegador", _open_dashboard, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Iniciar AFP", _start_afp),
        pystray.MenuItem("Parar AFP", _stop_afp),
        pystray.MenuItem("Reiniciar AFP", _restart_afp),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair", lambda icon, item: icon.stop()),
    )


def _acquire_singleton() -> bool:
    """Uma unica instancia do tray (Windows mutex)."""
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, "Global\\AFP-SystemTray-Singleton")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        if handle:
            kernel32.CloseHandle(handle)
        return False
    return True


def main() -> None:
    if sys.platform != "win32":
        print("afp_tray.py suporta apenas Windows.", file=sys.stderr)
        sys.exit(1)

    if not _acquire_singleton():
        sys.exit(0)

    state.notified_completions = _load_notified()
    poll_status()
    icon = pystray.Icon(
        "afp-tray",
        _make_icon(_icon_mode()),
        "Agent Factory Platform",
        menu=_build_menu(),
    )
    state.icon_ref = icon

    threading.Thread(target=_poll_loop, daemon=True).start()
    icon.run()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--export-icons":
        export_tray_assets()
        print(f"Icones exportados em {ASSETS_DIR}")
    else:
        main()
