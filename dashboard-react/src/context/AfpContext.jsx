import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import {
  fetchProjects,
  fetchMissions,
  fetchAllEvents,
  BASE_URL,
} from '../services/api';
import { applyAgentEvent, bootstrapFromEvents } from '../services/eventProcessor';

const initialState = {
  projects: [],
  missionsApi: [],
  missionsData: {},
  agentsState: {},
  events: [],
  providers: {},
  connectionStatus: 'connecting',
  loading: true,
  error: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'LOAD_START':
      return { ...state, loading: true, error: null };
    case 'LOAD_SUCCESS':
      return {
        ...state,
        loading: false,
        projects: action.projects,
        missionsApi: action.missions,
        providers: action.providers || state.providers,
      };
    case 'LOAD_ERROR':
      return { ...state, loading: false, error: action.error };
    case 'BOOTSTRAP_EVENTS':
      return bootstrapFromEvents(
        { ...state, events: [] },
        action.events,
      );
    case 'SSE_EVENT':
      return applyAgentEvent(state, action.event);
    case 'CONNECTION':
      return { ...state, connectionStatus: action.status };
    case 'SET_PROVIDERS':
      return { ...state, providers: { ...state.providers, ...action.providers } };
    default:
      return state;
  }
}

const AfpContext = createContext(null);

export function AfpProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const loadInitial = useCallback(async () => {
    dispatch({ type: 'LOAD_START' });
    try {
      const [projects, missions, eventPayload] = await Promise.all([
        fetchProjects(),
        fetchMissions(),
        fetchAllEvents(300),
      ]);
      dispatch({
        type: 'LOAD_SUCCESS',
        projects,
        missions: missions.missions || missions || [],
        providers: eventPayload.providers || {},
      });
      dispatch({ type: 'BOOTSTRAP_EVENTS', events: eventPayload.events || [] });
    } catch (err) {
      dispatch({ type: 'LOAD_ERROR', error: err });
    }
  }, []);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    const streamUrl = `${BASE_URL}/api/events/stream`;
    let es = null;
    let reconnectTimer = null;

    function connect() {
      dispatch({ type: 'CONNECTION', status: 'connecting' });
      es = new EventSource(streamUrl);
      es.onopen = () => dispatch({ type: 'CONNECTION', status: 'connected' });
      es.onerror = () => {
        dispatch({ type: 'CONNECTION', status: 'error' });
        es.close();
        reconnectTimer = setTimeout(connect, 5000);
      };
      es.addEventListener('agent_event', (e) => {
        try {
          dispatch({ type: 'SSE_EVENT', event: JSON.parse(e.data) });
        } catch {
          /* ignore malformed */
        }
      });
    }

    connect();
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (es) es.close();
    };
  }, []);

  const value = { state, dispatch, reload: loadInitial };
  return <AfpContext.Provider value={value}>{children}</AfpContext.Provider>;
}

export function useAfp() {
  const ctx = useContext(AfpContext);
  if (!ctx) throw new Error('useAfp must be used within AfpProvider');
  return ctx;
}
