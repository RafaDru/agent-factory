import React from 'react';
import ReactDOM from 'react-dom/client';
import { EuiProvider } from '@elastic/eui';
import App from './App'; // This will be App.jsx
import './App.scss';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <EuiProvider colorMode="dark">
      <App />
    </EuiProvider>
  </React.StrictMode>
);
