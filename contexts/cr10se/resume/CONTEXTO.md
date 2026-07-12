# Resume — CR-10 SE

## Proposito
Agente de retomada de impressoes 3D apos falha (descolamento, entupimento, queda de energia). Usa o resume_toolkit.py para analise, probe e construcao de GCode de retomada.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| analyze_gcode | Analisa GCode e identifica ultima layer completa |
| probe_position | Faz probe da posicao atual do nozzle |
| build_resume | Constroi GCode de retomada a partir da ultima layer valida |
| validate_resume | Valida GCode de retomada (sintaxe, seguranca) |
| full_resume | Executa retomada completa: analyze -> probe -> build -> validate -> upload -> start |

## Importante
NAO usar RESUME da tela da CR-10 SE (injeta 240°C no hotend, degrada PTFE). Usar sempre o resume_toolkit.py.

## Working Directory
`C:\Users\rafae\Documents\Impressao 3D`
