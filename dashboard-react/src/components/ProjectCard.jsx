// C:\Users\rafae\agent-factory/dashboard-react/src/components/ProjectCard.jsx
import React from 'react';
import {
  EuiCard,
  EuiHealth,
  EuiBadge,
  EuiFlexGroup,
  EuiFlexItem,
  EuiIcon,
  EuiText,
  EuiButtonIcon,
} from '@elastic/eui';

const ProjectCard = ({ projectId, events, status, onToggleExpand }) => {
  const [isExpanded, setIsExpanded] = React.useState(false);

  const handleToggleExpand = () => {
    setIsExpanded(!isExpanded);
    onToggleExpand();
  };

  const getBadgeColor = () => {
    switch (status.status) {
      case 'running':
        return 'success';
      case 'completed':
        return 'primary';
      case 'failed':
        return 'danger';
      default:
        return 'subdued';
    }
  };

  return (
    <EuiCard layout="compact" hasShadow={false}>
      <EuiFlexGroup>
        <EuiFlexItem grow={false}>
          <EuiHealth color={getBadgeColor()}>{status.status}</EuiHealth>
        </EuiFlexItem>
        <EuiFlexItem>
          <EuiText>
            <h2>{projectId}</h2>
          </EuiText>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiText>
            <p>Total de eventos: {events.length}</p>
          </EuiText>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiButtonIcon
            iconType={isExpanded ? 'arrowUp' : 'arrowDown'}
            onClick={handleToggleExpand}
          />
        </EuiFlexItem>
      </EuiFlexGroup>
      {isExpanded && (
        <EuiFlexGroup>
          {events.slice(-5).map((event, index) => (
            <EuiFlexItem key={index}>
              <EuiText>
                <p>{event.message}</p>
              </EuiText>
            </EuiFlexItem>
          ))}
        </EuiFlexGroup>
      )}
    </EuiCard>
  );
};

export default ProjectCard;
