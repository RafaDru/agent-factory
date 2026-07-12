import io, sys, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    async with sse_client('http://127.0.0.1:9091/sse') as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            # Test worker directly
            print("=== run_agent: desenvolvedor write_file ===")
            result = await session.call_tool('run_agent', {
                'project_id': 'agent-factory-dev',
                'agent_id': 'desenvolvedor',
                'task': {
                    'task_id': 'direct-test',
                    'title': 'Teste direto',
                    'action': 'write_file',
                    'file_path': 'TESTE_MCP_DIRETO.txt',
                    'content': 'Criado via MCP run_agent'
                }
            })
            for c in result.content:
                data = json.loads(c.text)
                print(json.dumps(data, indent=2))
            
            # Check if file was created
            import os
            path = os.path.join(os.getcwd(), 'TESTE_MCP_DIRETO.txt')
            print(f"\nArquivo existe: {os.path.exists(path)}")
            if os.path.exists(path):
                with open(path) as f:
                    print(f"Conteudo: '{f.read()}'")

asyncio.run(main())
