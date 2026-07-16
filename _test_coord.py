import sys, time; sys.path.insert(0, '.')
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

print('Testing coordinator plan...', flush=True)
t0 = time.time()
r = coord.execute({
    'action': 'plan_and_execute',
    'goal': 'Adicionar um botao no dashboard.',
    'context': 'Use refactor_code.'
})
print(f'Done in {time.time()-t0:.0f}s', flush=True)
print(f'Status: {r["status"]}', flush=True)
for s in r.get("steps", []):
    print(f'  {s.get("step","?")}: {s.get("status","?")}', flush=True)
