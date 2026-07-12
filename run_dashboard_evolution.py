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
                'objective': 'Implementar collapsível, tempo real, modelo LLM no dashboard e corrigir o status "preparando" travado.',
                'context': '1. Design: prototipar UI. 2. Desenvolvedor: aplicar UI e debugar EventNotifier.'
            })
            for c in result.content:
                print(c.text)
asyncio.run(main())
