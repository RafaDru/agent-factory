"""
Test coordinator LLM plan generation via MCP run_objective
"""
import io, sys, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

MCP_URL = 'http://127.0.0.1:8081/sse'
ROOT = r'C:\Users\rafae\agent-factory'


async def test():
    async with sse_client(MCP_URL) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            # Test 1: run_objective with just a goal (LLM generates plan)
            print('=== run_objective: coordenador com LLM ===')
            print('Enviando objetivo: Listar arquivos Python em src/')
            result = await session.call_tool('run_objective', {
                'project_id': 'agent-factory-dev',
                'objective': 'Listar arquivos Python no diretorio src/',
                'context': 'Usar list_directory com pattern *.py',
            })
            for c in result.content:
                data = json.loads(c.text)
                print(f'\nStatus: {data.get("status","?")}')
                print(f'Task ID: {data.get("task_id","?")}')
                print(f'Resumo: {data.get("summary","")}')
                if 'error_type' in data:
                    print(f'ERRO: {data["error_type"]}: {data.get("message","")}')
                    print(f'Hint: {data.get("hint","")}')
                else:
                    out = data.get('output', {})
                    steps = out.get('steps', [])
                    print(f'Total steps: {out.get("total_steps",0)}')
                    print(f'Completed: {out.get("completed",0)}')
                    print(f'Failed: {out.get("failed",0)}')
                    for s in steps:
                        status_icon = '+' if s['status'] == 'ok' else ('-' if s['status'] == 'error' else ' ')
                        result_preview = str(s.get('result',''))[:200] if s['status'] == 'ok' else s.get('error','')
                        print(f'  [{status_icon}] {s["step"]} ({s["agent_id"]}): {result_preview}')
            print()

            # Test 2: run_objective with manual tasks (existing flow)
            print('=== run_objective: coordenador com tasks manuais ===')
            result = await session.call_tool('run_objective', {
                'project_id': 'agent-factory-dev',
                'objective': 'Validar sintaxe do AgentBase',
                'context': '',
            })
            for c in result.content:
                data = json.loads(c.text)
                print(f'Status: {data.get("status","?")}')
                print(f'Task ID: {data.get("task_id","?")}')
                out = data.get('output', {})
                steps = out.get('steps', [])
                print(f'Steps: {len(steps)}')
                for s in steps:
                    print(f'  - {s["step"]} ({s["agent_id"]}): {s["status"]}')

    print('\nTestes concluidos!')


asyncio.run(test())
