import React, { useState, useEffect, useCallback } from 'react';
import {
  EuiPanel,
  EuiHeader,
  EuiHeaderSection,
  EuiHeaderSectionItem,
  EuiHeaderLogo,
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiLoadingSpinner,
  EuiEmptyPrompt,
  EuiText,
  EuiTitle,
  EuiSpacer,
  EuiButtonIcon,
  EuiTabs,
  EuiTab,
  EuiModal,
  EuiModalHeader,
  EuiModalHeaderTitle,
  EuiModalBody,
  EuiModalFooter,
  EuiButton,
  EuiIcon,
  EuiHealth,
  EuiBadge,
} from '@elastic/eui';
import EventTable from './components/EventTable';
import ProviderSelector from './components/ProviderSelector';
import Breadcrumb from './components/Breadcrumb';
import { fetchProjects as apiFetchProjects, fetchEvents } from './services/api';

const GROUP_LABELS = { coordenador: 'Coordenador', upstream: 'Upstream', downstream: 'Downstream' };
const getGroupFor = (projectId) => {
  if (projectId === 'AFP-Team') return 'coordenador';
  if (['pta', 'cr10se'].includes(projectId)) return 'upstream';
  return 'downstream';
};

function App() {
  const [projects, setProjects] = useState([]);
  const [events, setEvents] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [view, setView] = useState('home');
  const [selectedProject, setSelectedProject] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [activeTab, setActiveTab] = useState('events');
  const [expandedGroups, setExpandedGroups] = useState({});
  const [llmModalAgent, setLlmModalAgent] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const projectIds = await apiFetchProjects();
      setProjects(projectIds);
      const allEvents = [];
      const allProviders = [];
      for (const pid of projectIds) {
        const data = await fetchEvents(pid, 50);
        if (data && data.events) allEvents.push(...data.events);
        if (data && data.agent_models) {
          for (const [agentId, model] of Object.entries(data.agent_models)) {
            allProviders.push({ agent_id: agentId, current_provider: 'auto', model });
          }
        }
      }
      allEvents.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      setEvents(allEvents);
      if (allProviders.length > 0) setProviders(allProviders);
      setLoading(false);
    } catch (err) {
      setError(err);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const intervalId = setInterval(loadData, 3000);
    return () => clearInterval(intervalId);
  }, [loadData]);

  const handleNavigate = (newView, projectId, agentId) => {
    setView(newView);
    setSelectedProject(projectId);
    setSelectedAgent(agentId);
  };

  const handleProviderChange = async (agentId, newProvider) => {
    try {
      const { updateAgentProvider } = await import('./services/api');
      await updateAgentProvider(agentId, newProvider);
      setProviders(prev => prev.map(p => p.agent_id === agentId ? { ...p, current_provider: newProvider } : p));
    } catch (err) {
      console.error('Failed to update provider', err);
    }
  };

  const toggleGroup = (groupKey) => {
    setExpandedGroups(prev => ({ ...prev, [groupKey]: !prev[groupKey] }));
  };

  const getProjectStatus = (projectId) => {
    const projectEvents = events.filter(e => e.project_id === projectId);
    const latest = projectEvents[0];
    return latest ? latest.status : 'idle';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'success';
      case 'completed': return 'primary';
      case 'failed': return 'danger';
      default: return 'subdued';
    }
  };

  const filteredEvents = selectedProject
    ? events.filter((e) => e.project_id === selectedProject)
    : events;

  const renderProjectCard = (projectId) => {
    const status = getProjectStatus(projectId);
    const eventCount = events.filter(e => e.project_id === projectId).length;
    return (
      <EuiFlexItem key={projectId}>
        <EuiPanel
          paddingSize="m"
          onClick={() => handleNavigate('project', projectId, null)}
          style={{ cursor: 'pointer' }}
        >
          <EuiFlexGroup alignItems="center" gutterSize="s">
            <EuiFlexItem grow={false}>
              <EuiHealth color={getStatusColor(status)}>{status}</EuiHealth>
            </EuiFlexItem>
            <EuiFlexItem>
              <EuiText><h3>{projectId}</h3></EuiText>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiText size="s" color="subdued">{eventCount} eventos</EuiText>
            </EuiFlexItem>
          </EuiFlexGroup>
        </EuiPanel>
      </EuiFlexItem>
    );
  };

  const renderGroup = (groupKey, label) => {
    const groupProjects = projects.filter(p => getGroupFor(p) === groupKey);
    if (groupProjects.length === 0) return null;
    const isExpanded = expandedGroups[groupKey] !== false;
    return (
      <div key={groupKey} style={{ marginBottom: 24 }}>
        <EuiFlexGroup alignItems="center" gutterSize="s" onClick={() => toggleGroup(groupKey)} style={{ cursor: 'pointer' }}>
          <EuiFlexItem grow={false}>
            <EuiButtonIcon iconType={isExpanded ? 'arrowDown' : 'arrowRight'} aria-label={label} />
          </EuiFlexItem>
          <EuiFlexItem>
            <EuiText><h4>{label}</h4></EuiText>
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiText size="s" color="subdued">{groupProjects.length} projetos</EuiText>
          </EuiFlexItem>
        </EuiFlexGroup>
        {isExpanded && (
          <div style={{ paddingLeft: 8 }}>
            <EuiFlexGrid columns={3}>
              {groupProjects.map(renderProjectCard)}
            </EuiFlexGrid>
          </div>
        )}
      </div>
    );
  };

  const renderHome = () => (
    <>
      <EuiFlexGroup gutterSize="none" alignItems="center">
        <EuiFlexItem grow={false}>
          <EuiTitle><h2>Projetos</h2></EuiTitle>
        </EuiFlexItem>
        <EuiFlexItem grow={false} style={{ marginLeft: 12 }}>
          <EuiButtonIcon
            iconType={projects.some(p => getGroupFor(p) === 'coordenador') ? 'usersRolesApp' : 'grid'}
            onClick={() => setExpandedGroups({})}
            aria-label="Dashboard"
          />
        </EuiFlexItem>
      </EuiFlexGroup>
      <EuiSpacer />
      {Object.entries(GROUP_LABELS).map(([key, label]) => renderGroup(key, label))}
    </>
  );

  const renderProjectDetail = () => {
    if (!selectedProject) return null;
    const tabs = [
      { id: 'events', label: 'Eventos' },
      { id: 'providers', label: 'Provedores LLM' },
      { id: 'config', label: 'Config' },
      { id: 'logs', label: 'Logs' },
    ];
    const projectEvents = events.filter(e => e.project_id === selectedProject);
    const agentProviders = providers.filter(p => projectEvents.some(e => e.agent_id === p.agent_id));
    return (
      <>
        <EuiTabs>
          {tabs.map(tab => (
            <EuiTab key={tab.id} isSelected={activeTab === tab.id} onClick={() => setActiveTab(tab.id)}>
              {tab.label}
            </EuiTab>
          ))}
        </EuiTabs>
        <EuiSpacer />
        {activeTab === 'events' && (
          <EuiPanel>
            <EventTable events={filteredEvents} />
          </EuiPanel>
        )}
        {activeTab === 'providers' && (
          <EuiPanel>
            <ProviderSelector
              agents={agentProviders.length > 0 ? agentProviders : providers}
              onProviderChange={handleProviderChange}
              onOpenLlmModal={(agent) => setLlmModalAgent(agent)}
            />
          </EuiPanel>
        )}
        {activeTab === 'config' && (
          <EuiPanel>
            <EuiText color="subdued">Configurações do projeto em abas (em desenvolvimento)</EuiText>
          </EuiPanel>
        )}
        {activeTab === 'logs' && (
          <EuiPanel>
            <EuiText color="subdued">Logs do projeto (em desenvolvimento)</EuiText>
          </EuiPanel>
        )}
      </>
    );
  };

  return (
    <>
      <EuiHeader position="fixed">
        <EuiHeaderSection>
          <EuiHeaderSectionItem border="right">
            <EuiHeaderLogo iconType="logoElastic">Agent Factory</EuiHeaderLogo>
          </EuiHeaderSectionItem>
        </EuiHeaderSection>
      </EuiHeader>
      <div style={{ padding: '24px', marginTop: '56px' }}>
        <Breadcrumb projectId={selectedProject} agentId={selectedAgent} tab={activeTab} onNavigate={handleNavigate} />
        <EuiSpacer />
        {loading ? (
          <EuiFlexGroup justifyContent="center" alignItems="center" style={{ minHeight: 200 }}>
            <EuiFlexItem grow={false}>
              <EuiLoadingSpinner size="xl" />
            </EuiFlexItem>
          </EuiFlexGroup>
        ) : error ? (
          <EuiEmptyPrompt iconType="warning" title={<h2>Erro ao carregar dados</h2>} body={<p>{error.message}</p>} />
        ) : view === 'home' ? (
          renderHome()
        ) : (
          renderProjectDetail()
        )}
      </div>

      {llmModalAgent && (
        <EuiModal onClose={() => setLlmModalAgent(null)}>
          <EuiModalHeader>
            <EuiModalHeaderTitle>
              <EuiFlexGroup alignItems="center" gutterSize="m">
                <EuiFlexItem grow={false}>
                  <EuiIcon type="userAvatar" size="l" />
                </EuiFlexItem>
                <EuiFlexItem>
                  <EuiText><h3>{llmModalAgent.agent_id}</h3></EuiText>
                  <EuiText size="s" color="subdued">{selectedProject || 'AFP-Team'}</EuiText>
                </EuiFlexItem>
                <EuiFlexItem grow={false}>
                  <EuiBadge color={getStatusColor(getProjectStatus(selectedProject))}>
                    {llmModalAgent.current_provider || 'auto'}
                  </EuiBadge>
                </EuiFlexItem>
              </EuiFlexGroup>
            </EuiModalHeaderTitle>
          </EuiModalHeader>
          <EuiModalBody>
            <EuiText>
              <p>Provedor atual: <strong>{llmModalAgent.current_provider || 'auto'}</strong></p>
              <p>Modelo: {llmModalAgent.model || '-'}</p>
            </EuiText>
          </EuiModalBody>
          <EuiModalFooter>
            <EuiButton onClick={() => setLlmModalAgent(null)} fill>Fechar</EuiButton>
          </EuiModalFooter>
        </EuiModal>
      )}
    </>
  );
}

export default App;
