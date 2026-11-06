// Exercise the actual native adapter with a JSON REST boundary to the real router.
// This browser test does not claim to be an Electron/SDK integration test.
import * as React from 'react';
import { createRoot } from 'react-dom/client';
import { createApp } from '../../ui/app.js';
import { createNativeApi } from '../../ui/desktop-entry.js';
const cell = value => ({ get: () => value, subscribe: () => () => {} });

// Reject the way Hermes Desktop's ctx.rest does (checked in the Hermes source):
// main rejects with `${status}: ${body}` (apps/desktop/electron/api-transport.ts httpStatusError);
// only 404 is resolved as a sentinel and rethrown unwrapped by preload (electron/api-expected-404.ts);
// every other status crosses ipcRenderer.invoke, which prefixes
// "Error invoking remote method 'hermes:api': Error: " (src/store/notifications.ts unwraps it).
const ctx = {
  async rest(path, { method = 'GET', body } = {}) {
    let response;
    try {
      response = await fetch(`/api/plugins/network-xray${path}`, {
        method,
        headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      // Node's undici message in the main process, behind the same IPC prefix.
      throw new Error("Error invoking remote method 'hermes:api': TypeError: fetch failed");
    }
    const text = await response.text();
    if (!response.ok) {
      const main = `${response.status}: ${text}`;
      if (response.status === 404) throw new Error(main);
      throw new Error(`Error invoking remote method 'hermes:api': Error: ${main}`);
    }
    return JSON.parse(text);
  },
};
const api = createNativeApi(ctx, { connectionId: cell('test'), profile: cell('isolated') });
const App = createApp(React, api);
createRoot(document.getElementById('root')).render(React.createElement(App));
