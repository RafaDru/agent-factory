"""MCP client to trigger an objective on the solarman-solar-monitor project."""
import json, sys, uuid, asyncio, httpx, time

MCP_URL = "http://127.0.0.1:8081"

async def call_objective():
    session_id = uuid.uuid4().hex
    messages_url = f"{MCP_URL}/messages/?session_id={session_id}"

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Connect to SSE to get tool list
        print(f"[client] Connecting to SSE (session={session_id})...")
        sse_resp = await client.stream("GET", f"{MCP_URL}/sse")
        tool_list = None
        async with sse_resp:
            async for line in sse_resp.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get("method") == "tools/list":
                                tool_list = item.get("params", {}).get("result", {})
                                break
                    if tool_list:
                        break

        # 2. Call run_objective
        req_id = 1
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {
                "name": "run_objective",
                "arguments": {
                    "project_id": "solarman-solar-monitor",
                    "objective": "Executar as melhorias preparadas para o sistema de energia solar: (1) criar as 5 SQL views (v_performance_ratio, v_autoconsumo, v_economia, v_assimetria_inversores, v_alerta_limpeza), (2) implementar as funcoes Python de monitoramento (send_weekly_report, check_panel_degradation, get_dashboard_metrics), (3) verificar integracao com banco Supabase, (4) rodar testes e gerar relatorio de resultados.",
                    "context": "Usar SmartRouter com fallback para LLM (groq > deepseek > mimo > openrouter > cerebras). As views SQL ja estao definidas em schema.sql. As funcoes Python ja estao em monitor.py. Verificar se o schema.sql foi aplicado ao Supabase e se as funcoes rodam sem erro.",
                }
            }
        }

        print(f"\n[client] Calling run_objective...")
        resp = await client.post(messages_url, json=payload)
        print(f"[client] POST status: {resp.status_code}")
        text = resp.text
        print(f"[client] Response: {text[:1000]}")
        
        # 3. Wait for SSE events
        print(f"\n[client] Waiting for completion events (30s timeout)...")
        deadline = time.time() + 30
        sse_resp2 = await client.stream("GET", f"{MCP_URL}/sse")
        async with sse_resp2:
            async for line in sse_resp2.aiter_lines():
                if time.time() > deadline:
                    break
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        print(f"[event] {json.dumps(data, indent=2)[:500]}")
                    except:
                        print(f"[raw] {line[:300]}")

if __name__ == "__main__":
    asyncio.run(call_objective())
