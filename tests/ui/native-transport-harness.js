// Exercise the actual native adapter with a JSON REST boundary to the real router.
// This browser test does not claim to be an Electron/SDK integration test.
import * as React from 'react';
import { createRoot } from 'react-dom/client';
import { createApp } from '../../ui/app.js';
import { createNativeApi } from '../../ui/desktop-entry.js';
const cell = value => ({ get: () => value, subscribe: () => () => {} });
const ctx = {
  async rest(path, { method = 'GET', body } = {}) {
    const response = await fetch(`/api/plugins/network-xray${path}`, {
      method,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Request rejected');
    return result;
  },
};
const api = createNativeApi(ctx, { connectionId: cell('test'), profile: cell('isolated') });
const App = createApp(React, api);
createRoot(document.getElementById('root')).render(React.createElement(App));
