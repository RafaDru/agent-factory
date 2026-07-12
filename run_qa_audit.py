import io, sys, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    async with sse_client('http://127.0.0.1:9091/sse') as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            # O QA tem a tarefa de validar a existência do SDK
            result = await session.call_tool('run_objective', {
                'project_id': 'agent-factory-dev',
                'objective': 'Auditar existência do StandardBaseAgent.',
                'context': 'O QA deve tentar validar o import. Se o arquivo não existir, reporte FAILED para o Coordenador.'
            })
            for c in result.content:
                data = json.loads(c.text)
                print(f"Status: {data.get('status','?')}")
                # Imprimir o resumo para ver a resposta do QA
                print(f"Resumo: {data.get('summary','?')}")

asyncio.run(main())
