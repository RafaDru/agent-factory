import sys
sys.path.insert(0, 'src')
from protocols.schema import AgentState
from protocols.events import format_event
from datetime import datetime, timezone

# Teste schema
state = AgentState(agent_id='test', status='idle')
ts = state.timestamp
assert ts.tzinfo is not None, 'Schema timestamp deve ser timezone-aware'
assert ts.tzinfo == timezone.utc, 'Timezone deve ser UTC'
print('Schema timestamp OK:', ts.isoformat())

# Teste events
event = format_event('test', 'test_event', {'key': 'value'})
ts_str = event['timestamp']
# Deve conter +00:00 ou Z
assert '+' in ts_str or ts_str.endswith('Z'), 'Event timestamp deve ter timezone'
print('Event timestamp OK:', ts_str)
print('Todos os testes passaram.')
