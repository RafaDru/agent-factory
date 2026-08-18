"""Healthcheck: verifica AFP sem travar no Get-Process."""
import subprocess, sys, json, os, time, urllib.request

exit_code = 0
checks = []

# 1. RabbitMQ
try:
    r = subprocess.run(["docker", "ps", "--filter", "name=afp-rabbitmq", "--format", "{{.Status}}"],
                       capture_output=True, text=True, timeout=5)
    if "healthy" in r.stdout.lower() or "up" in r.stdout.lower():
        checks.append(("RabbitMQ", "OK", r.stdout.strip()))
    else:
        checks.append(("RabbitMQ", "FAIL", "nao encontrado"))
        exit_code = 1
except Exception as e:
    checks.append(("RabbitMQ", "FAIL", str(e)))
    exit_code = 1

# 2. Dashboard (port 8080)
try:
    r = urllib.request.urlopen("http://localhost:8080/api/projects", timeout=3)
    if r.status == 200:
        checks.append(("Dashboard (8080)", "OK", "200"))
    else:
        checks.append(("Dashboard (8080)", "WARN", str(r.status)))
except Exception as e:
    checks.append(("Dashboard (8080)", "FAIL", str(e)))
    exit_code = 1

# 3. MCP (port 8081)
try:
    r = urllib.request.urlopen("http://localhost:8081/sse", timeout=3)
    checks.append(("MCP (8081)", "OK", str(r.status)))
except Exception as e:
    checks.append(("MCP (8081)", "WARN", str(e)))

# 4. PID file - check processes via Windows API
pid_file = os.path.join(os.path.dirname(__file__), ".agent-factory", "afp.pid")
if os.path.exists(pid_file):
    import ctypes
    kernel32 = ctypes.windll.kernel32
    pids = [int(line.strip().strip('\ufeff')) for line in open(pid_file) if line.strip().strip('\ufeff').isdigit()]
    alive_pids = set()
    for pid in pids:
        handle = kernel32.OpenProcess(0x0400, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            alive_pids.add(pid)
    dead = [p for p in pids if p not in alive_pids]
    if dead:
        checks.append(("Processos", "WARN", f"{len(pids)-len(dead)}/{len(pids)} vivos, mortos: {dead}"))
    else:
        checks.append(("Processos", "OK", f"{len(pids)}/{len(pids)} vivos"))
else:
    checks.append(("Processos", "FAIL", "afp.pid nao encontrado"))
    exit_code = 1

# Summary
print("=== AFP Healthcheck ===")
for name, status, detail in checks:
    print(f"  [{status}] {name}: {detail}")
print("---")
if exit_code == 0:
    print("Status: OPERACIONAL")
else:
    print("Status: COM FALHAS")
sys.exit(exit_code)
