import React, { useState, useEffect, useRef } from 'react';
import {
  EuiCard,
  EuiHealth,
  EuiFlexGroup,
  EuiFlexItem,
  EuiText,
  EuiButtonIcon,
  EuiPanel,
  EuiSpacer,
  EuiCodeBlock,
  EuiBadge,
} from '@elastic/eui';

const ProjectCard = ({ projectId, events, status, onToggleExpand }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  const isRunning = status?.status === 'running';

  useEffect(() => {
    if (isRunning) {
      startTimeRef.current = Date.now();
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      setElapsed(0);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isRunning]);

  const formatTimer = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  const getColor = () => {
    switch (status?.status) {
      case 'running': return 'success';
      case 'completed': return 'primary';
      case 'failed': return 'danger';
      default: return 'subdued';
    }
  };

  const handleToggle = () => {
    setIsExpanded(!isExpanded);
    if (onToggleExpand) onToggleExpand();
  };

  return (
    <EuiCard layout="compact" hasShadow={false}>
      <EuiFlexGroup alignItems="center">
        <EuiFlexItem grow={false}>
          <EuiHealth color={getColor()}>{status?.status || 'idle'}</EuiHealth>
        </EuiFlexItem>
        <EuiFlexItem>
          <EuiFlexGroup alignItems="center" gutterSize="s">
            <EuiFlexItem>
              <EuiText><h2>{projectId}</h2></EuiText>
            </EuiFlexItem>
            {isRunning ? (
              <EuiFlexItem grow={false}>
                <EuiBadge color="success">{formatTimer(elapsed)}</EuiBadge>
              </EuiFlexItem>
            ) : (
              <EuiFlexItem grow={false}>
                <EuiText size="s" color="subdued">Idle</EuiText>
              </EuiFlexItem>
            )}
          </EuiFlexGroup>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiText size="s" color="subdued">{events.length} eventos</EuiText>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiButtonIcon
            iconType={isExpanded ? 'arrowUp' : 'arrowDown'}
            onClick={handleToggle}
            aria-label="Expandir"
          />
        </EuiFlexItem>
      </EuiFlexGroup>
      {isExpanded && (
        <>
          <EuiSpacer size="s" />
          <EuiPanel color="subdued" paddingSize="s">
            <EuiText size="s"><strong>Logs recentes</strong></EuiText>
            <EuiSpacer size="xs" />
            <EuiCodeBlock fontSize="s" isCopyable={false} paddingSize="s" transparentBackground>
              {events.slice(-5).map((e) =>
                `[${new Date(e.timestamp).toLocaleTimeString('pt-BR')}] ${e.agent_id}: ${e.message}`
              ).join('\n') || '(sem logs)'}
            </EuiCodeBlock>
          </EuiPanel>
        </>
      )}
    </EuiCard>
  );
};

export default ProjectCard;
