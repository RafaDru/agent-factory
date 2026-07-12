import sys, json
sys.path.insert(0, ".")

from src.registry import get_registry
from src.protocols.schema import ProjectConfig

registry = get_registry()
project_id = "solarman-solar-monitor"

# Carregar coordenador + auto-wire subordinates
coord = registry.load_agent(project_id, "coordenador")
for aid in ["negocios", "desenvolvedor", "design"]:
    agent = registry.load_agent(project_id, aid)
    coord.set_subordinates({aid: agent} if not coord.subordinates else {**coord.subordinates, aid: agent})

print("=" * 60)
print("TAREFA 1: Negocios analisa oportunidades de otimizacao")
print("=" * 60)

result = coord.run({
    "task_id": "solar-001",
    "action": "plan_and_execute",
    "goal": "Analisar o sistema de monitoramento solar residencial sob a otica do usuario e identificar oportunidades de melhoria, prevencao de falhas, expansao e geracao de valor",
    "context": """Usina: RAFAELDRUMMONDINFINIT (3.78 kWp, Lagoa Santa MG)
2 microinversores Deye MI, 7 paineis
Python + PostgreSQL + ntfy.sh
Coleta diaria via API SOLARMAN
Notificacao: resumo diario (acima/abaixo da media fixa) + alerta 24h sem geracao""",
    "tasks": [
        {
            "name": "analise-oportunidades",
            "agent_id": "negocios",
            "task": {
                "task_id": "analise-001",
                "action": "analyze",
                "prompt": """Voce e um especialista em energia solar residencial. Analise o sistema de monitoramento e identifique:

1. OPORTUNIDADES DE OTIMIZACAO:
   - O que um usuario residencial realmente precisa saber sobre sua geracao?
   - Quais metricas sao mais importantes (performance ratio, economia R$, payback)?
   - Como detectar queda de performance por inversor/painel antes que vire problema?
   - A media de 18 kWh/dia fixa e adequada ou deveria ser uma media movel sazonal?

2. PREVENCAO DE FALHAS:
   - Como saber se os paineis precisam de limpeza?
   - E possivel detectar sujeira/obstrucao por dados eletricos?
   - Como detectar degradacao precoce de microinversores?
   - Alarmes que fariam diferenca no dia a dia

3. EXPANSAO:
   - Dados para decidir se vale a pena expandir a planta
   - O que analisar: consumo historico vs geracao, horario de pico, sazonalidade
   - Vale bateria? Qual seria o impacto?

4. INTEGRACAO CONCESSIONARIA:
   - E possivel cruzar dados com a operadora de energia?
   - O que seria interessante comparar (medicao bidirecional, credito, tarifa)?
   - Dados abertos de irradiacao para comparar performance real vs esperada

5. RECOMENDACOES:
   - Top 5 melhorias priorizadas por impacto x esforco
   - O que implementar primeiro, segundo e terceiro
   - Roadmap sugerido para evolucao do monitor solar

Seja detalhado e especifico para o contexto brasileiro (Lagoa Santa, MG, clima tropical, tarifa CEMIG).""",
            },
            "depends_on": [],
        },
    ],
})

output = result.output if hasattr(result, "output") else result
print(f"\nStatus: {result.status.value}")
print(f"Steps: {output.get('completed', '?')}/{output.get('total_steps', '?')}")
for step in output.get("steps", []):
    print(f"\n--- Passo: {step['step']} ({step['status']}) ---")
    if "result" in step:
        resp = step["result"]
        if isinstance(resp, dict) and "response" in resp:
            print(resp["response"][:2000])
        else:
            print(str(resp)[:2000])
    if "error" in step:
        print(f"ERRO: {step['error']}")

print("\n" + "=" * 60)
print("CONCLUIDO")
