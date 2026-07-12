# Klipper — CR-10 SE

## Proposito
Agente de comunicacao direta com a Creality CR-10 SE. Envia comandos GCode, le status, modifica configuracoes e gerencia arquivos via SSH, WebSocket e Klipper UDS.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| send_gcode | Envia comando GCode via SSH echo > /tmp/printer |
| read_status | Le status atual via WebSocket |
| get_temps | Le temperaturas (bico, mesa) |
| modify_config | Modifica printer.cfg (section, param, value) |
| restart_klipper | Reinicia servico Klipper |
| upload_file | Upload de GCode via HTTP |
| start_print | Inicia impressao de arquivo |
| check_status | Verifica conectividade |
| run_script | Executa script do diretorio Impressao 3D |

## Parametros da Impressora
- max_velocity: 200, max_accel: 2000, PA: 0.030
- Temperatura ideal: 210°C bico / 65°C mesa
- Flow: M221 S115, Speed: M220 S50
- Correntes: X=0.65, Y=0.60, Z=0.80, E=0.70

## Working Directory
`C:\Users\rafae\Documents\Impressao 3D`
