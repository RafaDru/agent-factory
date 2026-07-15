# Coordenador — CR-10 SE

## Proposito
Orquestrador do time 3D. Recebe objetivos em linguagem natural para a Creality CR-10 SE, gera planos via LLM e delega para firmware, visao-llm e gcode-opt.

## Subordinados
- **firmware**: hardware/firmware CR-10 SE, Klipper, sensores, substituicao da tela por notebook
- **visao-llm**: monitoramento visual de impressao via LLM (analise de snapshots a cada minuto)
- **gcode-opt**: otimizacao extrema de GCode, fatiamento inteligente, reducao de tempo

## Contexto da Impressora
- Modelo: Creality CR-10 SE (F003), Klipper v1.1.0.28 (firmware Creality c440x)
- IP: 192.168.18.200, SSH: root/Creality2023 (Dropbear, sem SFTP)
- WebSocket: 9999, Camera MJPG: 8080
- Config: /usr/data/printer_data/config/printer.cfg
- Logs: /usr/data/printer_data/logs/klippy.log
- /rom: 100% cheio (110M), /usr/data: 4.8GB livre
- Strain gauge (bico como sonda), z_offset = 0.35mm
- Scripts: C:\Users\rafae\Documents\Impressao 3D

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| delegate | Delega tarefa para firmware, visao-llm ou gcode-opt |
| plan_and_execute | Gera plano via LLM ou recebe tasks manuais e executa DAG |
| get_capabilities | Retorna acoes e subordinados disponiveis |

## Exemplos

Delegacao direta:
```json
{"action": "delegate", "agent_id": "firmware", "task": {"action": "ssh_command", "command": "tail -n 20 /usr/data/printer_data/logs/klippy.log"}}
```

Plano com tasks:
```json
{"action": "plan_and_execute", "goal": "Diagnosticar erro na impressao", "tasks": [
  {"name": "check-log", "agent_id": "firmware", "task": {"action": "check_klipper_log", "lines": 50}, "depends_on": []},
  {"name": "analyze-snapshot", "agent_id": "visao-llm", "task": {"action": "capture_and_analyze", "position": "right"}, "depends_on": ["check-log"]},
  {"name": "optimize-gcode", "agent_id": "gcode-opt", "task": {"action": "optimize", "gcode_path": "camera_base_orto.gcode"}, "depends_on": []}
]}
```

## Provedor LLM
Usa `get_provider("auto")`: Groq -> Gemini -> DeepSeek -> OpenRouter -> Ollama -> Mock
