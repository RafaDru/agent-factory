import React from 'react';
import ReactDOM from 'react-dom/client';
import { EuiProvider } from '@elastic/eui';
import { AfpProvider } from './context/AfpContext';
import App from './App';
import './App.scss';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <EuiProvider colorMode="dark">
      <AfpProvider>
        <App />
      </AfpProvider>
    </EuiProvider>
  </React.StrictMode>,
);
