export function agentKey(projectId, agentId) {
  return `${projectId}:${agentId}`;
}

function createAgentState() {
  return {
    status: 'ready',
    subStatus: '',
    task: null,
    mission: null,
    timerStart: null,
    events: [],
    lastExecution: null,
  };
}

const TERMINAL_MISSION = new Set(['completed', 'partial', 'failed', 'cancelled']);

function missionStatusFromApi(apiObj) {
  const s = String(apiObj?.status || '').toLowerCase();
  if (TERMINAL_MISSION.has(s) || s === 'running' || s === 'planned') return s;
  return 'running';
}

function normalizeStatus(status) {
  if (!status) return 'ready';
  const s = String(status).toLowerCase();
  if (s === 'success') return 'completed';
  return s;
}

function isCoordinator(agentId) {
  return String(agentId || '').toLowerCase().includes('coorden');
}

function extractMissionIdFromMessage(msg) {
  const m = msg.match(/Missao\s+'([^']+)'/i);
  return m ? m[1] : null;
}

function extractDelegation(msg) {
  let match = msg.match(/Passo\s+'(.+?)'\s*->\s*(\w+)/i);
  if (match) {
    return { taskName: match[1].trim(), targetAgent: match[2].trim() };
  }
  match = msg.match(/Delegando\s+'([^']+)'\s+para\s+(\w+)/i);
  if (match) {
    return { taskName: match[1].trim(), targetAgent: match[2].trim() };
  }
  match = msg.match(/Delegando\s+para\s+(\w+):?\s*(.*)/i);
  if (match) {
    return { taskName: (match[2] || '').trim() || msg, targetAgent: match[1].trim() };
  }
  return null;
}

export function applyAgentEvent(state, rawEvent) {
  const event = { ...rawEvent };
  const agentId = event.agent_id;
  const projectId = event.project_id || 'unknown';
  if (!agentId) return state;

  const key = agentKey(projectId, agentId);
  const agentsState = { ...state.agentsState };
  const agentState = { ...(agentsState[key] || createAgentState()) };

  const status = normalizeStatus(event.status);
  if (event.status) {
    agentState.status = status;
    if (status === 'running') {
      agentState.timerStart = agentState.timerStart || Date.now();
    } else {
      agentState.timerStart = null;
    }
  }

  if (event.sub_status || event.message) {
    agentState.subStatus = event.sub_status || String(event.message).slice(0, 120);
  }
  if (event.task_id) agentState.task = event.task_id;
  if (event.mission_id) agentState.mission = event.mission_id;
  else if (event.payload?.mission) agentState.mission = event.payload.mission;

  agentState.lastExecution = {
    timestamp: event.timestamp || new Date().toISOString(),
    mission: agentState.mission,
    task: agentState.task,
    status: agentState.status,
    message: event.message || '',
  };

  const evtRecord = {
    id: `${Date.now()}-${Math.random()}`,
    actor: agentId,
    message: event.message || event.status || '',
    timestamp: event.timestamp || new Date().toISOString(),
    missionId: event.mission_id || agentState.mission,
    taskId: event.task_id || event.trace_id || null,
    status: event.status,
    projectId,
    payload: event.payload,
  };

  agentState.events = [evtRecord, ...(agentState.events || [])].slice(0, 250);
  agentsState[key] = agentState;

  const missionsData = rebuildMissionsData(
    agentsState,
    state.missionsApi || [],
    state.missionsData || {},
    evtRecord,
  );

  const events = [event, ...(state.events || [])]
    .filter((e, i, arr) => i === 0 || e.timestamp !== arr[1]?.timestamp || e.agent_id !== arr[1]?.agent_id)
    .slice(0, 500);

  return {
    ...state,
    agentsState,
    missionsData,
    events,
  };
}

export function bootstrapFromEvents(state, events) {
  let next = { ...state, events: [] };
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0),
  );
  for (const event of sorted) {
    next = applyAgentEvent(next, event);
  }
  return next;
}

