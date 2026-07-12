"""MCP client — executa objetivo solar com caminhos corrigidos."""
import io, sys, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    async with sse_client('http://127.0.0.1:8081/sse') as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            result = await session.call_tool('run_objective', {
                'project_id': 'solarman-solar-monitor',
                'objective': 'Aplicar melhorias no sistema solar: ler schema.sql, ler monitor.py, rodar pytest, gerar relatorio',
                'context': 'Diretorio: C:\\Users\\rafae\\agent-factory. Usar read_file para arquivos, run_script para scripts, run_git para git.',
            })

            for c in result.content:
                data = json.loads(c.text)
                print(f"Status: {data.get('status','?')} | Duracao: {data.get('duration_ms',0):.0f}ms")
                steps = data.get('output',{}).get('steps',[])
                for s in steps:
                    r = s.get('result',{})
                    st = r.get('status','?') if isinstance(r,dict) else '?'
                    out = str(r)[:300].replace('\n',' ')
                    print(f"  [{s['status']:6}] {s.get('agent_id','?')} / {s['step']}")
                    print(f"         -> {st}: {out}")

asyncio.run(main())
