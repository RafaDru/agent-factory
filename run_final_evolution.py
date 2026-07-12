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
                'project_id': 'agent-factory-dev',
                'objective': 'Implementar collapsível nos projetos, Dark/Light Mode e exibir modelo LLM no dashboard.',
                'context': 'DesignAgent: planejar UI. DesenvolvedorAgent: implementar. QA: validar.'
            })
            for c in result.content:
                data = json.loads(c.text)
                print(f"Status: {data.get('status','?')}")
                print(f"Resumo: {data.get('summary','?')}")

asyncio.run(main())
