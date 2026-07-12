"""
Agent Factory — MCP Smoke Test
================================
Testa o servidor MCP via SSE, exercitando todas as tools e resources.

Uso:
    python test_mcp_smoke.py [--url http://127.0.0.1:8081/sse]
"""

import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import asyncio
import argparse
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession


async def smoke_test(url: str):
    def parse_content(result):
        """Accumula TextContent items em uma lista de dicts."""
        items = []
        for c in result.content:
            obj = json.loads(c.text)
            if isinstance(obj, list):
                items.extend(obj)
            else:
                items.append(obj)
        return items

    print(f"[MCP] Conectando ao servidor: {url}")
    async with sse_client(url) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            print("[MCP] Conectado e inicializado\n")

            # List tools
            tools = await session.list_tools()
            print(f"[TOOLS] {len(tools.tools)} disponiveis:")
            for t in tools.tools:
                params = {k: v.get("description", "") for k, v in t.inputSchema.get("properties", {}).items()}
                print(f"   - {t.name}: {params}")
            print()

            # List resource templates
            resources = await session.list_resource_templates()
            print(f"[RESOURCES] {len(resources.resourceTemplates)} templates:")
            for r in resources.resourceTemplates:
                print(f"   - {r.uriTemplate}")
            print()

            # Tool: list_projects
            print("[TEST] list_projects...", end=" ")
            result = await session.call_tool("list_projects", {})
            if result.content:
                data = parse_content(result)
                print(f"OK ({len(data)} projetos)")
                for p in data:
                    print(f"   - {p['project_id']}: {p['name']} ({len(p['agents'])} agentes)")
            else:
                print(f"FALHA (isError={result.isError})")
            print()

            # Tool: list_agents (agent-factory-dev)
            print("[TEST] list_agents(agent-factory-dev)...", end=" ")
            result = await session.call_tool("list_agents", {"project_id": "agent-factory-dev"})
            if result.content:
                data = parse_content(result)
                print(f"OK ({len(data)} agentes)")
                for a in data:
                    actions = a.get("capabilities", {}).get("actions", {})
                    print(f"   - {a['agent_id']}: {list(actions.keys())}")
            else:
                print(f"FALHA (isError={result.isError})")
            print()

            # Tool: list_agents (pta)
            print("[TEST] list_agents(pta)...", end=" ")
            result = await session.call_tool("list_agents", {"project_id": "pta"})
            if result.content:
                data = parse_content(result)
                print(f"OK ({len(data)} agentes)")
                for a in data:
                    if "error" not in a:
                        actions = a.get("capabilities", {}).get("actions", {})
                        print(f"   - {a['agent_id']}: {list(actions.keys())}")
                    else:
                        print(f"   - {a['agent_id']}: ERRO: {a['error']}")
            else:
                print(f"FALHA (isError={result.isError})")
            print()

            # Tool: read_events
            print("[TEST] read_events(agent-factory-dev, limit=5)...", end=" ")
            result = await session.call_tool("read_events", {"project_id": "agent-factory-dev", "limit": 5})
            if result.content:
                data = parse_content(result)
                print(f"OK ({len(data)} eventos)")
                for e in data[:3]:
                    print(f"   - {e.get('agent_id','?')}: {e.get('message','?')[:60]}")
            else:
                print(f"FALHA (isError={result.isError})")
            print()

            # Tool: get_project_status
            print("[TEST] get_project_status(agent-factory-dev)...", end=" ")
            result = await session.call_tool("get_project_status", {"project_id": "agent-factory-dev"})
            if result.content:
                data = parse_content(result)
                item = data[0] if data else {}
                print(f"OK - {item.get('total_events',0)} eventos, {item.get('completed_events',0)} completos")
            else:
                print(f"FALHA (isError={result.isError})")
            print()

            # Resource: events
            print("[TEST] resource(afp://agent-factory-dev/events)...", end=" ")
            res = await session.read_resource("afp://agent-factory-dev/events")
            if res.contents:
                print(f"OK ({len(res.contents[0].text)} bytes)")
            else:
                print("FALHA - vazio")
            print()

            # Resource: context
            print("[TEST] resource(afp://agent-factory-dev/coordenador/context)...", end=" ")
            res = await session.read_resource("afp://agent-factory-dev/coordenador/context")
            if res.contents:
                text = res.contents[0].text
                lines = text.strip().split("\n") if hasattr(text, 'split') else []
                print(f"OK ({len(lines)} linhas)")
                for l in lines[:3]:
                    print(f"   {l}")
            else:
                print("FALHA - vazio")
            print()

            # Resource: capabilities
            print("[TEST] resource(afp://agent-factory-dev/agent-factory-dev/capabilities)...", end=" ")
            res = await session.read_resource("afp://agent-factory-dev/agent-factory-dev/capabilities")
            if res.contents:
                data = json.loads(res.contents[0].text) if isinstance(res.contents[0].text, str) else {}
                actions = data.get("actions", {})
                print(f"OK ({len(actions)} acoes): {list(actions.keys())}")
            else:
                print("FALHA - vazio")
            print()

    print("[MCP] Smoke test concluido com sucesso!")


def main():
    parser = argparse.ArgumentParser(description="MCP Smoke Test")
    parser.add_argument("--url", default="http://127.0.0.1:8081/sse",
                        help="MCP server SSE URL")
    args = parser.parse_args()
    asyncio.run(smoke_test(args.url))


if __name__ == "__main__":
    main()
