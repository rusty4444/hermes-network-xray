import * as React from 'react';
import { createRoot } from 'react-dom/client';
import { createApp } from './app.js';

export const api = {
  ownerKey: () => 'Standalone · this backend',
  subscribeOwner: () => () => {},
  async request(path, { method = 'GET', body, timeoutMs = 20000 } = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`/api/plugins/network-xray${path}`, {
        method, headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: 'same-origin', signal: controller.signal,
      });
      const result = await response.json();
      if (!response.ok) {
        const detail = result?.detail ?? result?.error;
        throw new Error(typeof detail === 'string' ? detail : detail?.message || `Backend rejected the request (HTTP ${response.status}). Check the URL or bundle and retry.`);
      }
      return result;
    } finally { clearTimeout(timeout); }
  },
};

const App = createApp(React, api);
createRoot(document.getElementById('root')).render(React.createElement(App));
