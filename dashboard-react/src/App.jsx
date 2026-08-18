import React, { useState } from 'react';
import {
  EuiHeader,
  EuiHeaderSection,
  EuiHeaderSectionItem,
  EuiHeaderLogo,
  EuiHeaderLink,
  EuiFlexGrid,
  EuiFlexItem,
  EuiFlexGroup,
  EuiLoadingSpinner,
  EuiEmptyPrompt,
  EuiSpacer,
  EuiTabs,
  EuiTab,
  EuiPanel,
  EuiText,
  EuiModal,
  EuiModalHeader,
  EuiModalHeaderTitle,
  EuiModalBody,
  EuiModalFooter,
  EuiButton,
  EuiBadge,
  EuiIcon,
} from '@elastic/eui';
import { useAfp } from './context/AfpContext';
import LiveShell from './components/LiveShell';
import ProjectCard from './components/ProjectCard';
import TeamAgents from './components/TeamAgents';
import MissionControl from './components/MissionControl';
import ProviderSelector from './components/ProviderSelector';
import EventTable from './components/EventTable';
import Breadcrumb from './components/Breadcrumb';
import { agentKey, getProjectAggregateStatus, getRunningAgents } from './services/eventProcessor';
import { updateAgentProvider } from './services/api';

const TAB_LABELS = {
  agents: 'Equipe',
  'mission-control': 'Mission Control',
  events: 'Eventos',
  providers: 'Provedores LLM',
};

