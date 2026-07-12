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
                'objective': 'Implementar src/tray_manager.py com pystray/plyer e registrar startup.',
                'context': 'Agente desenvolvedor deve escrever o arquivo. Após, Design e QA validam.'
            })
            for c in result.content:
                data = json.loads(c.text)
                print(f"Status: {data.get('status','?')}")
                steps = data.get('output', {}).get('steps', [])
                for s in steps:
                    print(f"  [{s.get('agent_id','?')}] {s.get('step')} -> {s.get('status')}")

asyncio.run(main())
