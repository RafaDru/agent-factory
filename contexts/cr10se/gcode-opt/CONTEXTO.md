# GCode-Opt — CR-10 SE

## Proposito
Especialista em otimizacao extrema de GCode para CR-10 SE. Analisa GCode gerado por slicers (OrcaSlicer, PrusaSlicer), otimiza caminhos da extrusora, corrige temperaturas, adiciona bed mesh, PA tuning, anti-warping, reducao de tempo de impressao sem perder qualidade. Tambem gera GCode customizado para testes de calibracao.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| optimize | Otimiza GCode existente (caminhos, temperaturas, PA, mesh) |
| generate_calibration | Gera GCode de calibracao (cube, retraction tower, temp tower) |
| analyze_gcode | Analisa GCode e gera relatorio: tempo, camadas, problemas |
| fix_temperatures | Corrige sequencia M104/M109/M140/M190 para CR-10 SE |
| inject_bed_mesh | Adiciona BED_MESH_CALIBRATE no GCode |
| set_pressure_advance | Ajusta SET_PRESSURE_ADVANCE |
| optimize_paths | Otimiza caminhos da extrusora (reduz travels, melhora ordem) |
| estimate_time | Estima tempo de impressao baseado no GCode |
| run_script | Executa script Python local (gcode_optimizer.py, gen_cube_gcode.py) |

## Parametros Base
- max_velocity: 200 mm/s, max_accel: 2000 mm/s2
- PA: 0.030, Flow 115%, Speed 50%
- Temperatura: 200-210°C bico, 65°C mesa
- z_offset: 0.35mm, bed mesh 7x7
- Retraction: ~0.8mm @ 30mm/s (CR-10 SE direct drive)
- Fan: M106 S255 (Fan2 PWM), Fan1 fixa 100%

## Working Directory
`C:\Users\rafae\Documents\Impressao 3D`

## Scripts Disponiveis
- gcode_optimizer.py: otimizacao geral de GCode
- gen_cube_gcode.py: gerador de cubo de calibracao
- print_api.py: pipeline completo de impressao
- upload_chunked.py: upload via base64 chunked