function App() {
  const { state } = useAfp();
  const {
    projects,
    agentsState,
    missionsData,
    events,
    providers,
    connectionStatus,
    loading,
    error,
  } = state;

  const [view, setView] = useState('home');
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [activeTab, setActiveTab] = useState('agents');
  const [llmModalAgent, setLlmModalAgent] = useState(null);

  const selectedProject = projects.find((p) => p.project_id === selectedProjectId);

  const handleNavigate = (newView, projectId, _agentId, tab) => {
    setView(newView);
    if (projectId !== undefined) setSelectedProjectId(projectId);
    if (tab) setActiveTab(tab);
    else if (newView === 'project') setActiveTab('agents');
  };

  const handleProviderChange = async (agentId, newProvider) => {
    try {
      await updateAgentProvider(agentId, newProvider);
    } catch (err) {
      console.error('Failed to update provider', err);
    }
  };

  const getProjectStats = (project) => {
    const agentIds = (project.agents || []).map((a) => a.agent_id);
    const aggregateStatus = getProjectAggregateStatus(project.project_id, agentsState, agentIds);
    const runningCount = getRunningAgents(agentsState).filter((r) => r.projectId === project.project_id).length;
    const eventCount = events.filter((e) => e.project_id === project.project_id).length;
    return { aggregateStatus, runningCount, eventCount };
  };

  const projectEvents = selectedProjectId
    ? events.filter((e) => e.project_id === selectedProjectId)
    : events;

  const agentProviders = selectedProject
    ? (selectedProject.agents || []).map((a) => ({
      agent_id: a.agent_id,
      current_provider: providers[a.agent_id] || a.llm_provider || 'auto',
      model: null,
    }))
    : [];

  const renderHome = () => (
    <>
      <EuiFlexGroup alignItems="center" justifyContent="spaceBetween">
        <EuiFlexItem grow={false}>
          <EuiText><h2>Projetos</h2></EuiText>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiHeaderLink iconType="globe" onClick={() => { setView('mission-global'); }}>
            Mission Control global
          </EuiHeaderLink>
        </EuiFlexItem>
      </EuiFlexGroup>
      <EuiSpacer size="m" />
      <EuiFlexGrid columns={2}>
        {projects.map((project) => {
          const stats = getProjectStats(project);
          return (
            <EuiFlexItem key={project.project_id}>
              <ProjectCard
                project={project}
                {...stats}
                onClick={() => handleNavigate('project', project.project_id)}
              />
            </EuiFlexItem>
          );
        })}
      </EuiFlexGrid>
    </>
  );

  const renderProject = () => {
    if (!selectedProject) return null;
    const tabs = ['agents', 'mission-control', 'events', 'providers'];
    return (
      <>
        <EuiText>
          <p>{selectedProject.description || ''}</p>
        </EuiText>
        <EuiSpacer size="s" />
        <EuiTabs>
          {tabs.map((tab) => (
            <EuiTab key={tab} isSelected={activeTab === tab} onClick={() => setActiveTab(tab)}>
              {TAB_LABELS[tab] || tab}
            </EuiTab>
          ))}
        </EuiTabs>
        <EuiSpacer size="m" />
        {activeTab === 'agents' && (
          <TeamAgents
            project={selectedProject}
            agentsState={agentsState}
            onSelectLlm={(agent) => setLlmModalAgent(agent)}
          />
        )}
        {activeTab === 'mission-control' && (
          <MissionControl missionsData={missionsData} projectId={selectedProjectId} />
        )}
        {activeTab === 'events' && (
          <EuiPanel>
            <EventTable events={projectEvents} />
          </EuiPanel>
        )}
        {activeTab === 'providers' && (
          <EuiPanel>
            <ProviderSelector
              agents={agentProviders}
              onProviderChange={handleProviderChange}
              onOpenLlmModal={(agent) => setLlmModalAgent(agent)}
            />
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
            <EuiHeaderLogo
              iconType="logoElastic"
              onClick={() => handleNavigate('home', null)}
              style={{ cursor: 'pointer' }}
            >
              Console AFP
            </EuiHeaderLogo>
          </EuiHeaderSectionItem>
          <EuiHeaderSectionItem>
            <EuiHeaderLink isActive={view === 'home'} onClick={() => handleNavigate('home', null)}>
              Projetos
            </EuiHeaderLink>
          </EuiHeaderSectionItem>
          <EuiHeaderSectionItem>
            <EuiHeaderLink
              isActive={view === 'mission-global'}
              onClick={() => setView('mission-global')}
            >
              Mission Control
            </EuiHeaderLink>
          </EuiHeaderSectionItem>
        </EuiHeaderSection>
      </EuiHeader>

      <div style={{ padding: 24, marginTop: 56, minHeight: '100vh' }}>
        <LiveShell
          agentsState={agentsState}
          missionsData={missionsData}
          connectionStatus={connectionStatus}
          onNavigate={handleNavigate}
        />
        <Breadcrumb
          projectId={view === 'project' ? selectedProjectId : null}
          tab={view === 'project' ? TAB_LABELS[activeTab] : null}
          onNavigate={(v, pid) => handleNavigate(v, pid)}
        />
        <EuiSpacer size="m" />

        {loading ? (
          <EuiFlexGroup justifyContent="center" style={{ minHeight: 200 }}>
            <EuiFlexItem grow={false}><EuiLoadingSpinner size="xl" /></EuiFlexItem>
          </EuiFlexGroup>
        ) : error ? (
          <EuiEmptyPrompt
            iconType="warning"
            title={<h2>Erro ao carregar</h2>}
            body={<p>{error.message}</p>}
          />
        ) : view === 'home' ? (
          renderHome()
        ) : view === 'mission-global' ? (
          <MissionControl missionsData={missionsData} global />
        ) : (
          renderProject()
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
                  <EuiText><h3>{llmModalAgent.agent_name || llmModalAgent.agent_id}</h3></EuiText>
                  <EuiText size="s" color="subdued">{selectedProjectId}</EuiText>
                </EuiFlexItem>
                <EuiFlexItem grow={false}>
                  <EuiBadge>{llmModalAgent.llm_provider || 'auto'}</EuiBadge>
                </EuiFlexItem>
              </EuiFlexGroup>
            </EuiModalHeaderTitle>
          </EuiModalHeader>
          <EuiModalBody>
            <EuiText>
              <p>Provider: <strong>{llmModalAgent.llm_provider || 'auto'}</strong></p>
              <p>Configure na aba Provedores LLM do projeto.</p>
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
