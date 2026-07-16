import sys; sys.path.insert(0, '.')
from src.agents.coordinator import AgentFactoryCoordinator
from src.agents.factory_dev import AgentFactoryDevAgent
from src.agents.qa import QAAgent
from src.agents.design_factory import DesignAgent
from src.protocols.events import EventNotifier

n = EventNotifier('AFP-Team')
dev = AgentFactoryDevAgent('AFP-Team', n)
qa = QAAgent('AFP-Team', n)
des = DesignAgent('AFP-Team', n)
coord = AgentFactoryCoordinator('AFP-Team', n, agents={'dev': dev, 'qa': qa, 'designer': des})

r = coord.execute({
    'action': 'plan_and_execute',
    'goal': 'Adicionar um botao no dashboard.',
    'context': 'Use refactor_code.'
})

for s in r.get("steps", []):
    print(f"\n--- {s.get('step','?')} ({s.get('agent_id','?')}) ---")
    print(f"  status: {s.get('status','')}  decision: {s.get('decision','')}")
    res = s.get("result", {})
    if isinstance(res, dict):
        for k in ("error","rationale","summary"):
            v = res.get(k,"")
            if v: print(f"  {k}: {str(v)[:500]}")
    elif res:
        print(f"  result: {str(res)[:500]}")
