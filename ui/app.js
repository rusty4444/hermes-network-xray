import { styles } from './styles.js';

export const STAGES = ['dns', 'tcp', 'tls', 'http'];
export const MAX_IMPORT_BYTES = 128 * 1024;
const REQUEST_TIMEOUT_MS = 20000;
const STATUS = {
  ok: { label: 'Passed', symbol: '✓' },
  error: { label: 'Failed', symbol: '×' },
  skipped: { label: 'Skipped', symbol: '−' },
  unknown: { label: 'Unknown', symbol: '?' },
};
const VERDICTS = {
  both_healthy: 'Both reached HTTP', both_failed: 'Both failed',
  diverged: 'Different outcomes', inconclusive: 'Inconclusive capture',
};

export function formatDuration(value) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
    ? `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} ms` : 'Not measured';
}

export function errorMessage(error) {
  const message = typeof error === 'string' ? error : error?.message;
  if (/timeout|timed out|deadline|abort/i.test(message || '') || error?.name === 'AbortError') {
    return 'The request timed out. This is not evidence of a DNS or connection failure. Refresh saved results before retrying; the backend may have completed the capture.';
  }
  return message || 'The backend could not complete this request. Check the connection and try again.';
}

// A slot is invalidated synchronously, before React effects can run.
export function createOperationGuard(ownerKey) {
  let active = true;
  const generations = new Map();
  return {
    invalidate(slot) { generations.set(slot, (generations.get(slot) || 0) + 1); },
    begin(slot) {
      const owner = ownerKey();
      const generation = (generations.get(slot) || 0) + 1;
      generations.set(slot, generation);
      return () => active && owner === ownerKey() && generations.get(slot) === generation;
    },
    dispose() { active = false; },
  };
}

export function validateRequest(url, label) {
  if (!url || url !== url.trim() || /[\u0000-\u0020\u007f\\]/.test(url)) {
    return 'Enter an exact HTTP(S) URL without spaces, control characters, or backslashes.';
  }
  if (url.length > 2048 || !/^https?:\/\//.test(url)) return 'Use an explicit http:// or https:// URL (up to 2048 characters).';
  try {
    const parsed = new URL(url);
    if (!parsed.hostname || parsed.username || parsed.password || url.includes('?') || url.includes('#')) {
      return 'URLs must have a hostname and no credentials, query string, or fragment.';
    }
  } catch { return 'That URL is not valid. Check the hostname, port, and path.'; }
  if (!label || label.length > 48 || /[\u0000-\u001f\u007f]/.test(label)) return 'Name this vantage with 1–48 printable characters.';
  return '';
}

export function parseImportText(text) {
  const bundle = JSON.parse(text);
  const stack = [];
  const tokens = text.match(/"(?:\\.|[^"\\])*"|[{}\[\],:]/g) || [];
  for (const token of tokens) {
    if (token === '{' || token === '[') stack.push({ object: token === '{', keys: new Set(), expectsKey: true });
    else if (token === '}' || token === ']') stack.pop();
    else if (token === ',' && stack.at(-1)?.object) stack.at(-1).expectsKey = true;
    else if (token.startsWith('"') && stack.at(-1)?.object && stack.at(-1).expectsKey) {
      const frame = stack.at(-1);
      const key = JSON.parse(token);
      if (frame.keys.has(key)) throw new Error('Duplicate JSON keys are not allowed.');
      frame.keys.add(key);
      frame.expectsKey = false;
    }
  }
  return bundle;
}

export function buildImportPayload(text) {
  // Validate syntax/duplicate keys, but transport the original text. JSON.parse +
  // JSON.stringify would change Python float forms such as 12000.0 and -0.0.
  parseImportText(text);
  return { bundle_json: text };
}

export function downloadText(filename, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  try { anchor.click(); } finally { setTimeout(() => URL.revokeObjectURL(url), 1000); }
}

function overall(probe) {
  if (probe.capture.status !== 'complete' || probe.stages.some(stage => stage.status === 'unknown')) return 'inconclusive';
  return probe.stages.find(stage => stage.name === 'http')?.status === 'ok' ? 'healthy' : 'failed';
}

function timestamp(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'long' });
}

