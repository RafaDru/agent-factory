import React, { useState, useEffect, useCallback } from 'react';
import {
  EuiPanel,
  EuiHeader,
  EuiHeaderSection,
  EuiHeaderSectionItem,
  EuiHeaderLogo,
  EuiHeaderLink,
  EuiHeaderLinks,
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiLoadingSpinner,
  EuiEmptyPrompt,
  EuiText,
  EuiTitle,
  EuiSpacer,
} from '@elastic/eui';
import EventTable from './components/EventTable';
import ProviderSelector from './components/ProviderSelector';
import { fetchProjects as apiFetchProjects, fetchEvents, fetchAgentProvider } from './services/api';

function App() {
  const [isSideNavOpen, setSideNavOpen] = useState(true);
  const [projects, setProjects] = useState([]);
  const [events, setEvents] = useState([]);
  const [providers, setProviders] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const toggleSideNav = () => {
    setSideNavOpen(!isSideNavOpen);
  };

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

  const handleProviderChange = async (agentId, newProvider) => {
    try {
      const { updateAgentProvider } = await import('./services/api');
      await updateAgentProvider(agentId, newProvider);
      setProviders(prev => prev.map(p => p.agent_id === agentId ? { ...p, current_provider: newProvider } : p));
    } catch (err) {
      console.error('Failed to update provider', err);
    }
  };

  const handleProjectSelect = (project) => {
    setSelectedProject(project);
  };

  const filteredEvents = selectedProject
    ? events.filter((e) => e.project_id === selectedProject)
    : events;

  const renderProjectCards = () => (
    <EuiFlexGrid columns={3}>
      {projects.map((projectId) => (
        <EuiFlexItem key={projectId}>
          <EuiPanel
            paddingSize="m"
            onClick={() => setSelectedProject(projectId === selectedProject ? null : projectId)}
            style={{ cursor: 'pointer' }}
          >
            <EuiText><h3>{projectId}</h3></EuiText>
            <EuiText size="s" color="subdued">
              {events.filter(e => e.project_id === projectId).length} eventos
            </EuiText>
          </EuiPanel>
        </EuiFlexItem>
      ))}
    </EuiFlexGrid>
  );

  return (
    <>
      <EuiHeader position="fixed">
        <EuiHeaderSection>
          <EuiHeaderSectionItem border="right">
            <EuiHeaderLogo iconType="logoElastic">Agent Factory</EuiHeaderLogo>
          </EuiHeaderSectionItem>
        </EuiHeaderSection>
        <EuiHeaderSection side="right">
          <EuiHeaderSectionItem>
            <EuiHeaderLinks>
              <EuiHeaderLink isActive>Dashboard</EuiHeaderLink>
              <EuiHeaderLink>Settings</EuiHeaderLink>
            </EuiHeaderLinks>
          </EuiHeaderSectionItem>
        </EuiHeaderSection>
      </EuiHeader>
      <div style={{ padding: '24px', marginTop: '56px' }}>
        {loading ? (
          <EuiFlexGroup justifyContent="center" alignItems="center" style={{ minHeight: 200 }}>
            <EuiFlexItem grow={false}>
              <EuiLoadingSpinner size="xl" />
            </EuiFlexItem>
          </EuiFlexGroup>
        ) : error ? (
          <EuiEmptyPrompt iconType="warning" title={<h2>Erro ao carregar dados</h2>} body={<p>{error.message}</p>} />
        ) : (
          <>
            <EuiTitle><h2>Projetos</h2></EuiTitle>
            <EuiSpacer />
            {renderProjectCards()}
            <EuiSpacer size="xxl" />
            <EuiTitle><h2>Eventos</h2></EuiTitle>
            <EuiSpacer />
            <EuiPanel>
              <EventTable events={filteredEvents} />
            </EuiPanel>
            <EuiSpacer size="xxl" />
            <EuiTitle><h2>Provedores LLM</h2></EuiTitle>
            <EuiSpacer />
            <EuiPanel>
              <ProviderSelector agents={providers} onProviderChange={handleProviderChange} />
            </EuiPanel>
          </>
        )}
      </div>
    </>
  );
}

export default App;
