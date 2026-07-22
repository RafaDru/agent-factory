"""Smoke test: runs a lightweight objective through all AFP-Team agents,
then verifies Mission Control (Global + Local) reflects the results."""
import sys, json, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

from src.registry import get_registry
from src.mcp.server import run_objective
from src.dashboard.server import DashboardServer

def main():
    print("=" * 60)
    print("SMOKE TEST — Agent Factory Platform")
    print("=" * 60)
    registry = get_registry()

    # 1. Verify all agents are registered
    print("\n[1] Checking registered agents...")
    for proj in registry.list_projects():
        refs = registry.list_agent_refs(proj.project_id) or {}
        print(f"  📁 {proj.project_id}: {', '.join(refs.keys()) if refs else '(nenhum)'}")
        for aid, aref in refs.items():
            try:
                agent = registry.load_agent(proj.project_id, aid)
                actions = agent.get_actions() if hasattr(agent, 'get_actions') else {}
                print(f"    🤖 {aid} — {len(actions)} actions: {list(actions.keys())[:4]}")
            except Exception as e:
                print(f"    ❌ {aid}: {e}")

    # 2. Run a lightweight objective targeting AFP-Team
    print("\n[2] Running lightweight smoke objective on AFP-Team...")
    result = run_objective(
        project_id="AFP-Team",
        objective="Smoke test: list all source files in src/agents/ and run a quick syntax check on one file.",
        context="This is an automated smoke test. Keep it lightweight — read 1 file, run 1 check."
    )
    status = result.get("status", "?")
    summary = result.get("summary", result.get("output", str(result)[:200]))
    print(f"  Status: {status}")
    print(f"  Summary: {str(summary)[:300]}")
    if result.get("error_type"):
        print(f"  ⚠ Error: {result['error_type']} — {result.get('message','')}")

    # 3. Start dashboard briefly and verify Mission Control data
    print("\n[3] Starting dashboard to verify Mission Control...")
    server = DashboardServer(port=8080)
    server.start()
    time.sleep(2)

    import urllib.request, urllib.error
    try:
        # Fetch missions API
        resp = urllib.request.urlopen("http://127.0.0.1:8080/api/missions", timeout=5)
        missions_api = json.loads(resp.read().decode())
        print(f"  /api/missions: {len(missions_api)} entries")
        if missions_api:
            print(f"    Latest: {missions_api[-1].get('id','?')[:50]} — {missions_api[-1].get('status','?')}")

        # Fetch events (used by Mission Control to build missions)
        resp = urllib.request.urlopen("http://127.0.0.1:8080/api/events", timeout=5)
        events = json.loads(resp.read().decode())
        print(f"  /api/events: {len(events) if isinstance(events, list) else len(events.get('events',[]))} events")

        # Smoke test the dashboard HTML loads correctly
        resp = urllib.request.urlopen("http://127.0.0.1:8080/", timeout=5)
        html = resp.read().decode()
        checks = [
            ("Mission Control Global", "🚀 Mission Control Global" in html),
            ("Mission Control header", "Global" in html),
            ("Nav Home link", '🏠 Home' in html),
            ("Project selector", 'projectSelector' in html),
            ("Mission card V2", 'mission-card-v2' in html),
            ("Blocked status CSS", 'status-blocked' in html),
            ("Blocked status badge", 'blocked' in html),
            ("Agent chain helper", 'getTaskAgentChain' in html),
            ("Collapsible body", 'toggleMcBody' in html),
            ("Stale cleanup logic", 'STALE_MS' in html),
            ("Backfill objectives", 'Backfill objectives' in html),
            ("Project grouping", 'Mission Control Global' in html),
        ]
        print("\n  Dashboard HTML smoke checks:")
        for name, ok in checks:
            print(f"    {'✅' if ok else '❌'} {name}")

    except Exception as e:
        print(f"  ❌ Dashboard check failed: {e}")
    finally:
        server.stop()

    print("\n" + "=" * 60)
    print("SMOKE TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
