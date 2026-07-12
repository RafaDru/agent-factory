"""MCP client - Executa melhorias solares com agentes corrigidos."""
import io, sys, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

MCP_URL = 'http://127.0.0.1:8081/sse'

async def main():
    async with sse_client(MCP_URL) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            print("=== 1. Status do Projeto Solar ===")
            result = await session.call_tool('get_project_status', {
                'project_id': 'solarman-solar-monitor'
            })
            for c in result.content:
                data = json.loads(c.text)
                print(f"  Projeto: {data['config']['name']}")
                print(f"  Agentes: {data['agent_refs']}")
                print(f"  Eventos: {data['total_events']} (ok: {data['completed_events']}, fail: {data['failed_events']})")

            print("\n=== 2. Executando Melhorias Solares ===")
            result = await session.call_tool('run_objective', {
                'project_id': 'solarman-solar-monitor',
                'objective': """Aplicar as melhorias no sistema de energia solar:

1. SQL Views: executar as 5 views no Supabase
   - src/supabase/migrations/schema.sql contem as definicoes

2. Python Monitor: verificar se as funcoes existem e rodam
   - src/monitor.py contem send_weekly_report, check_panel_degradation, get_dashboard_metrics

3. Testes: executar pytest na pasta tests/

4. Relatorio: gerar analise do que funciona e o que precisa de ajuste""",
                'context': """Usar SmartRouter para LLM (groq > deepseek > mimo).
Diretorio: C:\\Users\\rafae\\agent-factory
Arquivos importantes:
- src/supabase/migrations/schema.sql
- src/monitor.py
- tests/

O desenvolvedor deve usar read_file para ler os arquivos antes de executar.
Para rodar scripts, usar run_script com comando shell.
Para git, usar run_git.
"""
            })

            print("\n=== 3. Resultado do Coordenador ===")
            for c in result.content:
                data = json.loads(c.text)
                if 'error_type' in data:
                    print(f"  ERRO: {data['error_type']}: {data.get('message','')}")
                    return

                print(f"  Status: {data.get('status','?')}")
                print(f"  Task ID: {data.get('task_id','?')}")
                print(f"  Duracao: {data.get('duration_ms',0):.0f}ms")
                out = data.get('output', {})

                steps = out.get('steps', [])
                if steps:
                    print(f"\n  Tarefas executadas ({len(steps)}):")
                    for s in steps:
                        r = s.get('result', {})
                        if isinstance(r, dict):
                            r_status = r.get('status', '?')
                            r_out = r.get('stdout', '') or r.get('response', '') or r.get('error', '')
                            r_out = r_out[:200].replace('\n', ' ')
                        else:
                            r_status = '?'
                            r_out = str(r)[:200]
                        print(f"    [{s['status']}] {s.get('agent_id','?')} / {s['step']}")
                        print(f"      result: {r_status} | {r_out}")
                        if r.get('stderr'):
                            print(f"      stderr: {r['stderr'][:200]}")

            # Monitor events
            print("\n=== 4. Eventos Recentes ===")
            result = await session.call_tool('read_events', {
                'project_id': 'solarman-solar-monitor',
                'limit': 15
            })
            for c in result.content:
                events = json.loads(c.text)
                if isinstance(events, list):
                    for e in events[-10:]:
                        ag = e.get('agent_id','') or '(sistema)'
                        st = e.get('status','?')
                        msg = e.get('message','')[:120]
                        print(f"  [{st:10}] {ag:15} | {msg}")

    print("\nConcluido!")

asyncio.run(main())
