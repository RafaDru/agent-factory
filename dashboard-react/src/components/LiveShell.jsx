import React from 'react';
import { EuiFlexGroup, EuiFlexItem, EuiText, EuiBadge, EuiHealth, EuiIcon } from '@elastic/eui';
import { getRunningAgents, getActiveDelegations } from '../services/eventProcessor';

const statusColor = (s) => {
  if (s === 'connected') return 'success';
  if (s === 'error') return 'danger';
  return 'warning';
};

function LiveShell({ agentsState, missionsData, connectionStatus, onNavigate }) {
  const running = getRunningAgents(agentsState);
  const chains = getActiveDelegations(missionsData).slice(0, 4);

  return (
    <div
      style={{
        position: 'sticky',
        top: 56,
        zIndex: 1000,
        background: 'var(--euiColorEmptyShade, #1a1a2e)',
        borderBottom: '1px solid var(--euiColorLightShade, #333)',
        padding: '8px 16px',
        margin: '-24px -24px 16px',
      }}
    >
      <EuiFlexGroup alignItems="center" gutterSize="m" responsive={false} wrap>
        <EuiFlexItem grow={false}>
          <EuiHealth color={statusColor(connectionStatus)}>
            {connectionStatus === 'connected' ? 'Ao vivo' : connectionStatus}
          </EuiHealth>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiBadge color={running.length ? 'success' : 'hollow'}>
            {running.length} agente{running.length !== 1 ? 's' : ''} running
          </EuiBadge>
        </EuiFlexItem>
        <EuiFlexItem>
          {chains.length === 0 ? (
            <EuiText size="s" color="subdued">Nenhuma delegação ativa</EuiText>
          ) : (
            <EuiFlexGroup gutterSize="s" responsive={false} wrap alignItems="center">
              {chains.map((c, i) => (
                <EuiFlexItem grow={false} key={`${c.missionId}-${i}`}>
                  <EuiText
                    size="s"
                    style={{ cursor: 'pointer' }}
                    onClick={() => onNavigate?.('project', c.projectId, null, 'mission-control')}
                  >
                    <strong>{c.projectId}</strong>
                    {' '}
                    {c.from}
                    <EuiIcon type="sortRight" size="s" style={{ margin: '0 4px' }} />
                    {c.to}
                    <EuiText size="xs" color="subdued" style={{ marginLeft: 6 }}>
                      {String(c.task).slice(0, 40)}
                    </EuiText>
                  </EuiText>
                </EuiFlexItem>
              ))}
            </EuiFlexGroup>
          )}
        </EuiFlexItem>
      </EuiFlexGroup>
    </div>
  );
}

export default LiveShell;
