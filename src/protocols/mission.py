"""Persistência e leitura de status canônico de missões."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.protocols.schema import MissionRecord, MissionStatus

MISSION_STATUS_FILE = "status.json"


def mission_status_path(mission_dir: Path) -> Path:
    return mission_dir / MISSION_STATUS_FILE


def load_mission_record(mission_dir: Path) -> Optional[MissionRecord]:
    path = mission_status_path(mission_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return MissionRecord.model_validate(data)
    except (json.JSONDecodeError, ValueError, OSError):
        return None


def save_mission_record(mission_dir: Path, record: MissionRecord) -> str:
    mission_dir.mkdir(parents=True, exist_ok=True)
    path = mission_status_path(mission_dir)
    path.write_text(
        record.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return str(path)


def infer_mission_status(completed: int, failed: int, task_count: int) -> MissionStatus:
    if task_count == 0:
        return MissionStatus.PLANNED
    if failed == 0 and completed > 0:
        return MissionStatus.COMPLETED
    if failed > 0 and completed > 0:
        return MissionStatus.PARTIAL
    if failed > 0:
        return MissionStatus.FAILED
    return MissionStatus.RUNNING


def _objective_from_mission_context(mission_dir: Path) -> str:
    ctx_path = mission_dir / "input" / "Mission_Context.md"
    if not ctx_path.exists():
        return ""
    content = ctx_path.read_text(encoding="utf-8")
    for i, line in enumerate(content.split("\n")):
        if line.startswith("## Objetivo"):
            parts = []
            j = i + 1
            lines = content.split("\n")
            while j < len(lines) and not lines[j].startswith("##"):
                if lines[j].strip():
                    parts.append(lines[j])
                j += 1
            return "\n".join(parts).strip()
    return ""


def _task_statuses_from_output(mission_dir: Path) -> tuple[int, int, int, list[dict]]:
    tasks_out = mission_dir / "output" / "tasks"
    task_count = 0
    task_statuses: list[dict] = []

    if not tasks_out.exists():
        return 0, 0, 0, task_statuses

    for task_dir in sorted(tasks_out.iterdir()):
        if not task_dir.is_dir():
            continue
        task_count += 1
        for agent_dir in task_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            result = agent_dir / "result.md"
            if not result.exists():
                continue
            txt = result.read_text(encoding="utf-8")
            if "**Status:** success" in txt:
                st = "completed"
            elif "**Status:** failure" in txt:
                st = "failed"
            else:
                st = "pending"
            task_statuses.append(
                {"task": task_dir.name, "agent": agent_dir.name, "status": st}
            )

    completed = sum(1 for t in task_statuses if t["status"] == "completed")
    failed = sum(1 for t in task_statuses if t["status"] == "failed")
    return task_count, completed, failed, task_statuses


def build_mission_api_entry(mission_dir: Path) -> dict:
    """Monta payload REST de uma missao para /api/missions."""
    mission_id = mission_dir.name
    record = load_mission_record(mission_dir)
    task_count, completed, failed, task_statuses = _task_statuses_from_output(mission_dir)

    if record:
        task_count = record.task_count or task_count
        completed = record.completed if record.completed else completed
        failed = record.failed if record.failed is not None else failed
        status = record.status.value
        objective = (record.objective or record.goal or _objective_from_mission_context(mission_dir))[:200]
        entry = {
            "id": mission_id,
            "mission_id": mission_id,
            "project_id": record.project_id,
            "status": status,
            "objective": objective,
            "goal": (record.goal or "")[:200],
            "task_count": task_count,
            "completed": completed,
            "failed": failed,
            "skipped": record.skipped,
            "message": record.message,
            "task_statuses": task_statuses,
            "started_at": record.started_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }
        if record.completed_at:
            entry["completed_at"] = record.completed_at.isoformat()
        return entry

    status = infer_mission_status(completed, failed, task_count).value
    return {
        "id": mission_id,
        "mission_id": mission_id,
        "status": status,
        "objective": _objective_from_mission_context(mission_dir)[:200],
        "task_count": task_count,
        "completed": completed,
        "failed": failed,
        "task_statuses": task_statuses,
    }
