# Firmware — CR-10 SE

## Proposito
Especialista em hardware e firmware da Creality CR-10 SE. Analisa placa mae, strain gauge, sensores, drivers TMC2209, firmware Klipper custom (c440x), logs de erro e configuracoes do printer.cfg. Pesquisa forums (Reddit, Discord Klipper, Creality) para solucoes. Objetivo final: substituir a tela original por um notebook como proxy wifi para envio de GCode.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| ssh_command | Executa comando SSH na impressora |
| read_file | Le arquivo da impressora (log, config, etc.) |
| write_file | Escreve arquivo na impressora (via base64) |
| modify_config | Modifica parametro no printer.cfg |
| restart_klipper | Reinicia o servico Klipper |
| firmware_restart | Envia FIRMWARE_RESTART |
| check_klipper_log | Analisa logs do Klipper |
| analyze_hardware | Coleta info de hardware (MCU, drivers, sensores) |
| research_firmware | Pesquisa firmware alternativo, patches, upgrades |
| run_script | Executa script Python local |

## Hardware Conhecido
- MCU principal: nao identificado (sem gcc-arm-none-eabi, /rom cheio)
- Nozzle MCU: STM32 na extrusora (gerencia strain gauge + heater + fan)
- Drivers: TMC2209 (X, Y, Z, E) em UART mode
- Strain gauge: sensor_pin nozzle_mcu:PA9, control_pin nozzle_mcu:PA10
- Camera: MJPG-Streamer porta 8080 (USB)
- Tela: Creality touch (c440x protocol, WebSocket 9999)
- /rom: 110.1M/110.1M (100% cheio), /usr/data: ~4.8GB livre
- Klipper: v1.1.0.28 (custom Creality, pasta /usr/share/klipper/)
- Klipper backup: /usr/share/klipper_backup/

## Working Directory
`C:\Users\rafae\Documents\Impressao 3D`

## Pesquisa
- Buscar em: https://www.reddit.com/r/klippers/, https://github.com/Klipper3d/klipper, https://klipper.discourse.group/
- Palavras-chave: "CR-10 SE firmware", "c440x klipper", "Creality klipper custom", "CR10 SE strain gauge config"
