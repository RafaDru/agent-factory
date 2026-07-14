// C:\Users\rafae\agent-factory/dashboard-react/src/services/api.js
const BASE_URL = 'http://localhost:8080';

async function fetchProjects() {
  try {
    const response = await fetch(`${BASE_URL}/api/projects`);
    if (!response.ok) {
      throw new Error(`Erro ao buscar projetos: ${response.status}`);
    }
    const projectIds = await response.json();
    return projectIds;
  } catch (error) {
    throw error;
  }
}

async function fetchEvents(projectId, limit) {
  try {
    const response = await fetch(`${BASE_URL}/api/events?project=${projectId}&limit=${limit}`);
    if (!response.ok) {
      throw new Error(`Erro ao buscar eventos: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    throw error;
  }
}

async function fetchStatus(projectId) {
  try {
    const response = await fetch(`${BASE_URL}/api/status?project=${projectId}`);
    if (!response.ok) {
      throw new Error(`Erro ao buscar status: ${response.status}`);
    }
    const status = await response.json();
    return status;
  } catch (error) {
    throw error;
  }
}

async function fetchAgentProvider(agentId) {
  try {
    const response = await fetch(`${BASE_URL}/api/agent/${agentId}/provider`);
    if (!response.ok) {
      throw new Error(`Erro ao buscar provedor do agente: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    throw error;
  }
}

async function updateAgentProvider(agentId, provider) {
  try {
    const response = await fetch(`${BASE_URL}/api/agent/${agentId}/provider`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ provider }),
    });
    if (!response.ok) {
      throw new Error(`Erro ao atualizar provedor do agente: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    throw error;
  }
}

export { fetchProjects, fetchEvents, fetchStatus, fetchAgentProvider, updateAgentProvider };
