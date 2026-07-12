# Visao — CR-10 SE

## Proposito
Agente de monitoramento por visao computacional durante impressao 3D. Detecta anomalias, patinacao da extrusora, e crescimento da peca usando OpenCV.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| start_monitoring | Inicia print_health_monitor.py em background |
| analyze_frame | Analisa frame da camera (ROI grid, nozzle tracker, anomaly scoring) |
| check_anomaly | Verifica anomalia na impressao atual |
| capture_reference | Captura foto de referencia |
| run_orchestrator | Inicia VisionOrchestrator com monitoramento ciclico |

## Metodo de Deteccao
- ROI grid 8x6 para deteccao de crescimento
- Nozzle tracker por brightness threshold
- Extrusion verifier por comparacao de frames
- Anomaly scorer com auto-pause em score > 0.5

## Working Directory
`C:\Users\rafae\Documents\Impressao 3D`
