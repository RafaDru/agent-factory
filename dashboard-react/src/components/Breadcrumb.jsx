import React from 'react';
import { EuiBreadcrumbs } from '@elastic/eui';

const Breadcrumb = ({ projectId, agentId, tab, onNavigate }) => {
  const items = [{ text: 'Home', onClick: () => onNavigate('home', null, null) }];

  if (projectId) {
    items.push({
      text: projectId,
      onClick: agentId || tab ? () => onNavigate('project', projectId, null) : null,
    });
  }

  if (tab && projectId && !agentId) {
    items.push({ text: tab, onClick: () => onNavigate('project', projectId, tab) });
  }

  if (agentId) {
    items.push({ text: agentId });
  }

  return (
    <EuiBreadcrumbs
      breadcrumbs={items.map((item) => ({
        text: item.text,
        href: '#',
        onClick: (e) => { e.preventDefault(); if (item.onClick) item.onClick(); },
      }))}
      truncate={false}
    />
  );
};

export default Breadcrumb;
