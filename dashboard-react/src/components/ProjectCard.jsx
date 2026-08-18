import React from 'react';
import {
  EuiPanel,
  EuiHealth,
  EuiFlexGroup,
  EuiFlexItem,
  EuiText,
  EuiBadge,
  EuiIcon,
} from '@elastic/eui';

function ProjectCard({ project, aggregateStatus, runningCount, eventCount, onClick }) {
  const title = project.project_name || project.project_id;
  const team = project.team_name || project.team_id;

  const healthColor = {
    running: 'success',
    completed: 'primary',
    failed: 'danger',
    ready: 'subdued',
  }[aggregateStatus] || 'subdued';

  return (
    <EuiPanel
      paddingSize="m"
      onClick={onClick}
      style={{
        cursor: 'pointer',
        borderLeft: aggregateStatus === 'running' ? '4px solid #22d3ee' : undefined,
        boxShadow: aggregateStatus === 'running' ? '0 0 16px rgba(34,211,238,0.2)' : undefined,
      }}
    >
      <EuiFlexGroup alignItems="center" gutterSize="s">
        <EuiFlexItem grow={false}>
          <EuiText size="l">{project.icon || '📦'}</EuiText>
        </EuiFlexItem>
        <EuiFlexItem>
          <EuiText><h3>{title}</h3></EuiText>
          <EuiText size="s" color="subdued">{team}</EuiText>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiHealth color={healthColor}>{aggregateStatus}</EuiHealth>
        </EuiFlexItem>
      </EuiFlexGroup>
      <EuiFlexGroup gutterSize="s" style={{ marginTop: 12 }}>
        <EuiFlexItem grow={false}>
          <EuiBadge color={runningCount ? 'success' : 'hollow'}>
            {runningCount} running
          </EuiBadge>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiText size="xs" color="subdued">{eventCount} eventos</EuiText>
        </EuiFlexItem>
        <EuiFlexItem grow={false} style={{ marginLeft: 'auto' }}>
          <EuiIcon type="arrowRight" />
        </EuiFlexItem>
      </EuiFlexGroup>
    </EuiPanel>
  );
}

export default ProjectCard;
