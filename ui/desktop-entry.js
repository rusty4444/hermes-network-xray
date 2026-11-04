import * as React from 'react';
import { ROUTES_AREA, SIDEBAR_NAV_AREA, host } from '@hermes/plugin-sdk';
import { createApp } from './app.js';

export function createNativeApi(ctx, state) {
  return {
    request: (path, options = {}) => ctx.rest(path, options),
    ownerKey: () => JSON.stringify([state.connectionId.get(), state.profile.get()]),
    subscribeOwner(callback) {
      const offConnection = state.connectionId.subscribe(callback);
      const offProfile = state.profile.subscribe(callback);
      return () => { offConnection(); offProfile(); };
    },
  };
}

export default {
  id: 'network-xray',
  name: 'Network X-ray',
  register(ctx) {
    const App = createApp(React, createNativeApi(ctx, host.state));
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: '/network-xray' }, render: () => React.createElement(App) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: '/network-xray', label: 'Network X-ray', codicon: 'pulse' } },
    ]);
  },
};
