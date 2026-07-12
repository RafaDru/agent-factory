"""
Agent Factory — MCP run_agent + run_objective test
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

            # run_agent: list_directory via agent-factory-dev
            print('=== run_agent: agent-factory-dev list_directory ===')
            result = await session.call_tool('run_agent', {
                'project_id': 'agent-factory-dev',
                'agent_id': 'agent-factory-dev',
                'task': {
                    'task_id': 'test-mcp-1',
                    'action': 'list_directory',
                    'path': fr'{ROOT}\src',
                    'pattern': '*.py',
                }
            })
            for c in result.content:
                data = json.loads(c.text)
                if 'error_type' in data:
                    print(f'  ERRO: {data["error_type"]}: {data.get("message","")}')
                elif data.get('status') == 'completed':
                    output = data.get('output', {})
                    files = output.get('files', output.get('result', []))
                    if isinstance(files, list):
                        print(f'  OK - {len(files)} arquivos encontrados')
                        for f in files[:8]:
                            print(f'    - {f}')
                        if len(files) > 8:
                            print(f'    ... e mais {len(files) - 8}')
                    else:
                        print(f'  OK - saida: {str(files)[:120]}')
                else:
                    print(f'  Resposta: {json.dumps(data, indent=2)[:300]}')
            print()

            # run_agent: validate_python_syntax via qa
            print('=== run_agent: qa validate_python_syntax ===')
            result = await session.call_tool('run_agent', {
                'project_id': 'agent-factory-dev',
                'agent_id': 'qa',
                'task': {
                    'task_id': 'test-mcp-2',
                    'action': 'validate_python_syntax',
                    'file_path': fr'{ROOT}\src\agents\base.py',
                }
            })
            for c in result.content:
                data = json.loads(c.text)
                if 'error_type' in data:
                    print(f'  ERRO: {data["error_type"]}: {data.get("message","")}')
                else:
                    print(f'  Status: {data.get("status","?")}')
                    out = data.get('output', {})
                    if 'valid' in out:
                        print(f'  Valido: {out["valid"]}')
                    print(f'  Resumo: {data.get("summary","")}')
            print()

            # run_objective: high-level goal for coordinator
            print('=== run_objective: coordenador ===')
            result = await session.call_tool('run_objective', {
                'project_id': 'agent-factory-dev',
                'objective': 'Listar arquivos Python em src/ e depois rodar pytest em tests/',
                'context': 'Usar list_directory com pattern *.py e run_tests com args -q',
            })
            for c in result.content:
                data = json.loads(c.text)
                if 'error_type' in data:
                    print(f'  ERRO: {data["error_type"]}: {data.get("message","")}')
                else:
                    print(f'  Status: {data.get("status","?")}')
                    print(f'  Task ID: {data.get("task_id","?")}')
                    out = data.get('output', {})
                    plan = out.get('plan', out.get('tasks', []))
                    if plan:
                        print(f'  Tarefas no plano: {len(plan)}')
                        for t in plan:
                            print(f'    - {t.get("name","?")} -> {t.get("agent_id","?")}')
                    print(f'  Resumo: {data.get("summary","")}')
            print()

    # run_objective: better output
    print('=== run_objective: coordenador (com output) ===')
    result = await session.call_tool('run_objective', {
        'project_id': 'agent-factory-dev',
        'objective': 'Listar arquivos Python em src/ e rodar pytest basico',
        'context': 'Usar list_directory com pattern *.py e run_tests com args -q --tb=no',
    })
    for c in result.content:
        data = json.loads(c.text)
        print(f'  Status: {data.get("status","?")}')
        print(f'  Task ID: {data.get("task_id","?")}')
        print(f'  Resumo: {data.get("summary","")}')
        out = data.get('output', {})
        if 'plan' in out:
            print(f'  Tarefas no plano: {len(out["plan"])}')
            for t in out['plan']:
                print(f'    - {t.get("name","?")} -> {t.get("agent_id","?")}')
        elif 'tasks' in out:
            print(f'  Tarefas: {len(out["tasks"])}')

    print()
    print('Testes concluidos!')


asyncio.run(test())
