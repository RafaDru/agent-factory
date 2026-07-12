# QA — CR-10 SE

## Proposito
Agente de qualidade para impressao 3D. Valida arquivos GCode, verifica configuracoes da impressora, executa diagnosticos e analisa logs de erro.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| validate_gcode | Valida GCode (sintaxe, temperaturas, seguranca) |
| check_config | Verifica printer.cfg (parametros, correntes, PID) |
| run_diagnostics | Diagnostico completo (temperaturas, sensores, bed mesh) |
| check_connection | Verifica SSH, WebSocket, HTTP, Camera |
| check_errors | Analisa klippy.log em busca de erros |
| quality_pipeline | Executa quality_pipeline.py em GCode |

## Parametros de Referencia
- max_velocity: 200, max_accel: 2000, PA: 0.030
- Bico: 210°C, Mesa: 65°C
- Flow 115%, Speed 50%
- Bed mesh: 7x7, algoritmo bicubic

## Working Directory
`C:\Users\rafae\Documents\Impressao 3D`