function rebuildMissionsData(agentsState, missionsApi, prevMissionsData, latestEvent) {
  const allEvents = [];
  Object.values(agentsState).forEach((aState) => {
    (aState.events || []).forEach((evt) => allEvents.push(evt));
  });
  if (latestEvent && !allEvents.find((e) => e.id === latestEvent.id)) {
    allEvents.push(latestEvent);
  }
  allEvents.sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0));

  const apiMissions = {};
  (missionsApi || []).forEach((m) => {
    apiMissions[m.id || m.mission_id || ''] = m;
  });

  const missionsData = { ...prevMissionsData };
  let currentMissionId = null;

  for (const event of allEvents) {
    const msg = event.message || '';
    const agentId = event.actor || '?';
    const coord = isCoordinator(agentId);

    let missionId = event.missionId;
    if (!missionId && coord) {
      missionId = extractMissionIdFromMessage(msg);
      if (missionId) currentMissionId = missionId;
    }
    if (!missionId && currentMissionId) missionId = currentMissionId;
    if (!missionId) continue;

    if (!missionsData[missionId]) {
      const apiObj = apiMissions[missionId] || {};
      missionsData[missionId] = {
        id: missionId,
        projectId: apiObj.project_id || event.projectId || event.payload?.project_id || 'unknown',
        objective: apiObj.objective || apiObj.objetivo || '',
        status: missionStatusFromApi(apiObj),
        timestamp: event.timestamp,
        tasks: {},
        delegations: [],
      };
    }

    const mission = missionsData[missionId];

    if (coord && event.payload?.objective) {
      mission.objective = event.payload.objective;
    }

    if (coord) {
      const delegation = extractDelegation(msg);
      if (delegation) {
        const taskKey = delegation.taskName.substring(0, 80);
        if (!mission.tasks[taskKey]) {
          mission.tasks[taskKey] = {
            id: taskKey,
            name: delegation.taskName,
            agent: delegation.targetAgent,
            requestedBy: agentId,
            status: 'running',
          };
        } else {
          mission.tasks[taskKey].status = 'running';
          mission.tasks[taskKey].agent = delegation.targetAgent;
        }
        mission.delegations.push({
          id: `${missionId}-${mission.delegations.length}`,
          from: agentId,
          to: delegation.targetAgent,
          task: delegation.taskName,
          timestamp: event.timestamp,
          status: 'running',
        });
        currentMissionId = missionId;
      }
    }

    const taskKeys = Object.keys(mission.tasks);
    if (taskKeys.length > 0) {
      const lastKey = taskKeys[taskKeys.length - 1];
      const task = mission.tasks[lastKey];
      const st = normalizeStatus(event.status);
      if (st === 'completed') {
        if (task.status !== 'failed') task.status = 'completed';
      } else if (st === 'failed') {
        task.status = 'failed';
      } else if (st === 'running' && task.status !== 'completed' && task.status !== 'failed') {
        task.status = 'running';
      }
      if (!coord && agentId !== '?') task.agent = agentId;
    }

    const tasks = Object.values(mission.tasks);
    if (tasks.some((t) => t.status === 'running')) mission.status = 'running';
    else if (tasks.length && tasks.every((t) => t.status === 'completed')) mission.status = 'completed';
    else if (tasks.some((t) => t.status === 'failed')) mission.status = 'failed';

    // Status canonico do coordenador (payload ou API)
    const payloadStatus = event.payload?.mission_status;
    if (payloadStatus && TERMINAL_MISSION.has(String(payloadStatus).toLowerCase())) {
      mission.status = String(payloadStatus).toLowerCase();
    }
    if (/Missao concluida:/i.test(msg)) mission.status = 'completed';
    if (/Missao parcial:/i.test(msg)) mission.status = 'partial';
    if (/Missao falhou:/i.test(msg)) mission.status = 'failed';
  }

  // API status.json prevalece sobre inferencia quando terminal
  Object.entries(apiMissions).forEach(([id, apiObj]) => {
    const canonical = missionStatusFromApi(apiObj);
    if (!missionsData[id]) {
      missionsData[id] = {
        id,
        projectId: apiObj.project_id || 'unknown',
        objective: apiObj.objective || '',
        status: canonical,
        timestamp: apiObj.updated_at || apiObj.started_at || null,
        tasks: {},
        delegations: [],
      };
    } else if (TERMINAL_MISSION.has(canonical)) {
      missionsData[id].status = canonical;
    }
    if (apiObj.objective) missionsData[id].objective = apiObj.objective;
  });

  return missionsData;
}

export function getRunningAgents(agentsState) {
  return Object.entries(agentsState || {})
    .filter(([, s]) => s.status === 'running')
    .map(([key, s]) => {
      const [projectId, agentId] = key.split(':');
      return { projectId, agentId, ...s };
    });
}

export function getProjectAggregateStatus(projectId, agentsState, agentIds = []) {
  const keys = agentIds.map((id) => agentKey(projectId, id));
  const statuses = keys.map((k) => agentsState[k]?.status).filter(Boolean);
  if (statuses.includes('running')) return 'running';
  if (statuses.includes('failed')) return 'failed';
  if (statuses.includes('completed')) return 'completed';
  return 'ready';
}

export function getActiveDelegations(missionsData, projectId = null) {
  const chains = [];
  Object.values(missionsData || {}).forEach((mission) => {
    if (mission.status !== 'running') return;
    if (projectId && mission.projectId !== projectId) return;
    const recent = (mission.delegations || []).slice(-3);
    if (recent.length === 0 && Object.keys(mission.tasks || {}).length > 0) {
      const lastTask = Object.values(mission.tasks).slice(-1)[0];
      if (lastTask) {
        chains.push({
          projectId: mission.projectId,
          missionId: mission.id,
          from: lastTask.requestedBy || 'coordenador',
          to: lastTask.agent,
          task: lastTask.name,
        });
      }
      return;
    }
    recent.forEach((d) => {
      chains.push({
        projectId: mission.projectId,
        missionId: mission.id,
        from: d.from,
        to: d.to,
        task: d.task,
      });
    });
  });
  return chains;
}
