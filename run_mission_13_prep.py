"""
Missao #13-prep: Coordenador analisar e categorizar melhorias do dashboard
=======================================================================
Testar se o coordenador, apos as missoes #12 e #15, consegue analisar
holisticamente um conjunto de temas, classificar (bug vs melhoria),
priorizar e sugerir plano de execucao.
Deve consultar negocios e designer para fundamentar a analise.
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.registry import get_registry
from src.mcp.server import _wire_subordinates

project_id = "AFP-Team"
registry = get_registry()

agent = registry.load_agent(project_id, "coordenador")
_wire_subordinates(registry, project_id, agent)

task = {
    "task_id": "missao-analise-melhorias-13",
    "action": "plan_and_execute",
    "goal": "Analisar os pontos abaixo, classificar cada um como bug ou melhoria, priorizar por ordem de impacto no usuario, e sugerir plano de implementacao. CONSULTAR negocios e designer durante a analise.",
    "context": (
        "## Pontos a Analisar\n\n"
        "### P1 - Interaction Flow com 'idas e vindas'\n"
        "Atual: cada task aparece como running (com glow) e depois completed/failed.\n"
        "Problema: like fica piscando running mesmo apos terminar, dando sensacao falsa de execucao.\n"
        "Melhoria desejada: agrupar por task 'mae' da conversa, mostrar apenas o estado atual.\n"
        "Interaction Flow deve mostrar como esta ocorrendo a operacao, nao ser um log historico.\n\n"
        "### P2 - Cards de agentes sem atualizacao ao vivo\n"
        "Bug: os agent cards acima do interaction flow nao refletem em tempo real o status.\n"
        "O SSE entrega eventos mas os cards nao sao atualizados.\n\n"
        "### P3 - Lista de modelos limitada\n"
        "Melhoria: mostra apenas Groq/Ollama/Opencode. Outros providers (OpenAI, Anthropic, etc)\n"
        "nao aparecem mesmo se configurados.\n\n"
        "### P4 - Primeira tela (localhost:8080) sem live stream\n"
        "Melhoria: a pagina de listagem de projetos nao mostra status ao vivo dos agentes.\n"
        "Fica piscando '0 agents running' mesmo quando ha execucao.\n\n"
        "### P5 - Navegacao por URL (/project=xxx)\n"
        "Bug/UX: refresh no browser volta para primeira tela. Deveria manter o projeto selecionado\n"
        "via query param na URL.\n\n"
        "## O que o coordenador deve fazer\n"
        "1. CONSULTAR negocios: qual o impacto de cada ponto para o usuario?\n"
        "2. CONSULTAR designer: qual a melhor abordagem de UX para P1 (interaction flow)\n"
        "   e P4 (pagina inicial com live stream)?\n"
        "3. Classificar cada ponto como: bug, melhoria, ou feature\n"
        "4. Priorizar: alta (bloqueante), media, baixa\n"
        "5. Sugerir ordem de execucao (quem implementa o que)\n\n"
        "## Formato de Saida Esperado\n"
        "Relatorio estruturado com:\n"
        "- Classificacao de cada ponto (bug/melhoria/feature)\n"
        "- Prioridade (alta/media/baixa)\n"
        "- Justificativa\n"
        "- Ordem de execucao recomendada\n"
        "- Agente responsavel por cada acao"
    ),
}

print("Executando missao de analise...")
start = time.time()
result = agent.run(task)
elapsed = time.time() - start

output = result.output if hasattr(result, "output") else result
print("\n=== RESULTADO DA ANALISE ===")
print("Tempo: %.1fs" % elapsed)
print("Status:", result.status.value)

if isinstance(output, dict):
    steps = output.get("steps", [])
    print("Steps: %d, Completed: %d, Failed: %d" % (
        output.get("total_steps", "?"),
        output.get("completed", "?"),
        output.get("failed", "?"),
    ))
    for s in steps:
        print("\n  --- %s (%s) [%s/%s] ---" % (
            s.get("step", "?"), s.get("agent_id", "?"),
            s.get("status", "?"), s.get("decision", "?"),
        ))
        rationale = s.get("rationale", s.get("result", ""))
        if isinstance(rationale, str) and len(rationale) > 50:
            print("  %s..." % rationale[:300].replace("\n", "\n  "))
    # Extrair relatorio consolidado
    for s in steps:
        if s.get("step", "").endswith("relatorio") or "relatorio" in s.get("step", "").lower():
            r = s.get("result", s.get("rationale", ""))
            if isinstance(r, str) and len(r) > 100:
                print("\n\n=== RELATORIO CONSOLIDADO ===")
                print(r[:2000])
                break

print("\nDone!")
