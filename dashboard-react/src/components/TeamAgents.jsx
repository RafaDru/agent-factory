import React, { useEffect, useState } from 'react';
import {
  EuiPanel,
  EuiFlexGroup,
  EuiFlexItem,
  EuiText,
  EuiHealth,
  EuiButton,
  EuiSpacer,
  EuiBadge,
} from '@elastic/eui';
import { agentKey } from '../services/eventProcessor';

const borderColor = {
  running: '#22d3ee',
  completed: '#22c55e',
  failed: '#ef4444',
  ready: 'transparent',
};

function formatElapsed(timerStart) {
  if (!timerStart) return null;
  const sec = Math.floor((Date.now() - timerStart) / 1000);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function AgentCard({ projectId, agent, agentState, onSelectLlm }) {
  const status = agentState?.status || 'ready';
  const [elapsed, setElapsed] = useState(null);

  useEffect(() => {
    if (status !== 'running' || !agentState?.timerStart) {
      setElapsed(null);
      return undefined;
    }
    const tick = () => setElapsed(formatElapsed(agentState.timerStart));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [status, agentState?.timerStart]);

  return (
    <EuiPanel
      paddingSize="m"
      style={{
        borderLeft: `4px solid ${borderColor[status] || borderColor.ready}`,
        boxShadow: status === 'running' ? '0 0 12px rgba(34,211,238,0.25)' : undefined,
      }}
    >
      <EuiFlexGroup alignItems="center" gutterSize="s">
        <EuiFlexItem grow={false}>
          <EuiText><h4>{agent.emoji || '🤖'} {agent.agent_name || agent.agent_id}</h4></EuiText>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiHealth color={status === 'running' ? 'success' : status === 'failed' ? 'danger' : 'subdued'}>
            {status}
          </EuiHealth>
        </EuiFlexItem>
        {status === 'running' && elapsed && (
          <EuiFlexItem grow={false}>
            <EuiBadge>{elapsed}</EuiBadge>
          </EuiFlexItem>
        )}
        <EuiFlexItem grow={false}>
          <EuiButton size="s" onClick={() => onSelectLlm(agent)}>
            LLM
          </EuiButton>
        </EuiFlexItem>
      </EuiFlexGroup>
      <EuiSpacer size="s" />
      <EuiText size="s" color="subdued">{agent.description || agent.role || ''}</EuiText>
      {agentState?.subStatus && (
        <EuiText size="xs" style={{ marginTop: 8 }}>{agentState.subStatus}</EuiText>
      )}
      {agentState?.task && (
        <EuiText size="xs" color="subdued">Task: {agentState.task}</EuiText>
      )}
    </EuiPanel>
  );
}

function TeamAgents({ project, agentsState, onSelectLlm }) {
  const agents = project.agents || [];
  const projectId = project.project_id;

  if (agents.length === 0) {
    return <EuiText color="subdued">Nenhum agente registrado neste projeto.</EuiText>;
  }

  const coord = agents.filter((a) => (a.role || '').includes('coorden'));
  const workers = agents.filter((a) => !(a.role || '').includes('coorden'));

  const renderList = (list, title) => (
    list.length > 0 && (
      <>
        <EuiText><h4>{title}</h4></EuiText>
        <EuiSpacer size="s" />
        <EuiFlexGroup direction="column" gutterSize="m">
          {list.map((agent) => (
            <EuiFlexItem key={agent.agent_id}>
              <AgentCard
                projectId={projectId}
                agent={agent}
                agentState={agentsState[agentKey(projectId, agent.agent_id)]}
                onSelectLlm={onSelectLlm}
              />
            </EuiFlexItem>
          ))}
        </EuiFlexGroup>
        <EuiSpacer size="m" />
      </>
    )
  );

  return (
    <>
      {renderList(coord, 'Coordenação')}
      {renderList(workers, 'Equipe')}
    </>
  );
}

export default TeamAgents;
export { AgentCard };
