"""Testes de auto-discovery — ignora contexts/_template/."""
from src.project_discovery import discover_projects


def test_discovery_skips_template():
    ids = [p["project"]["project_id"] for p in discover_projects()]
    assert "{{PROJECT_ID}}" not in ids
    assert all(not pid.startswith("_") for pid in ids)
    assert "demo-onboarding" in ids
    assert "afp-team" not in ids
    assert "cr10se" not in ids
    assert "solarman-solar-monitor" not in ids
