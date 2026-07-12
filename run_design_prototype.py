import io, sys, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    async with sse_client('http://127.0.0.1:9091/sse') as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool('run_objective', {
                'project_id': 'solarman-solar-monitor',
                'objective': 'Criar o protótipo visual (HTML/CSS) do dashboard solar com gráficos e métricas.',
                'context': 'Agente Design deve priorizar o protótipo. O Desenvolvedor pode fornecer dados via monitor.py.'
            })
            for c in result.content:
                data = json.loads(c.text)
                print(f"Status: {data.get('status','?')}")
                steps = data.get('output', {}).get('steps', [])
                for s in steps:
                    r = s.get('result', {})
                    if isinstance(r, dict):
                        html = r.get('html', '')
                        print(f"  [{s['status']}] {s.get('agent_id','?')} / {s['step']} -> HTML: {html[:100]}...")
                    else:
                        print(f"  [{s['status']}] {s.get('agent_id','?')} / {s['step']}")

asyncio.run(main())