function displayValue(value) {
  if (value === null || value === undefined) return 'Not recorded';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

/** Shared native/browser view. Only the supplied adapter owns transport. */
export function createApp(React, api) {
  const h = React.createElement;
  const { useState, useEffect, useRef } = React;
  const Button = ({ children, primary, ...props }) => h('button', {
    type: 'button', className: `nx-button${primary ? ' nx-primary' : ''}`, ...props,
  }, children);
  const Badge = ({ children, tone = '' }) => h('span', { className: `nx-badge ${tone ? `nx-${tone}` : ''}` }, children);
  const Field = ({ label, children }) => h('label', { className: 'nx-field' }, h('span', null, label), children);
  const Message = ({ children, error = false }) => children && h('div', {
    className: `nx-message${error ? ' nx-error-message' : ''}`, role: error ? 'alert' : 'status',
  }, children);

  function App() {
    const [owner, setOwner] = useState(api.ownerKey());
    const identity = useRef({ owner: api.ownerKey(), revision: 0 });
    const [revision, setRevision] = useState(0);
    useEffect(() => {
      const update = () => {
        const next = api.ownerKey();
        if (identity.current.owner === next) return;
        identity.current = { owner: next, revision: identity.current.revision + 1 };
        setOwner(next);
        setRevision(identity.current.revision);
      };
      const unsubscribe = api.subscribeOwner(update);
      update();
      return unsubscribe;
    }, []);
    return h(Workspace, { key: `${owner}:${revision}`, owner, identity });
  }

  function Workspace({ owner, identity }) {
    const instance = useRef(identity.current);
    const guard = useRef(null);
    if (!guard.current) guard.current = createOperationGuard(() =>
      identity.current === instance.current ? api.ownerKey() : Symbol('expired-owner'));
    const [url, setUrl] = useState('');
    const [label, setLabel] = useState('This backend');
    const [history, setHistory] = useState([]);
    const [historyState, setHistoryState] = useState({ loading: true, error: '' });
    const [sides, setSides] = useState({ left: {}, right: {} });
    const selectionRevision = useRef(0);
    const [comparison, setComparison] = useState(null);
    const [compareState, setCompareState] = useState({ loading: false, error: '' });
    const [busy, setBusy] = useState('');
    const [notice, setNotice] = useState('');
    const [error, setError] = useState('');
    const [evidence, setEvidence] = useState(null);
    const [experiment, setExperiment] = useState(null);
    const [confirmed, setConfirmed] = useState(false);
    const [downloadBusy, setDownloadBusy] = useState(false);
    const evidenceRef = useRef(null);
    const evidenceTrigger = useRef(null);
    const request = (path, options = {}) => api.request(path, { timeoutMs: REQUEST_TIMEOUT_MS, ...options });

    async function refreshHistory() {
      const current = guard.current.begin('history');
      setHistoryState({ loading: true, error: '' });
      try {
        const result = await request('/probes');
        if (!current()) return;
        setHistory(result.probes);
        setHistoryState({ loading: false, error: '' });
      } catch (cause) {
        if (current()) setHistoryState({ loading: false, error: errorMessage(cause) });
      }
    }

    useEffect(() => {
      // React StrictMode replays mount effects; each lifetime needs a fresh guard.
      const lifetime = createOperationGuard(() =>
        identity.current === instance.current ? api.ownerKey() : Symbol('expired-owner'));
      guard.current = lifetime;
      refreshHistory();
      return () => lifetime.dispose();
    }, []);

    function clearComparison() {
      guard.current.invalidate('compare');
      guard.current.invalidate('report');
      setDownloadBusy(false);
      setComparison(null);
      setCompareState({ loading: false, error: '' });
      setEvidence(null);
      setExperiment(null);
      setConfirmed(false);
    }

    async function select(side, id, envelope) {
      selectionRevision.current += 1;
      const current = guard.current.begin(side);
      clearComparison();
      setSides(previous => ({ ...previous, [side]: { id, envelope, loading: Boolean(id && !envelope), error: '' } }));
      if (!id || envelope) return;
      try {
        const result = await request(`/probes/${encodeURIComponent(id)}`);
        if (current()) setSides(previous => ({ ...previous, [side]: { id, envelope: result, loading: false, error: '' } }));
      } catch (cause) {
        if (current()) setSides(previous => ({ ...previous, [side]: { id, loading: false, error: errorMessage(cause) } }));
      }
    }

    useEffect(() => {
      const left = sides.left.envelope?.probe;
      const right = sides.right.envelope?.probe;
      if (!left || !right) return;
      if (left.id === right.id || left.target.url !== right.target.url) {
        setCompareState({ loading: false, error: left.id === right.id
          ? 'Choose two different captures to compare.' : 'These captures use different URLs. Choose two captures of the exact same URL.' });
        return;
      }
      const current = guard.current.begin('compare');
      setCompareState({ loading: true, error: '' });
      request('/compare', { method: 'POST', body: { left_id: left.id, right_id: right.id } })
        .then(result => {
          if (!current()) return;
          setComparison(result);
          setCompareState({ loading: false, error: '' });
        }).catch(cause => {
          if (current()) setCompareState({ loading: false, error: errorMessage(cause) });
        });
      return () => guard.current.invalidate('compare');
    }, [sides.left.envelope, sides.right.envelope]);

    useEffect(() => { if (evidence) evidenceRef.current?.focus(); }, [evidence]);

    function acceptCapture(result, startingSelection) {
      refreshHistory();
      if (selectionRevision.current === startingSelection) {
        const side = result.origin === 'imported' ? 'right' : 'left';
        select(side, result.probe.id, result);
      }
      setNotice(`${result.origin === 'imported' ? 'Imported' : 'Captured'} “${result.probe.vantage.label}”. Saved to this backend’s history.`);
    }

    async function runProbe(target, vantage, connectIp = null) {
      const invalid = validateRequest(target, vantage);
      if (invalid) { setError(invalid); return; }
      const current = guard.current.begin('mutation');
      const startingSelection = selectionRevision.current;
      setBusy('probe'); setError(''); setNotice('');
      try {
        const body = { url: target, label: vantage };
        if (connectIp !== null) body.connect_ip = connectIp;
        const result = await request('/probe', { method: 'POST', body });
        if (current()) {
          acceptCapture(result, startingSelection);
          setExperiment(null); setConfirmed(false);
        }
      } catch (cause) { if (current()) setError(errorMessage(cause)); }
      finally { if (current()) setBusy(''); }
    }

    async function importFile(event) {
      const file = event.target.files?.[0];
      event.target.value = '';
      if (!file) return;
      const current = guard.current.begin('mutation');
      const startingSelection = selectionRevision.current;
      setError(''); setNotice(''); setBusy('import');
      try {
        if (file.size > MAX_IMPORT_BYTES) throw new Error('Bundle is larger than 128 KiB. Export a single probe JSON file from the collector.');
        let body;
        try { body = buildImportPayload(await file.text()); }
        catch (cause) { throw new Error(`This file is not valid JSON or contains duplicate keys. Choose an unmodified probe bundle. ${cause.message}`); }
        // Reading a file can outlive a profile change. Never post it to the new owner.
        if (!current()) return;
        const result = await request('/import', { method: 'POST', body });
        if (current()) acceptCapture(result, startingSelection);
      } catch (cause) { if (current()) setError(errorMessage(cause)); }
      finally { if (current()) setBusy(''); }
    }

    async function download(kind) {
      const slot = kind === 'report' ? 'report' : 'collector';
      const current = guard.current.begin(slot);
      setError('');
      if (kind === 'report') setDownloadBusy(true);
      try {
        const path = kind === 'report'
          ? `/export/${encodeURIComponent(sides.left.id)}/${encodeURIComponent(sides.right.id)}` : '/collector';
        const result = await request(path);
        if (!current()) return;
        downloadText(result.filename, kind === 'report' ? result.html : result.source,
          kind === 'report' ? 'text/html;charset=utf-8' : 'text/x-python;charset=utf-8');
        setNotice(kind === 'report' ? 'Report download requested. Review addresses and paths before sharing.' : 'Collector download requested. Run it manually on the other machine.');
      } catch (cause) { if (current()) setError(errorMessage(cause)); }
      finally { if (current() && kind === 'report') setDownloadBusy(false); }
    }

    function openEvidence(side, stage, event) {
      evidenceTrigger.current = event.currentTarget;
      setEvidence({ side, stage });
    }
    function closeEvidence() {
      setEvidence(null);
      evidenceTrigger.current?.focus();
    }

    return h('main', { className: 'nx-root' },
      h('style', null, styles),
      h('div', { className: 'nx-shell' },
        h('header', { className: 'nx-header' },
          h('div', { className: 'nx-brand' }, h(NetworkMark), h('div', null,
            h('div', { className: 'nx-eyebrow' }, 'NETWORK DIAGNOSTICS'), h('h1', null, 'Network X-ray'),
            h('p', { className: 'nx-tagline' }, 'Same URL. Two perspectives.'))),
          h('div', { className: 'nx-header-meta' }, h(Badge, null, 'On-demand · read-only'),
            h('span', { className: 'nx-owner', title: owner }, 'Backend scope: ', owner))),
        h('section', { className: 'nx-panel nx-compose', 'aria-labelledby': 'nx-capture-heading' },
          h('div', { className: 'nx-section-heading' }, h('div', null,
            h('span', { className: 'nx-eyebrow' }, '01 / CAPTURE'), h('h2', { id: 'nx-capture-heading' }, 'Trace a single request')),
            h('span', { className: 'nx-caption' }, 'DNS → TCP → TLS → HTTP')),
          h('form', { className: 'nx-probe-form', noValidate: true, onSubmit: event => { event.preventDefault(); if (!busy) runProbe(url, label); } },
            h(Field, { label: 'Target URL' }, h('input', { type: 'url', value: url, placeholder: 'https://service.example/', maxLength: 2048,
              autoComplete: 'off', spellCheck: false, onChange: event => setUrl(event.target.value), 'aria-describedby': 'nx-url-help' })),
            h(Field, { label: 'Name this backend’s vantage' }, h('input', { value: label, maxLength: 48, onChange: event => setLabel(event.target.value) })),
            h(Button, { primary: true, type: 'submit', disabled: Boolean(busy) }, busy === 'probe' ? 'Waiting for capture…' : 'Run probe', h('span', { 'aria-hidden': true }, ' ↗'))),
          h('p', { id: 'nx-url-help', className: 'nx-caption' }, 'Explicit HTTP(S) URL only. No credentials, query strings, or fragments. Runs on this backend—not necessarily this browser’s machine.'),
          h('div', { className: 'nx-policy' }, h('strong', null, 'Direct · no proxy'), 'Single selected address · HEAD only · verified TLS · no redirects followed · no response body'),
          h(Message, { error: true }, error), h(Message, null, busy === 'import' ? 'Validating and saving the bundle…' : notice),
          h('details', { className: 'nx-collector' },
            h('summary', null, h('span', null, 'Add the other perspective'), h('span', { className: 'nx-caption' }, 'Portable collector + JSON import')),
            h('div', { className: 'nx-collector-body' },
              h('ol', null, h('li', null, 'Download the standalone collector. It needs Python 3.10+; no Hermes installation.'),
                h('li', null, 'Copy it to the other machine. Run ', h('code', null, 'python3 network-xray-collector.py --help'), ' for the exact command. Use the same URL and a distinct vantage label.'),
                h('li', null, 'Transfer the saved JSON bundle back, then import it here. Nothing runs remotely from this page.')),
              h('div', { className: 'nx-actions' }, h(Button, { onClick: () => download('collector') }, '↓ Download collector'),
                h('label', { className: `nx-button nx-file-button${busy ? ' nx-disabled' : ''}` }, '↑ Import peer bundle',
                  h('input', { type: 'file', accept: '.json,application/json', disabled: Boolean(busy), onChange: importFile, 'aria-label': 'Import peer bundle' }))),
              h('p', { className: 'nx-caption' }, 'Maximum 128 KiB. Server validates the bundle. A content hash is not proof of origin; imported observations are unauthenticated.')))),
        h('section', { className: 'nx-comparison', 'aria-labelledby': 'nx-compare-heading' },
          h('div', { className: 'nx-section-heading' }, h('div', null, h('span', { className: 'nx-eyebrow' }, '02 / COMPARE'),
            h('h2', { id: 'nx-compare-heading' }, 'Find the first difference')),
            h('div', { className: 'nx-actions' }, h(Button, { onClick: refreshHistory, disabled: historyState.loading }, historyState.loading ? 'Loading history…' : '↻ Refresh history'),
              h(Button, { onClick: () => download('report'), disabled: !comparison || downloadBusy }, downloadBusy ? 'Preparing report…' : '↓ Export report'))),
          h(Message, { error: true }, historyState.error),
          h('div', { className: 'nx-selectors' }, ['left', 'right'].map(side => h(Field, { key: side, label: `${side === 'left' ? 'A' : 'B'} / ${side === 'left' ? 'First' : 'Second'} perspective` },
            h('select', { value: sides[side].id || '', onChange: event => select(side, event.target.value), 'aria-label': `${side === 'left' ? 'First' : 'Second'} perspective` },
              h('option', { value: '' }, history.length ? 'Choose a saved capture…' : 'No saved captures yet'),
              history.map(item => h('option', { value: item.id, key: item.id }, `${item.label} · ${item.overall} · ${item.origin} · ${timestamp(item.captured_at)} · ${item.url}`)))))),
          h(Message, { error: true }, compareState.error),
          compareState.loading && h(Message, null, 'Comparing recorded observations…'),
          comparison && h('div', { className: `nx-verdict nx-verdict-${comparison.verdict}`, role: 'status' },
            h('div', { className: 'nx-verdict-symbol', 'aria-hidden': true }, comparison.first_divergence ? '≠' : '='),
            h('div', null, h('div', { className: 'nx-eyebrow' }, VERDICTS[comparison.verdict] || comparison.verdict),
              h('h3', null, comparison.headline), h('p', null, comparison.first_divergence
                ? `First observed difference · ${comparison.first_divergence.toUpperCase()}` : 'No stage difference identified in the available evidence.'))),
          !comparison && !compareState.loading && !sides.left.id && !sides.right.id && h('div', { className: 'nx-empty-intro' },
            h('h3', null, 'Two captures. One clear comparison.'), h('p', null, 'Run a probe here, import a capture from another vantage, then choose both above. Nothing runs until you ask.')),
          h('div', { className: 'nx-ladders' }, ['left', 'right'].map(side => h(Perspective, {
            key: side, side, state: sides[side], divergence: comparison?.first_divergence,
            selected: evidence, onEvidence: openEvidence, onRetry: () => select(side, sides[side].id),
          }))),
          evidence && h(Evidence, { selection: evidence, envelope: sides[evidence.side].envelope, panelRef: evidenceRef, onClose: closeEvidence }),
          comparison && h(Findings, { comparison, onPrepare: test => { setExperiment({ ...test }); setConfirmed(false); } }),
          experiment && h('section', { className: 'nx-confirm nx-panel', 'aria-labelledby': 'nx-confirm-heading' },
            h('span', { className: 'nx-eyebrow' }, 'EXPLICIT LOCAL EXPERIMENT'), h('h3', { id: 'nx-confirm-heading' }, experiment.title),
            h('p', null, 'This will run on the currently connected backend only. It does not run on the imported peer.'),
            h('dl', { className: 'nx-facts' }, h('dt', null, 'Exact URL'), h('dd', null, experiment.url), h('dt', null, 'Connect IP override'),
              h('dd', null, experiment.connect_ip || 'None — normal DNS selection')),
            experiment.connect_ip && h('p', { className: 'nx-caption' }, 'Original hostname, Host header, and TLS SNI are preserved. This is an explicit override, not a normal-DNS success.'),
            h(Field, { label: 'Local experiment vantage name' }, h('input', { value: label, maxLength: 48, onChange: event => setLabel(event.target.value) })),
            h('label', { className: 'nx-check' }, h('input', { type: 'checkbox', checked: confirmed, onChange: event => setConfirmed(event.target.checked) }),
              `I confirm: run this test on this backend as “${label}”.`),
            h('div', { className: 'nx-actions' }, h(Button, { primary: true, disabled: !confirmed || Boolean(busy),
              onClick: () => runProbe(experiment.url, label, experiment.connect_ip) }, busy === 'probe' ? 'Waiting for capture…' : 'Run confirmed test here'),
              h(Button, { onClick: () => setExperiment(null) }, 'Cancel')))),
        h('footer', { className: 'nx-footer' }, h('span', null, 'Evidence, not a root-cause verdict.'),
          h('span', null, 'Point-in-time captures · one address per probe · browser trust and proxies may differ'))));
  }

  function NetworkMark() {
    return h('svg', { className: 'nx-mark', viewBox: '0 0 48 48', fill: 'none', 'aria-hidden': true },
      h('rect', { x: 1, y: 1, width: 46, height: 46, rx: 12, stroke: 'currentColor', opacity: '.3' }),
      h('path', { d: 'M10 24h8l4-10 6 20 4-10h6', stroke: 'currentColor', strokeWidth: 2, strokeLinejoin: 'round', strokeLinecap: 'round' }));
  }

  function Perspective({ side, state, divergence, selected, onEvidence, onRetry }) {
    const probe = state.envelope?.probe;
    return h('article', { className: 'nx-perspective', 'aria-label': `${side === 'left' ? 'First' : 'Second'} perspective ladder` },
      h('header', { className: 'nx-perspective-header' }, h('span', { className: 'nx-letter' }, side === 'left' ? 'A' : 'B'),
        h('div', { className: 'nx-perspective-title' }, h('h3', null, probe?.vantage.label || 'Awaiting a capture'),
          h('span', { className: 'nx-caption' }, probe ? timestamp(probe.captured_at) : 'Choose a saved result above')),
        probe && h(Badge, { tone: overall(probe) }, overall(probe))),
      state.loading && h(Message, null, 'Loading recorded evidence…'),
      state.error && h('div', { className: 'nx-side-error' }, h(Message, { error: true }, state.error), h(Button, { onClick: onRetry }, 'Retry this capture')),
      probe && h('div', { className: 'nx-probe-meta' }, h(Badge, null, state.envelope.origin === 'local' ? 'Local capture' : 'Imported · unauthenticated'),
        h('span', { className: 'nx-caption' }, probe.vantage.platform, ' · Python ', probe.vantage.python),
        h('code', { className: 'nx-target' }, probe.target.url),
        h('div', { className: 'nx-caption' }, 'Capture: ', probe.capture.status, ' · ', formatDuration(probe.capture.duration_ms)),
        probe.capture.error && h(Message, { error: true }, `${probe.capture.error.code}: ${probe.capture.error.message}`),
        h('div', { className: `nx-override${probe.target.connect_ip ? ' nx-override-active' : ''}` }, probe.target.connect_ip
          ? `Explicit connect-IP override: ${probe.target.connect_ip} · original Host/SNI retained` : 'No IP override · DNS-selected address'),
        h('div', { className: 'nx-caption' }, 'Direct / no proxy · single address · HEAD · TLS verified when applicable')),
      h('ol', { className: 'nx-stage-list' }, STAGES.map((name, index) => {
        const stage = probe?.stages.find(item => item.name === name);
        const status = stage ? (STATUS[stage.status] || STATUS.unknown) : { symbol: '·', label: 'No capture' };
        const isSelected = selected?.side === side && selected?.stage === name;
        return h('li', { key: name, className: `nx-stage-item${divergence === name ? ' nx-divergence' : ''}` },
          h('button', { type: 'button', className: `nx-stage nx-${stage?.status || 'empty'}${isSelected ? ' nx-selected' : ''}`,
            disabled: !stage, onClick: event => onEvidence(side, name, event), 'aria-expanded': Boolean(isSelected),
            'aria-controls': stage ? 'nx-evidence' : undefined, 'aria-label': `${probe?.vantage.label || side}: ${name.toUpperCase()} ${status.label}; view evidence` },
            h('span', { className: 'nx-stage-symbol', 'aria-hidden': true }, status.symbol),
            h('div', { className: 'nx-stage-content' }, h('div', { className: 'nx-stage-top' },
              h('strong', null, name.toUpperCase()), h('span', { className: 'nx-stage-status' }, status.label)),
              h('p', null, stage?.summary || ['Resolve the hostname', 'Connect to one address', 'Verify the certificate', 'Read HTTP response headers'][index])),
            h('div', { className: 'nx-stage-time' }, stage ? formatDuration(stage.duration_ms) : '—',
              stage && h('span', { className: 'nx-evidence-link' }, 'Evidence ↗'))));
      })));
  }

  function Evidence({ selection, envelope, panelRef, onClose }) {
    const stage = envelope?.probe.stages.find(item => item.name === selection.stage);
    if (!stage) return null;
    const facts = { ...stage.details, ...(stage.error ? { error_code: stage.error.code, error_message: stage.error.message } : {}) };
    return h('section', { id: 'nx-evidence', className: 'nx-panel nx-evidence', ref: panelRef, tabIndex: -1,
      'aria-labelledby': 'nx-evidence-heading', onKeyDown: event => { if (event.key === 'Escape') onClose(); } },
      h('div', { className: 'nx-section-heading' }, h('div', null, h('span', { className: 'nx-eyebrow' }, 'RECORDED STAGE EVIDENCE'),
        h('h3', { id: 'nx-evidence-heading' }, `${stage.name.toUpperCase()} / ${envelope.probe.vantage.label}`)),
        h(Button, { onClick: onClose, 'aria-label': 'Close stage evidence' }, 'Close ×')),
      h('p', null, stage.summary, ' · ', STATUS[stage.status]?.label || 'Unknown', ' · ', formatDuration(stage.duration_ms)),
      Object.keys(facts).length ? h('dl', { className: 'nx-facts' }, Object.entries(facts).flatMap(([key, value]) => [
        h('dt', { key: `${key}-key` }, key), h('dd', { key: `${key}-value` }, h('code', null, displayValue(value))),
      ])) : h('p', { className: 'nx-caption' }, 'No stage details were recorded. Skipped or unknown is not proof of failure.'),
      h('p', { className: 'nx-caption' }, 'Captured ', timestamp(envelope.probe.captured_at), ' · ', envelope.origin,
        ' · Probe ', envelope.probe.id));
  }

  function Findings({ comparison, onPrepare }) {
    const groups = [
      { kind: 'observation', title: 'What the evidence shows', subtitle: 'OBSERVATIONS' },
      { kind: 'hypothesis', title: 'What might explain it', subtitle: 'HYPOTHESES · NOT PROVEN' },
    ];
    return h('div', { className: 'nx-analysis' }, h('div', { className: 'nx-findings-grid' }, groups.map(group =>
      h('section', { key: group.kind, className: 'nx-finding-section' }, h('span', { className: 'nx-eyebrow' }, group.subtitle),
        h('h3', null, group.title), comparison.findings.some(finding => finding.kind === group.kind)
          ? h('ul', null, comparison.findings.filter(finding => finding.kind === group.kind).map((finding, index) => h('li', { key: index },
            h('span', { className: 'nx-finding-stage' }, finding.stage.toUpperCase()), finding.text)))
          : h('p', { className: 'nx-caption' }, group.kind === 'hypothesis' ? 'No specific hypothesis is supported by these captures.' : 'No additional observations recorded.')))),
      comparison.next_tests.length > 0 && h('section', { className: 'nx-next-tests' }, h('span', { className: 'nx-eyebrow' }, '03 / TEST A HYPOTHESIS'),
        h('h3', null, 'A deliberate next step'), comparison.next_tests.map((test, index) => h('div', { className: 'nx-next-test', key: index },
          h('div', null, h('h4', null, test.title), h('p', null, test.reason), h('p', { className: 'nx-caption' }, 'Local backend only · confirmation required')),
          h(Button, { onClick: () => onPrepare(test) }, 'Review test →')))),
      h('section', { className: 'nx-limitations' }, h('h3', null, 'Limits of this comparison'),
        h('ul', null, [...new Set([...comparison.limitations, ...comparison.findings.filter(item => item.kind === 'limitation').map(item => item.text)])]
          .map((text, index) => h('li', { key: index }, text)))));
  }

  return App;
}
