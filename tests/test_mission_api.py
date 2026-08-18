"""Testes de build_mission_api_entry para /api/missions."""
from pathlib import Path

from src.protocols.mission import build_mission_api_entry, save_mission_record
from src.protocols.schema import MissionRecord, MissionStatus


def test_build_mission_api_entry_from_status_json(tmp_path):
    mission_dir = tmp_path / "missao-test"
    mission_dir.mkdir()
    (mission_dir / "input").mkdir()
    (mission_dir / "input" / "Mission_Context.md").write_text(
        "## Objetivo Curado\nObjetivo via contexto\n",
        encoding="utf-8",
    )
    save_mission_record(
        mission_dir,
        MissionRecord(
            mission_id="missao-test",
            project_id="AFP-Team",
            status=MissionStatus.COMPLETED,
            goal="Goal canonico",
            objective="Objetivo canonico",
            task_count=1,
            completed=1,
            message="Missao concluida",
        ),
    )

    entry = build_mission_api_entry(mission_dir)
    assert entry["status"] == "completed"
    assert entry["mission_id"] == "missao-test"
    assert entry["project_id"] == "AFP-Team"
    assert "Objetivo canonico" in entry["objective"]


def test_build_mission_api_entry_inferred_without_status_json(tmp_path):
    mission_dir = tmp_path / "missao-infer"
    out = mission_dir / "output" / "tasks" / "step-1" / "dev"
    out.mkdir(parents=True)
    (out / "result.md").write_text("**Status:** success\n", encoding="utf-8")
    (mission_dir / "input").mkdir()
    (mission_dir / "input" / "Mission_Context.md").write_text(
        "## Objetivo\nInferido do contexto\n",
        encoding="utf-8",
    )

    entry = build_mission_api_entry(mission_dir)
    assert entry["status"] == "completed"
    assert entry["completed"] == 1
