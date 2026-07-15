# Visao-LLM — CR-10 SE

## Proposito
Agente de monitoramento visual de impressao 3D usando analise de imagens via LLM. A cada minuto durante a impressao, captura snapshot da camera MJPG, analisa via LLM multimodal (Gemini, Groq LLaMA Vision, etc.), detecta anomalias (primeira camada falhando, warping, stringing, blob, extrusao irregular). Otimiza o momento da captura: aguarda a extrusora estar no lado direito da mesa (camera esta na esquerda) para melhor angulo.

## Acoes Disponiveis

| Acao | Descricao |
|------|-----------|
| capture_snapshot | Captura snapshot da camera MJPG (porta 8080) |
| get_position | Le posicao atual da extrusora (GET_POSITION) |
| wait_for_position | Aguarda extrusora chegar a posicao X especifica |
| analyze_snapshot | Envia snapshot para LLM multimodal e analisa qualidade |
| start_monitoring | Inicia loop de monitoramento: posiciona -> captura -> analisa |
| stop_monitoring | Para o loop de monitoramento |
| check_anomaly | Verifica anomalia na impressao atual |
| save_artifact | Salva snapshot e relatorio de analise |

## Metodo de Captura Inteligente
1. Aguarda extrusora mover para X > 110 (lado direito, camera na esquerda)
2. Captura snapshot via wget http://localhost:8080/?action=snapshot
3. Envia para LLM com prompt: "Analise esta imagem de impressao 3D. Identifique: 1) Aderencia da primeira camada 2) Warping 3) Stringing 4) Blobs/under-extrusion 5) Qualidade geral"
4. Se anomalia detectada: salva artefato + alerta

## Working Directory
`C:\Users\rafae\Documents\Impressao 3D`
