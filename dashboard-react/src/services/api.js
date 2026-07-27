const BASE_URL = import.meta.env.DEV ? '' : 'http://localhost:8080';

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, options);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${path}`);
  }
  return response.json();
}

async function fetchProjects() {
  return request('/api/projects');
}

async function fetchMissions() {
  return request('/api/missions');
}

async function fetchEvents(projectId, limit = 100) {
  const q = projectId ? `?project=${encodeURIComponent(projectId)}&limit=${limit}` : `?limit=${limit}`;
  return request(`/api/events${q}`);
}

async function fetchAllEvents(limit = 200) {
  return request(`/api/events?limit=${limit}`);
}

async function updateAgentProvider(agentId, provider) {
  return request(`/api/agent/${agentId}/provider`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider }),
  });
}

export {
  BASE_URL,
  fetchProjects,
  fetchMissions,
  fetchEvents,
  fetchAllEvents,
  updateAgentProvider,
};
