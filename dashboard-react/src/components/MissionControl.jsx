import React from 'react';
import {
  EuiPanel,
  EuiTitle,
  EuiText,
  EuiSpacer,
  EuiFlexGroup,
  EuiFlexItem,
  EuiHealth,
  EuiBadge,
  EuiIcon,
  EuiEmptyPrompt,
} from '@elastic/eui';

function DelegationGraph({ delegations }) {
  if (!delegations?.length) return null;
  const recent = delegations.slice(-6);
  return (
    <EuiPanel paddingSize="m" hasShadow={false} color="subdued">
      <EuiText size="s"><strong>Quem acionou quem</strong></EuiText>
      <EuiSpacer size="s" />
      <EuiFlexGroup direction="column" gutterSize="s">
        {recent.map((d) => (
          <EuiFlexItem key={d.id}>
            <EuiFlexGroup alignItems="center" gutterSize="s" responsive={false}>
              <EuiFlexItem grow={false}>
                <EuiBadge>{d.from}</EuiBadge>
              </EuiFlexItem>
              <EuiFlexItem grow={false}>
                <EuiIcon type="sortRight" />
              </EuiFlexItem>
              <EuiFlexItem grow={false}>
                <EuiBadge color="primary">{d.to}</EuiBadge>
              </EuiFlexItem>
              <EuiFlexItem>
                <EuiText size="xs" color="subdued">{d.task}</EuiText>
              </EuiFlexItem>
            </EuiFlexGroup>
          </EuiFlexItem>
        ))}
      </EuiFlexGroup>
    </EuiPanel>
  );
}

function MissionCard({ mission }) {
  const tasks = Object.values(mission.tasks || {});
  return (
    <EuiPanel paddingSize="m" style={{ marginBottom: 16 }}>
      <EuiFlexGroup alignItems="center">
        <EuiFlexItem>
          <EuiTitle size="xs"><h3>{mission.id}</h3></EuiTitle>
          {mission.objective && (
            <EuiText size="s" color="subdued">{mission.objective}</EuiText>
          )}
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiHealth
            color={
              mission.status === 'running' ? 'success'
                : mission.status === 'failed' ? 'danger'
                  : mission.status === 'partial' ? 'warning'
                    : mission.status === 'completed' ? 'primary' : 'subdued'
            }
          >
            {mission.status}
          </EuiHealth>
        </EuiFlexItem>
      </EuiFlexGroup>
      <EuiSpacer size="m" />
      <DelegationGraph delegations={mission.delegations} />
      {tasks.length > 0 && (
        <>
          <EuiSpacer size="m" />
          <EuiText size="s"><strong>Tarefas</strong></EuiText>
          <EuiSpacer size="s" />
          {tasks.map((t) => (
            <EuiFlexGroup key={t.id} alignItems="center" gutterSize="s" style={{ marginBottom: 8 }}>
              <EuiFlexItem grow={false}>
                <EuiBadge color={t.status === 'running' ? 'success' : t.status === 'failed' ? 'danger' : 'hollow'}>
                  {t.status}
                </EuiBadge>
              </EuiFlexItem>
              <EuiFlexItem grow={false}>
                <EuiText size="s">{t.agent}</EuiText>
              </EuiFlexItem>
              <EuiFlexItem>
                <EuiText size="xs" color="subdued">{t.name}</EuiText>
              </EuiFlexItem>
            </EuiFlexGroup>
          ))}
        </>
      )}
    </EuiPanel>
  );
}

function MissionControl({ missionsData, projectId = null, global = false }) {
  const missions = Object.values(missionsData || {})
    .filter((m) => !projectId || m.projectId === projectId)
    .sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));

  const active = missions.filter((m) => m.status === 'running');
  const recent = missions.filter((m) => m.status !== 'running').slice(0, 5);

  if (missions.length === 0) {
    return (
      <EuiEmptyPrompt
        iconType="visGauge"
        title={<h3>Sem missões ainda</h3>}
        body={<p>Quando o coordenador receber um objetivo, as delegações aparecerão aqui em tempo real.</p>}
      />
    );
  }

  return (
    <>
      <EuiTitle size="s">
        <h2>{global ? 'Mission Control — Global' : 'Mission Control'}</h2>
      </EuiTitle>
      <EuiSpacer size="m" />
      {active.length > 0 && (
        <>
          <EuiText size="s"><strong>Em andamento</strong></EuiText>
          <EuiSpacer size="s" />
          {active.map((m) => <MissionCard key={m.id} mission={m} />)}
        </>
      )}
      {recent.length > 0 && (
        <>
          <EuiSpacer size="l" />
          <EuiText size="s" color="subdued"><strong>Recentes</strong></EuiText>
          <EuiSpacer size="s" />
          {recent.map((m) => <MissionCard key={m.id} mission={m} />)}
        </>
      )}
    </>
  );
}

export default MissionControl;
