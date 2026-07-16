"""
Gerenciador de servidores Agent Factory Platform.
Uso: python server_ctl.py <start|stop|restart|status>
"""
import sys, os, json, time, signal, subprocess
from pathlib import Path

if sys.platform == "win32":
    _pid_cache = set()

    def _refresh_pids():
        global _pid_cache
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                          capture_output=True, text=True)
        _pid_cache = set()
        for line in r.stdout.splitlines()[1:]:
            parts = line.split(",")
            if len(parts) >= 2:
                try: _pid_cache.add(int(parts[1].strip('"')))
                except: pass

    def _is_alive(pid):
        if not pid: return False
        _refresh_pids()
        return pid in _pid_cache

    def _kill(pid):
        if not pid: return
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
else:
    def _is_alive(pid):
        if not pid: return False
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _kill(pid):
        if not pid: return
        try:
            os.kill(pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass

PID_FILE = Path(".agent-factory") / ".server_pids.json"

def _save_pids(afp_pid=None, dash_pid=None):
    data = {}
    if PID_FILE.exists():
        data = json.loads(PID_FILE.read_text())
    if afp_pid is not None: data["afp"] = afp_pid
    if dash_pid is not None: data["dashboard"] = dash_pid
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(json.dumps(data, indent=2))

def _load_pids():
    if not PID_FILE.exists(): return {}
    return json.loads(PID_FILE.read_text())

def cmd_status():
    pids = _load_pids()
    for name in ("afp", "dashboard"):
        pid = pids.get(name)
        alive = _is_alive(pid)
        pid_str = str(pid) if pid else '--'
        print(f"  {name:12s} PID={pid_str:6s} {'RUNNING' if alive else 'STOPPED'}")
    return pids

def cmd_stop():
    pids = _load_pids()
    for name, pid in pids.items():
        if _is_alive(pid):
            _kill(pid)
            print(f"  {name}: stopped PID {pid}")
    PID_FILE.unlink(missing_ok=True)

def cmd_start():
    # Kill any existing
    cmd_stop()
    time.sleep(1)

    base = Path(__file__).parent

    # Start AFP (MCP + demo)
    proc_afp = subprocess.Popen(
        [sys.executable, "-X", "utf8", "start_agent_factory.py", "--demo", "--mcp"],
        cwd=base,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    _save_pids(afp_pid=proc_afp.pid)
    print(f"  AFP: started PID {proc_afp.pid}")

    time.sleep(2)

    # Start Dashboard
    proc_dash = subprocess.Popen(
        [sys.executable, "-c",
         "from src.dashboard.server import DashboardServer; s = DashboardServer(port=8080); s.start()"],
        cwd=base,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    _save_pids(dash_pid=proc_dash.pid)
    print(f"  Dashboard: started PID {proc_dash.pid}")

    time.sleep(3)

    # Verify
    print()
    cmd_status()

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "start": cmd_start()
    elif action == "stop": cmd_stop()
    elif action == "restart": cmd_start()
    elif action == "status": cmd_status()
    elif action == "killall":
        me = os.getpid()
        for proc in subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                                   capture_output=True, text=True).stdout.splitlines()[1:]:
            parts = proc.split(",")
            if len(parts) >= 2:
                try:
                    pid = int(parts[1].strip('"'))
                    if pid != me: _kill(pid)
                except: pass
        PID_FILE.unlink(missing_ok=True)
        print("  Todos os servidores parados.")
    else: print(f"Uso: {sys.argv[0]} <start|stop|restart|status|killall>")
