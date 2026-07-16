import subprocess
import time
import urllib.request
import json

# Inicia o servidor em background usando subprocess (Windows detached)
cmd = 'python -c "from src.dashboard.server import DashboardServer; s = DashboardServer(port=8080); s.start()"'
subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS, shell=True)

# Aguarda o servidor iniciar
time.sleep(3)

# Faz a requisição GET para /api/events?project=AFP-Team
try:
    with urllib.request.urlopen('http://localhost:8080/api/events?project=AFP-Team', timeout=5) as response:
        data = json.loads(response.read().decode())
        num_events = len(data) if isinstance(data, list) else 0
        print(f'Número de eventos retornados: {num_events}')
        # Salva o resultado em arquivo para validação
        with open('smoke_output.txt', 'w') as f:
            f.write(str(num_events))
except Exception as e:
    print(f'Erro na requisição: {e}')
    with open('smoke_output.txt', 'w') as f:
        f.write('0')
