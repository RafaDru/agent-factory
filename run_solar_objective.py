"""MCP client — dispara objetivo solar e monitora execucao."""
import io, sys, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

MCP_URL = 'http://127.0.0.1:8081/sse'

async def test():
    print("=== Conectando ao MCP Server ===")
    async with sse_client(MCP_URL) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            print("  Conectado!\n")

            # 1. Check project status
            print("=== Status do Projeto Solar ===")
            result = await session.call_tool('get_project_status', {
                'project_id': 'solarman-solar-monitor'
            })
            for c in result.content:
                print(f"  {json.dumps(json.loads(c.text), indent=2)}")
            print()

            # 2. Run objective
            print("=== run_objective: Melhorias Solar ===")
            result = await session.call_tool('run_objective', {
                'project_id': 'solarman-solar-monitor',
                'objective': """
Validar e executar as melhorias preparadas para o sistema de energia solar:

1. SQL Views: verificar se as 5 views foram aplicadas ao Supabase
   - v_performance_ratio
   - v_autoconsumo
   - v_economia
   - v_assimetria_inversores
   - v_alerta_limpeza

2. Funcoes Python: testar as 3 funcoes em monitor.py
   - send_weekly_report
   - check_panel_degradation
   - get_dashboard_metrics

3. Integracao: verificar conexao com banco e tabelas existentes

4. Gerar relatorio de resultados apontando:
   - O que funciona
   - O que precisa de ajuste
   - Proximos passos
""",
                'context': """
Usar SmartRouter (groq > deepseek > mimo > openrouter > cerebras) como fallback chain para decisoes do coordenador.

Arquivos de referencia:
- schema.sql (src/supabase/migrations/): contem as 5 SQL views
- monitor.py (src/): contem as 3 funcoes Python
- Workdir: C:\\Users\\rafae\\agent-factory

Projeto Supabase: solarman-solar-monitor
"""
            })

            for c in result.content:
                data = json.loads(c.text)
                if 'error_type' in data:
                    print(f"  ERRO: {data['error_type']}: {data.get('message', '')}")
                    return

                print(f"  Status: {data.get('status', '?')}")
                print(f"  Task ID: {data.get('task_id', '?')}")
                print(f"  Duracao: {data.get('duration_ms', '?')}ms")

                out = data.get('output', {})

                # Show plan
                plan = out.get('plan', out.get('tasks', []))
                if plan:
                    print(f"\n  Plano ({len(plan)} tarefas):")
                    for t in plan:
                        agent = t.get('agent_id', '?')
                        action = t.get('task', {}).get('action', t.get('action', '?'))
                        name = t.get('name', t.get('id', f'{action}'))
                        print(f"    [{agent}] {name}")

                # Show individual results
                results = out.get('results', out.get('executions', []))
                if results:
                    print(f"\n  Resultados ({len(results)}):")
                    for r in results:
                        status = r.get('status', '?')
                        agent = r.get('agent_id', '?')
                        r_out = r.get('output', r.get('result', {}))
                        summary = r.get('summary', '')
                        if isinstance(r_out, dict):
                            r_out = json.dumps(r_out, indent=2)[:200]
                        print(f"    [{status}] {agent}: {summary or str(r_out)[:150]}")

                summary = data.get('summary', '')
                if summary:
                    print(f"\n  Resumo: {summary}")

            # 3. Read events
            print("\n=== Eventos do Projeto Solar ===")
            result = await session.call_tool('read_events', {
                'project_id': 'solarman-solar-monitor',
                'limit': 20
            })
            for c in result.content:
                events = json.loads(c.text)
                if isinstance(events, list):
                    for e in events[-10:]:
                        print(f"  [{e.get('status','?')}] {e.get('agent_id','?')}: {e.get('message','')[:100]}")

    print("\nConcluido!")

asyncio.run(test())
