import io, sys, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    async with sse_client('http://127.0.0.1:9091/sse') as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            
            # Disparar objetivo
            print("--- Iniciando teste de orquestracao rigida ---")
            result = await session.call_tool('run_objective', {
                'project_id': 'agent-factory-dev',
                'objective': 'Criar README_AUTONOMIA.md e validar conteúdo.',
                'context': 'Desenvolvedor cria o arquivo. QA verifica se o conteúdo não está vazio.'
            })
            
            for c in result.content:
                data = json.loads(c.text)
                print(f"Status: {data.get('status','?')}")
                print(f"Resumo: {data.get('summary','?')}")
                
            # Verificar se o arquivo existe
            import os
            print(f"Arquivo criado: {os.path.exists('README_AUTONOMIA.md')}")

asyncio.run(main())
