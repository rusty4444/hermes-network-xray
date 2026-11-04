export const styles = `
.nx-root {
  --nx-bg: var(--ui-surface-background, #11161d);
  --nx-panel: var(--ui-widget-surface-background, #181f28);
  --nx-raised: var(--ui-control-hover-background, #202a35);
  --nx-text: var(--ui-text-primary, #edf2f7);
  --nx-muted: var(--ui-text-secondary, #b0bdcc);
  --nx-faint: var(--ui-text-tertiary, #99a8ba);
  --nx-border: var(--ui-stroke-primary, #33404f);
  --nx-accent: color-mix(in srgb, var(--nx-text) 45%, #159aaa);
  --nx-good: color-mix(in srgb, var(--nx-text) 45%, #50a781);
  --nx-bad: color-mix(in srgb, var(--nx-text) 45%, #db5145);
  --nx-warn: color-mix(in srgb, var(--nx-text) 45%, #b98e4d);
  box-sizing: border-box; min-width: 0; width: 100%; height: 100%; overflow: auto;
  background: var(--nx-bg); color: var(--nx-text); font: 14px/1.5 system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color-scheme: dark; accent-color: var(--nx-accent);
}
.nx-root *, .nx-root *::before, .nx-root *::after { box-sizing: border-box; }
.nx-root h1, .nx-root h2, .nx-root h3, .nx-root h4, .nx-root p { margin: 0; }
.nx-root h1 { font-size: clamp(24px, 3vw, 32px); font-weight: 650; letter-spacing: -.035em; line-height: 1.15; }
.nx-root h2 { font-size: 20px; font-weight: 600; letter-spacing: -.02em; line-height: 1.3; }
.nx-root h3 { font-size: 16px; line-height: 1.4; font-weight: 600; }
.nx-root h4 { font-size: 14px; font-weight: 600; }
.nx-root button, .nx-root input, .nx-root select { font: inherit; }
.nx-root button, .nx-root summary, .nx-root select { -webkit-tap-highlight-color: transparent; }
.nx-root button { cursor: pointer; }
.nx-root button:disabled, .nx-root .nx-disabled { cursor: not-allowed; opacity: .55; }
.nx-root :focus-visible { outline: 2px solid var(--nx-accent); outline-offset: 4px; }
.nx-root code { font: 12px/1.6 ui-monospace, SFMono-Regular, Consolas, monospace; }
.nx-root .nx-shell { max-width: 1280px; padding: 40px 40px 24px; margin: 0 auto; }
.nx-root .nx-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; margin-bottom: 32px; }
.nx-root .nx-brand { display: flex; align-items: center; gap: 16px; }
.nx-root .nx-mark { width: 48px; height: 48px; color: var(--nx-accent); flex: 0 0 auto; }
.nx-root .nx-eyebrow { display: block; font-size: 10px; font-weight: 650; line-height: 1.6; letter-spacing: .13em; color: var(--nx-faint); margin-bottom: 8px; }
.nx-root .nx-tagline { color: var(--nx-muted); margin-top: 8px; font-size: 14px; }
.nx-root .nx-header-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; padding-top: 4px; max-width: 35%; }
.nx-root .nx-owner { font-size: 11px; color: var(--nx-faint); overflow-wrap: anywhere; text-align: right; }
.nx-root .nx-badge { display: inline-flex; align-items: center; font-size: 10px; font-weight: 550; letter-spacing: .025em; line-height: 1.5; padding: 4px 8px; border: 1px solid var(--nx-border); border-radius: 5px; color: var(--nx-muted); white-space: nowrap; }
.nx-root .nx-healthy { color: var(--nx-good); }
.nx-root .nx-failed { color: var(--nx-bad); }
.nx-root .nx-inconclusive { color: var(--nx-warn); }
.nx-root .nx-panel { background: var(--nx-panel); border: 1px solid var(--nx-border); border-radius: 12px; }
.nx-root .nx-compose { padding: 24px; margin-bottom: 40px; }
.nx-root .nx-section-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; }
.nx-root .nx-section-heading .nx-eyebrow { margin-bottom: 4px; }
.nx-root .nx-caption { font-size: 12px; color: var(--nx-faint); line-height: 1.6; }
.nx-root .nx-probe-form { display: grid; grid-template-columns: minmax(0, 1fr) minmax(180px, .42fr) auto; gap: 16px; align-items: end; margin-bottom: 12px; }
.nx-root .nx-field { display: flex; flex-direction: column; gap: 8px; min-width: 0; font-size: 12px; color: var(--nx-muted); }
.nx-root input:not([type=checkbox]):not([type=file]), .nx-root select { width: 100%; min-width: 0; border: 1px solid var(--nx-border); background: var(--nx-bg); border-radius: 6px; padding: 11px 12px; color: var(--nx-text); font-size: 13px; height: 44px; }
.nx-root input::placeholder { color: var(--nx-faint); opacity: .85; }
.nx-root input:focus, .nx-root select:focus { border-color: var(--nx-accent); }
.nx-root .nx-button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 40px; padding: 9px 14px; border-radius: 6px; background: transparent; border: 1px solid var(--nx-border); color: var(--nx-text); font-size: 12px; font-weight: 550; text-decoration: none; white-space: nowrap; line-height: 1.5; }
.nx-root .nx-button:hover:not(:disabled) { background: var(--nx-raised); border-color: var(--nx-faint); }
.nx-root .nx-primary { background: #76d5e0; color: #10272d; border-color: #76d5e0; }
.nx-root .nx-primary:hover:not(:disabled) { background: #a2e5ec; border-color: #a2e5ec; }
.nx-root .nx-probe-form .nx-button { height: 44px; }
.nx-root .nx-policy { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; margin-top: 16px; font-size: 11px; color: var(--nx-faint); }
.nx-root .nx-policy strong { color: var(--nx-muted); font-weight: 550; }
.nx-root .nx-message { padding: 12px 16px; border: 1px solid var(--nx-border); border-radius: 6px; margin-top: 16px; color: var(--nx-muted); overflow-wrap: anywhere; font-size: 13px; }
.nx-root .nx-error-message { color: var(--nx-bad); border-color: color-mix(in srgb, var(--nx-bad) 40%, var(--nx-border)); }
.nx-root .nx-collector { margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--nx-border); }
.nx-root .nx-collector summary { cursor: pointer; color: var(--nx-muted); font-size: 13px; }
.nx-root .nx-collector summary .nx-caption { margin-left: 16px; }
.nx-root .nx-collector-body { margin-top: 16px; max-width: 76ch; }
.nx-root .nx-collector ol { padding-left: 20px; color: var(--nx-muted); font-size: 13px; }
.nx-root .nx-collector li { padding-left: 4px; margin-bottom: 8px; }
.nx-root .nx-collector code { background: var(--nx-bg); padding: 2px 4px; border-radius: 3px; overflow-wrap: anywhere; }
.nx-root .nx-collector-body > .nx-caption { margin-top: 16px; }
.nx-root .nx-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.nx-root .nx-file-button { position: relative; cursor: pointer; overflow: hidden; }
.nx-root .nx-file-button input { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
.nx-root .nx-file-button:focus-within { outline: 2px solid var(--nx-accent); outline-offset: 4px; }
.nx-root .nx-selectors { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
.nx-root .nx-selectors select { text-overflow: ellipsis; padding-right: 24px; }
.nx-root .nx-verdict { display: flex; gap: 16px; align-items: center; border: 1px solid var(--nx-border); border-left: 3px solid var(--nx-accent); background: var(--nx-panel); padding: 20px 24px; border-radius: 8px; margin: 24px 0; }
.nx-root .nx-verdict-symbol { flex-shrink: 0; width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; background: var(--nx-raised); color: var(--nx-accent); font-size: 24px; }
.nx-root .nx-verdict .nx-eyebrow { color: var(--nx-accent); margin-bottom: 4px; }
.nx-root .nx-verdict p { margin-top: 4px; font-size: 12px; color: var(--nx-muted); }
.nx-root .nx-verdict-both_failed { border-left-color: var(--nx-bad); }
.nx-root .nx-verdict-inconclusive { border-left-color: var(--nx-warn); }
.nx-root .nx-empty-intro { padding: 8px 0 24px; }
.nx-root .nx-empty-intro p { color: var(--nx-muted); font-size: 13px; margin-top: 4px; max-width: 80ch; }
.nx-root .nx-ladders { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 24px; align-items: start; }
.nx-root .nx-perspective { border: 1px solid var(--nx-border); border-radius: 12px; background: var(--nx-panel); min-width: 0; overflow: hidden; }
.nx-root .nx-perspective-header { display: flex; gap: 12px; align-items: center; padding: 20px; border-bottom: 1px solid var(--nx-border); min-height: 88px; }
.nx-root .nx-letter { font-size: 12px; font-weight: 650; color: var(--nx-accent); flex-shrink: 0; width: 28px; height: 32px; display: grid; place-items: center; border: 1px solid var(--nx-border); border-radius: 5px; }
.nx-root .nx-perspective-title { flex: 1; min-width: 0; }
.nx-root .nx-perspective-title h3 { overflow-wrap: anywhere; }
.nx-root .nx-perspective-title .nx-caption { font-size: 11px; }
.nx-root .nx-probe-meta { padding: 16px 20px 0; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.nx-root .nx-target { width: 100%; overflow-wrap: anywhere; color: var(--nx-muted); }
.nx-root .nx-probe-meta > .nx-caption, .nx-root .nx-probe-meta > .nx-message { width: 100%; }
.nx-root .nx-probe-meta > .nx-caption:nth-child(2) { width: auto; }
.nx-root .nx-override { width: 100%; font-size: 11px; color: var(--nx-faint); padding: 8px 0 0; overflow-wrap: anywhere; }
.nx-root .nx-override-active { color: var(--nx-warn); }
.nx-root .nx-stage-list { list-style: none; padding: 16px 12px; margin: 0; }
.nx-root .nx-stage-item { position: relative; }
.nx-root .nx-stage-item:not(:last-child)::after { content: ''; position: absolute; top: 53px; bottom: -24px; left: 24px; width: 1px; background: var(--nx-border); pointer-events: none; }
.nx-root .nx-stage { position: relative; width: 100%; display: flex; align-items: flex-start; gap: 12px; border: 1px solid transparent; background: transparent; border-radius: 8px; padding: 16px 12px; text-align: left; color: var(--nx-text); min-height: 96px; }
.nx-root .nx-stage:disabled { opacity: 1; cursor: default; }
.nx-root .nx-stage:hover:not(:disabled), .nx-root .nx-stage.nx-selected { background: var(--nx-raised); border-color: var(--nx-border); }
.nx-root .nx-stage-symbol { background: var(--nx-panel); position: relative; z-index: 1; flex: 0 0 24px; width: 24px; height: 24px; display: grid; place-items: center; border: 1px solid currentColor; border-radius: 50%; font-size: 13px; color: var(--nx-faint); }
.nx-root .nx-ok .nx-stage-symbol, .nx-root .nx-ok .nx-stage-status { color: var(--nx-good); }
.nx-root .nx-error .nx-stage-symbol, .nx-root .nx-error .nx-stage-status { color: var(--nx-bad); }
.nx-root .nx-unknown .nx-stage-symbol, .nx-root .nx-unknown .nx-stage-status { color: var(--nx-warn); }
.nx-root .nx-stage-content { flex: 1; min-width: 0; }
.nx-root .nx-stage-top { display: flex; align-items: center; gap: 12px; min-height: 24px; flex-wrap: wrap; }
.nx-root .nx-stage-top strong { font-size: 13px; font-weight: 650; letter-spacing: .03em; }
.nx-root .nx-stage-status { font-size: 10px; color: var(--nx-faint); }
.nx-root .nx-stage-content p { color: var(--nx-muted); font-size: 12px; line-height: 1.5; margin-top: 4px; overflow-wrap: anywhere; }
.nx-root .nx-stage-time { flex-shrink: 0; font: 11px/24px ui-monospace, SFMono-Regular, Consolas, monospace; color: var(--nx-muted); text-align: right; font-variant-numeric: tabular-nums; }
.nx-root .nx-evidence-link { display: block; font: 10px/1.6 system-ui, sans-serif; color: var(--nx-faint); margin-top: 8px; }
.nx-root .nx-divergence .nx-stage { border-color: color-mix(in srgb, var(--nx-accent) 35%, transparent); }
.nx-root .nx-divergence .nx-stage-top strong { color: var(--nx-accent); }
.nx-root .nx-empty .nx-stage-content { color: var(--nx-faint); }
.nx-root .nx-evidence { padding: 24px; margin-top: 24px; border-top: 2px solid var(--nx-accent); scroll-margin-block: 24px; }
.nx-root .nx-evidence > p { color: var(--nx-muted); }
.nx-root .nx-facts { display: grid; grid-template-columns: minmax(100px, 180px) minmax(0, 1fr); gap: 0 24px; font-size: 12px; margin: 16px 0; }
.nx-root .nx-facts dt, .nx-root .nx-facts dd { margin: 0; padding: 12px 0; border-top: 1px solid var(--nx-border); overflow-wrap: anywhere; }
.nx-root .nx-facts dt { color: var(--nx-faint); }
.nx-root .nx-facts dd { white-space: pre-wrap; }
.nx-root .nx-findings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-top: 32px; }
.nx-root .nx-finding-section { border-top: 1px solid var(--nx-border); padding-top: 24px; }
.nx-root .nx-finding-section h3 { margin-bottom: 16px; }
.nx-root .nx-finding-section ul { list-style: none; padding: 0; margin: 0; }
.nx-root .nx-finding-section li { font-size: 13px; color: var(--nx-muted); margin-bottom: 16px; line-height: 1.7; overflow-wrap: anywhere; }
.nx-root .nx-finding-stage { font: 10px/1.5 ui-monospace, SFMono-Regular, Consolas, monospace; color: var(--nx-faint); display: block; margin-bottom: 4px; }
.nx-root .nx-next-tests { margin-top: 32px; }
.nx-root .nx-next-test { display: flex; justify-content: space-between; gap: 24px; align-items: center; padding: 20px 0; border-bottom: 1px solid var(--nx-border); }
.nx-root .nx-next-test p { margin-top: 4px; font-size: 13px; color: var(--nx-muted); max-width: 70ch; }
.nx-root .nx-next-test .nx-caption { font-size: 11px; color: var(--nx-faint); }
.nx-root .nx-limitations { padding: 24px; border: 1px dashed var(--nx-border); border-radius: 8px; margin-top: 32px; }
.nx-root .nx-limitations h3 { font-size: 13px; color: var(--nx-muted); }
.nx-root .nx-limitations ul { padding-left: 16px; margin-bottom: 0; color: var(--nx-faint); font-size: 12px; }
.nx-root .nx-limitations li { margin-top: 8px; }
.nx-root .nx-confirm { padding: 24px; margin-top: 24px; border-color: var(--nx-accent); }
.nx-root .nx-confirm > p { color: var(--nx-muted); margin-top: 12px; }
.nx-root .nx-confirm > .nx-field { max-width: 360px; margin-top: 16px; }
.nx-root .nx-check { display: flex; align-items: flex-start; gap: 12px; margin: 24px 0; font-size: 13px; }
.nx-root .nx-check input { margin-top: 4px; }
.nx-root .nx-footer { display: flex; justify-content: space-between; gap: 16px; font-size: 11px; color: var(--nx-faint); padding-top: 32px; margin-top: 32px; border-top: 1px solid var(--nx-border); }
.nx-root .nx-side-error { padding: 0 16px 16px; }
.nx-root .nx-side-error .nx-button { margin-top: 8px; }
@media (prefers-color-scheme: light) {
  .nx-root { --nx-bg: var(--ui-surface-background, #f4f6f8); --nx-panel: var(--ui-widget-surface-background, #ffffff); --nx-raised: var(--ui-control-hover-background, #eef2f5); --nx-text: var(--ui-text-primary, #172632); --nx-muted: var(--ui-text-secondary, #445568); --nx-faint: var(--ui-text-tertiary, #586b7d); --nx-border: var(--ui-stroke-primary, #d3dce4); color-scheme: light; }
}
@media (max-width: 980px) {
  .nx-root .nx-shell { padding: 24px; }
  .nx-root .nx-probe-form { grid-template-columns: minmax(0, 1fr) minmax(160px, .65fr); }
  .nx-root .nx-probe-form .nx-button { grid-column: 1 / -1; justify-self: start; }
  .nx-root .nx-stage { gap: 8px; padding: 16px 8px; }
  .nx-root .nx-stage-item:not(:last-child)::after { left: 20px; }
  .nx-root .nx-stage-time { max-width: 80px; }
}
@media (max-width: 700px) {
  .nx-root .nx-shell { padding: 24px 16px; }
  .nx-root .nx-header { flex-direction: column; gap: 16px; }
  .nx-root .nx-header-meta { max-width: 100%; align-items: flex-start; }
  .nx-root .nx-owner { text-align: left; }
  .nx-root .nx-compose { padding: 20px 16px; margin-bottom: 32px; }
  .nx-root .nx-section-heading { flex-wrap: wrap; }
  .nx-root .nx-section-heading > .nx-caption { display: none; }
  .nx-root .nx-probe-form, .nx-root .nx-selectors, .nx-root .nx-ladders, .nx-root .nx-findings-grid { grid-template-columns: minmax(0, 1fr); gap: 16px; }
  .nx-root .nx-probe-form .nx-button { width: 100%; }
  .nx-root .nx-collector summary .nx-caption { display: block; margin: 4px 0 0 16px; }
  .nx-root .nx-verdict { padding: 16px; align-items: flex-start; }
  .nx-root .nx-verdict-symbol { width: 32px; height: 32px; }
  .nx-root .nx-facts { grid-template-columns: minmax(80px, .6fr) minmax(0, 1fr); gap: 0 16px; }
  .nx-root .nx-evidence, .nx-root .nx-confirm, .nx-root .nx-limitations { padding: 20px 16px; }
  .nx-root .nx-next-test { flex-direction: column; align-items: flex-start; gap: 12px; }
  .nx-root .nx-footer { flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  .nx-root *, .nx-root *::before, .nx-root *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
`;