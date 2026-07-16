import sys, time
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.as_posix())
print("Starting...", flush=True)

from src.agents.coordinator import AgentFactoryCoordinator
from src.agents.factory_dev import AgentFactoryDevAgent
from src.agents.qa import QAAgent
from src.agents.design_factory import DesignAgent
from src.protocols.events import EventNotifier
from src.llm import get_provider

print("Loading provider...", flush=True)
p = get_provider("opencode_zen")
print(f"Provider: {type(p).__name__}", flush=True)

print("Testing small chat...", flush=True)
t0 = time.time()
r = p.chat([{"role":"user","content":"Say hi in 3 words."}], max_tokens=20)
print(f"Chat OK in {time.time()-t0:.1f}s: {r.content[:100]}", flush=True)
