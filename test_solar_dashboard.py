import urllib.request, json

base = "http://localhost:8080"

# Test /api/projects
r = urllib.request.urlopen(f"{base}/api/projects", timeout=5)
projects = json.loads(r.read())
print(f"Projects: {projects}")

# Test /api/events for solar
r = urllib.request.urlopen(f"{base}/api/events?project=solarman-solar-monitor", timeout=5)
events = json.loads(r.read())
print(f"Solar events: {len(events.get('events', []))}")

# Test /api/status for each project
for p in projects:
    r = urllib.request.urlopen(f"{base}/api/status?project={p}", timeout=5)
    s = json.loads(r.read())
    print(f"Status {p}: phase={s.get('phase')}")

# Test debug
r = urllib.request.urlopen(f"{base}/api/debug", timeout=5)
debug = json.loads(r.read())
print(f"Debug notifiers: {debug.get('notifier_keys')}")
