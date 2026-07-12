"""
Test full MCP flow: run_objective with LLM-generated plan
"""
import io, sys, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

MCP_URL = 'http://127.0.0.1:8081/sse'


async def test():
    async with sse_client(MCP_URL) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            # run_objective with just a goal (triggers LLM plan generation)
            print('=== run_objective: coordenador com LLM ===')
            result = await session.call_tool('run_objective', {
                'project_id': 'agent-factory-dev',
                'objective': 'Listar arquivos Python em src/ com list_directory',
                'context': 'Usar pattern *.py para filtrar',
            })
            for c in result.content:
                data = json.loads(c.text)
                status = data.get('status', '?')
                print(f'Status: {status}')

                if 'error_type' in data:
                    print(f'ERRO: {data["error_type"]}: {data.get("message","")}')
                    print(f'Hint: {data.get("hint","")}')
                    continue

                out = data.get('output', {})
                steps = out.get('steps', [])
                print(f'Tarefas: {len(steps)}')
                for s in steps:
                    marker = '+' if s['status'] == 'ok' else '-'
                    result_preview = ''
                    if s['status'] == 'ok':
                        r = s.get('result', {})
                        if isinstance(r, dict):
                            items = r.get('items', r.get('files', []))
                            result_preview = f', {len(items)} itens'
                    elif s['status'] == 'error':
                        result_preview = f', erro: {s.get("error","?")}'
                    print(f'  [{marker}] {s["step"]} ({s["agent_id"]}): {s["status"]}{result_preview}')

    print('Teste concluido!')


asyncio.run(test())
