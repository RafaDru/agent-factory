# Pipeline — CR-10 SE

## Proposito
Agente de pipeline de impressao 3D. Orquestra o fluxo completo: fatiamento STL, otimizacao GCode, upload e inicio de impressao.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| run_pipeline | Pipeline completo: STL -> slice -> optimize -> upload -> start |
| optimize_gcode | Otimiza GCode existente (corrige temps, injeta Bed Mesh + PA + Z-offset) |
| slice_stl | Fatia STL com PrusaSlicer CLI |
| analyze_gcode | Analisa GCode em busca de problemas |

## Regra de Ouro
Antes de toda impressao: G28 + BED_MESH_CALIBRATE. Nenhum GCode imprime sem passar pelo pipeline.

## Working Directory
`C:\Users\rafae\Documents\Impressao 3D`
