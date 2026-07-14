import React from 'react';
import { EuiInMemoryTable, EuiHealth, EuiBadge, EuiText } from '@elastic/eui';

const getAgentColor = (agentId) => {
  const colors = { coordenador: 'primary', dev: 'success', qa: 'warning', designer: 'accent' };
  return colors[agentId] || 'subdued';
};

const getStatusColor = (status) => {
  switch (status) {
    case 'running': return 'success';
    case 'completed': return 'primary';
    case 'failed': return 'danger';
    case 'waiting': return 'warning';
    default: return 'subdued';
  }
};

const formatTimestamp = (ts) => {
  if (!ts) return '-';
  const d = new Date(ts);
  return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const EventTable = React.memo(({ events }) => {
  const columns = [
    {
      field: 'timestamp',
      name: 'Timestamp',
      sortable: true,
      width: '160px',
      render: (value) => <EuiText size="s">{formatTimestamp(value)}</EuiText>,
    },
    {
      field: 'agent_id',
      name: 'Agent',
      sortable: true,
      width: '140px',
      render: (value) => <EuiBadge color={getAgentColor(value)}>{value}</EuiBadge>,
    },
    {
      field: 'status',
      name: 'Status',
      sortable: true,
      width: '120px',
      render: (value) => <EuiHealth color={getStatusColor(value)}>{value}</EuiHealth>,
    },
    {
      field: 'message',
      name: 'Message',
      sortable: false,
      render: (value) => <EuiText size="s">{String(value || '').substring(0, 80)}</EuiText>,
    },
    {
      field: 'task_id',
      name: 'Task',
      sortable: true,
      width: '120px',
      render: (value) => <EuiText size="s" style={{ fontFamily: 'monospace' }}>{String(value || '').substring(0, 20)}</EuiText>,
    },
    {
      field: 'metrics.duration_ms',
      name: 'Duração',
      sortable: true,
      width: '100px',
      render: (value) => <EuiText size="s">{value ? `${value}ms` : '-'}</EuiText>,
    },
  ];

  return (
    <EuiInMemoryTable
      items={events}
      columns={columns}
      search={{ box: { incremental: true, placeholder: 'Buscar eventos...' } }}
      sorting={{ sort: { field: 'timestamp', direction: 'desc' } }}
      pagination={{ pageSizeOptions: [10, 25, 50], initialPageSize: 25 }}
      tableLayout="auto"
    />
  );
});

export default EventTable;
