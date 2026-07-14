import React from 'react';
import {
  EuiSelect,
  EuiFormRow,
  EuiFlexGroup,
  EuiFlexItem,
  EuiText,
  EuiBadge,
} from '@elastic/eui';

const PROVIDER_OPTIONS = [
  { value: 'auto', text: 'Auto' },
  { value: 'local_multi', text: 'Local Multi' },
  { value: 'cloud', text: 'Cloud' },
];

const ProviderSelector = ({ agents, onProviderChange }) => {
  if (!agents || agents.length === 0) {
    return <EuiText color="subdued">Nenhum agente disponível.</EuiText>;
  }

  return (
    <EuiFlexGroup direction="column" gutterSize="m">
      {agents.map((agent) => (
        <EuiFlexItem key={agent.agent_id}>
          <EuiFlexGroup alignItems="center" gutterSize="m">
            <EuiFlexItem grow={false}>
              <EuiBadge>{agent.agent_id}</EuiBadge>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiText size="s" color="subdued">
                {agent.model || '-'}
              </EuiText>
            </EuiFlexItem>
            <EuiFlexItem grow={false} style={{ minWidth: 160 }}>
              <EuiFormRow label="" display="column" fullWidth>
                <EuiSelect
                  options={PROVIDER_OPTIONS}
                  value={agent.current_provider || 'auto'}
                  onChange={(e) => onProviderChange(agent.agent_id, e.target.value)}
                  compressed
                />
              </EuiFormRow>
            </EuiFlexItem>
          </EuiFlexGroup>
        </EuiFlexItem>
      ))}
    </EuiFlexGroup>
  );
};

export default ProviderSelector;
