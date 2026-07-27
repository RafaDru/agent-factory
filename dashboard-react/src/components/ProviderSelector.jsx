import React, { useState } from 'react';
import {
  EuiSelect,
  EuiFormRow,
  EuiFlexGroup,
  EuiFlexItem,
  EuiText,
  EuiBadge,
  EuiTabs,
  EuiTab,
  EuiButtonIcon,
  EuiSpacer,
  EuiFieldText,
  EuiButton,
} from '@elastic/eui';

const PROVIDER_OPTIONS = [
  { value: 'auto', text: 'Auto' },
  { value: 'local_multi', text: 'Local Multi' },
  { value: 'cloud', text: 'Cloud' },
];

const TABS = [
  { id: 'providers', label: 'Provedores' },
  { id: 'api-keys', label: 'API Keys' },
  { id: 'ollama', label: 'Ollama' },
];

const ProviderSelector = ({ agents, onProviderChange, onOpenLlmModal }) => {
  const [activeTab, setActiveTab] = useState('providers');

  if (!agents || agents.length === 0) {
    return <EuiText color="subdued">Nenhum agente disponível.</EuiText>;
  }

  const renderProviders = () => (
    <EuiFlexGroup direction="column" gutterSize="m">
      {agents.map((agent) => (
        <EuiFlexItem key={agent.agent_id}>
          <EuiFlexGroup alignItems="center" gutterSize="m">
            <EuiFlexItem grow={false}>
              <EuiBadge>{agent.agent_id}</EuiBadge>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiText size="s" color="subdued">{agent.model || '-'}</EuiText>
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
            <EuiFlexItem grow={false}>
              <EuiButtonIcon
                iconType="inspect"
                onClick={() => onOpenLlmModal && onOpenLlmModal(agent)}
                aria-label="Detalhes LLM"
              />
            </EuiFlexItem>
          </EuiFlexGroup>
        </EuiFlexItem>
      ))}
    </EuiFlexGroup>
  );

  const renderApiKeys = () => (
    <EuiFlexGroup direction="column" gutterSize="m">
      <EuiFlexItem>
        <EuiFormRow label="Groq API Key" fullWidth>
          <EuiFieldText placeholder="gsk_..." type="password" />
        </EuiFormRow>
      </EuiFlexItem>
      <EuiFlexItem>
        <EuiFormRow label="OpenAI API Key" fullWidth>
          <EuiFieldText placeholder="sk-..." type="password" />
        </EuiFormRow>
      </EuiFlexItem>
      <EuiFlexItem>
        <EuiButton size="s">Salvar API Keys</EuiButton>
      </EuiFlexItem>
    </EuiFlexGroup>
  );

  const renderOllama = () => (
    <EuiFlexGroup direction="column" gutterSize="m">
      <EuiFlexItem>
        <EuiFormRow label="Ollama Endpoint" fullWidth>
          <EuiFieldText placeholder="http://localhost:11434" defaultValue="http://localhost:11434" />
        </EuiFormRow>
      </EuiFlexItem>
      <EuiFlexItem>
        <EuiFormRow label="Modelo padrão" fullWidth>
          <EuiFieldText placeholder="deepseek-r1:8b" />
        </EuiFormRow>
      </EuiFlexItem>
      <EuiFlexItem>
        <EuiButton size="s">Testar Conexão</EuiButton>
      </EuiFlexItem>
    </EuiFlexGroup>
  );

  return (
    <>
      <EuiTabs>
        {TABS.map(tab => (
          <EuiTab key={tab.id} isSelected={activeTab === tab.id} onClick={() => setActiveTab(tab.id)}>
            {tab.label}
          </EuiTab>
        ))}
      </EuiTabs>
      <EuiSpacer />
      {activeTab === 'providers' && renderProviders()}
      {activeTab === 'api-keys' && renderApiKeys()}
      {activeTab === 'ollama' && renderOllama()}
    </>
  );
};

export default ProviderSelector;
