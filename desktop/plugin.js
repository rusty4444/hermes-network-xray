// ui/desktop-entry.js
import * as React from "react";
import { ROUTES_AREA, SIDEBAR_NAV_AREA, host } from "@hermes/plugin-sdk";

// ui/styles.js
var styles = `
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

// ui/app.js
var STAGES = ["dns", "tcp", "tls", "http"];
var MAX_IMPORT_BYTES = 128 * 1024;
var REQUEST_TIMEOUT_MS = 2e4;
var STATUS = {
  ok: { label: "Passed", symbol: "✓" },
  error: { label: "Failed", symbol: "×" },
  skipped: { label: "Skipped", symbol: "−" },
  unknown: { label: "Unknown", symbol: "?" }
};
var VERDICTS = {
  both_healthy: "Both reached HTTP",
  both_failed: "Both failed",
  diverged: "Different outcomes",
  inconclusive: "Inconclusive capture"
};
function formatDuration(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? `${value.toLocaleString(void 0, { maximumFractionDigits: 1 })} ms` : "Not measured";
}
function errorMessage(error) {
  const message = typeof error === "string" ? error : error?.message;
  if (/timeout|timed out|deadline|abort/i.test(message || "") || error?.name === "AbortError") {
    return "The request timed out. This is not evidence of a DNS or connection failure. Refresh saved results before retrying; the backend may have completed the capture.";
  }
  return message || "The backend could not complete this request. Check the connection and try again.";
}
function createOperationGuard(ownerKey) {
  let active = true;
  const generations = /* @__PURE__ */ new Map();
  return {
    invalidate(slot) {
      generations.set(slot, (generations.get(slot) || 0) + 1);
    },
    begin(slot) {
      const owner = ownerKey();
      const generation = (generations.get(slot) || 0) + 1;
      generations.set(slot, generation);
      return () => active && owner === ownerKey() && generations.get(slot) === generation;
    },
    dispose() {
      active = false;
    }
  };
}
function validateRequest(url, label) {
  if (!url || url !== url.trim() || /[\u0000-\u0020\u007f\\]/.test(url)) {
    return "Enter an exact HTTP(S) URL without spaces, control characters, or backslashes.";
  }
  if (url.length > 2048 || !/^https?:\/\//.test(url)) return "Use an explicit http:// or https:// URL (up to 2048 characters).";
  try {
    const parsed = new URL(url);
    if (!parsed.hostname || parsed.username || parsed.password || url.includes("?") || url.includes("#")) {
      return "URLs must have a hostname and no credentials, query string, or fragment.";
    }
  } catch {
    return "That URL is not valid. Check the hostname, port, and path.";
  }
  if (!label || label.length > 48 || /[\u0000-\u001f\u007f]/.test(label)) return "Name this vantage with 1–48 printable characters.";
  return "";
}
function parseImportText(text) {
  const bundle = JSON.parse(text);
  const stack = [];
  const tokens = text.match(/"(?:\\.|[^"\\])*"|[{}\[\],:]/g) || [];
  for (const token of tokens) {
    if (token === "{" || token === "[") stack.push({ object: token === "{", keys: /* @__PURE__ */ new Set(), expectsKey: true });
    else if (token === "}" || token === "]") stack.pop();
    else if (token === "," && stack.at(-1)?.object) stack.at(-1).expectsKey = true;
    else if (token.startsWith('"') && stack.at(-1)?.object && stack.at(-1).expectsKey) {
      const frame = stack.at(-1);
      const key = JSON.parse(token);
      if (frame.keys.has(key)) throw new Error("Duplicate JSON keys are not allowed.");
      frame.keys.add(key);
      frame.expectsKey = false;
    }
  }
  return bundle;
}
function buildImportPayload(text) {
  parseImportText(text);
  return { bundle_json: text };
}
function downloadText(filename, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  try {
    anchor.click();
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 1e3);
  }
}
function overall(probe) {
  if (probe.capture.status !== "complete" || probe.stages.some((stage) => stage.status === "unknown")) return "inconclusive";
  return probe.stages.find((stage) => stage.name === "http")?.status === "ok" ? "healthy" : "failed";
}
function timestamp(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(void 0, { dateStyle: "medium", timeStyle: "long" });
}
function displayValue(value) {
  if (value === null || value === void 0) return "Not recorded";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}
function createApp(React2, api) {
  const h = React2.createElement;
  const { useState, useEffect, useRef } = React2;
  const Button = ({ children, primary, ...props }) => h("button", {
    type: "button",
    className: `nx-button${primary ? " nx-primary" : ""}`,
    ...props
  }, children);
  const Badge = ({ children, tone = "" }) => h("span", { className: `nx-badge ${tone ? `nx-${tone}` : ""}` }, children);
  const Field = ({ label, children }) => h("label", { className: "nx-field" }, h("span", null, label), children);
  const Message = ({ children, error = false }) => children && h("div", {
    className: `nx-message${error ? " nx-error-message" : ""}`,
    role: error ? "alert" : "status"
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
    if (!guard.current) guard.current = createOperationGuard(() => identity.current === instance.current ? api.ownerKey() : /* @__PURE__ */ Symbol("expired-owner"));
    const [url, setUrl] = useState("");
    const [label, setLabel] = useState("This backend");
    const [history, setHistory] = useState([]);
    const [historyState, setHistoryState] = useState({ loading: true, error: "" });
    const [sides, setSides] = useState({ left: {}, right: {} });
    const selectionRevision = useRef(0);
    const [comparison, setComparison] = useState(null);
    const [compareState, setCompareState] = useState({ loading: false, error: "" });
    const [busy, setBusy] = useState("");
    const [notice, setNotice] = useState("");
    const [error, setError] = useState("");
    const [evidence, setEvidence] = useState(null);
    const [experiment, setExperiment] = useState(null);
    const [confirmed, setConfirmed] = useState(false);
    const [downloadBusy, setDownloadBusy] = useState(false);
    const evidenceRef = useRef(null);
    const evidenceTrigger = useRef(null);
    const request = (path, options = {}) => api.request(path, { timeoutMs: REQUEST_TIMEOUT_MS, ...options });
    async function refreshHistory() {
      const current = guard.current.begin("history");
      setHistoryState({ loading: true, error: "" });
      try {
        const result = await request("/probes");
        if (!current()) return;
        setHistory(result.probes);
        setHistoryState({ loading: false, error: "" });
      } catch (cause) {
        if (current()) setHistoryState({ loading: false, error: errorMessage(cause) });
      }
    }
    useEffect(() => {
      const lifetime = createOperationGuard(() => identity.current === instance.current ? api.ownerKey() : /* @__PURE__ */ Symbol("expired-owner"));
      guard.current = lifetime;
      refreshHistory();
      return () => lifetime.dispose();
    }, []);
    function clearComparison() {
      guard.current.invalidate("compare");
      guard.current.invalidate("report");
      setDownloadBusy(false);
      setComparison(null);
      setCompareState({ loading: false, error: "" });
      setEvidence(null);
      setExperiment(null);
      setConfirmed(false);
    }
    async function select(side, id, envelope) {
      selectionRevision.current += 1;
      const current = guard.current.begin(side);
      clearComparison();
      setSides((previous) => ({ ...previous, [side]: { id, envelope, loading: Boolean(id && !envelope), error: "" } }));
      if (!id || envelope) return;
      try {
        const result = await request(`/probes/${encodeURIComponent(id)}`);
        if (current()) setSides((previous) => ({ ...previous, [side]: { id, envelope: result, loading: false, error: "" } }));
      } catch (cause) {
        if (current()) setSides((previous) => ({ ...previous, [side]: { id, loading: false, error: errorMessage(cause) } }));
      }
    }
    useEffect(() => {
      const left = sides.left.envelope?.probe;
      const right = sides.right.envelope?.probe;
      if (!left || !right) return;
      if (left.id === right.id || left.target.url !== right.target.url) {
        setCompareState({ loading: false, error: left.id === right.id ? "Choose two different captures to compare." : "These captures use different URLs. Choose two captures of the exact same URL." });
        return;
      }
      const current = guard.current.begin("compare");
      setCompareState({ loading: true, error: "" });
      request("/compare", { method: "POST", body: { left_id: left.id, right_id: right.id } }).then((result) => {
        if (!current()) return;
        setComparison(result);
        setCompareState({ loading: false, error: "" });
      }).catch((cause) => {
        if (current()) setCompareState({ loading: false, error: errorMessage(cause) });
      });
      return () => guard.current.invalidate("compare");
    }, [sides.left.envelope, sides.right.envelope]);
    useEffect(() => {
      if (evidence) evidenceRef.current?.focus();
    }, [evidence]);
    function acceptCapture(result, startingSelection) {
      refreshHistory();
      if (selectionRevision.current === startingSelection) {
        const side = result.origin === "imported" ? "right" : "left";
        select(side, result.probe.id, result);
      }
      setNotice(`${result.origin === "imported" ? "Imported" : "Captured"} “${result.probe.vantage.label}”. Saved to this backend’s history.`);
    }
    async function runProbe(target, vantage, connectIp = null) {
      const invalid = validateRequest(target, vantage);
      if (invalid) {
        setError(invalid);
        return;
      }
      const current = guard.current.begin("mutation");
      const startingSelection = selectionRevision.current;
      setBusy("probe");
      setError("");
      setNotice("");
      try {
        const body = { url: target, label: vantage };
        if (connectIp !== null) body.connect_ip = connectIp;
        const result = await request("/probe", { method: "POST", body });
        if (current()) {
          acceptCapture(result, startingSelection);
          setExperiment(null);
          setConfirmed(false);
        }
      } catch (cause) {
        if (current()) setError(errorMessage(cause));
      } finally {
        if (current()) setBusy("");
      }
    }
    async function importFile(event) {
      const file = event.target.files?.[0];
      event.target.value = "";
      if (!file) return;
      const current = guard.current.begin("mutation");
      const startingSelection = selectionRevision.current;
      setError("");
      setNotice("");
      setBusy("import");
      try {
        if (file.size > MAX_IMPORT_BYTES) throw new Error("Bundle is larger than 128 KiB. Export a single probe JSON file from the collector.");
        let body;
        try {
          body = buildImportPayload(await file.text());
        } catch (cause) {
          throw new Error(`This file is not valid JSON or contains duplicate keys. Choose an unmodified probe bundle. ${cause.message}`);
        }
        if (!current()) return;
        const result = await request("/import", { method: "POST", body });
        if (current()) acceptCapture(result, startingSelection);
      } catch (cause) {
        if (current()) setError(errorMessage(cause));
      } finally {
        if (current()) setBusy("");
      }
    }
    async function download(kind) {
      const slot = kind === "report" ? "report" : "collector";
      const current = guard.current.begin(slot);
      setError("");
      if (kind === "report") setDownloadBusy(true);
      try {
        const path = kind === "report" ? `/export/${encodeURIComponent(sides.left.id)}/${encodeURIComponent(sides.right.id)}` : "/collector";
        const result = await request(path);
        if (!current()) return;
        downloadText(
          result.filename,
          kind === "report" ? result.html : result.source,
          kind === "report" ? "text/html;charset=utf-8" : "text/x-python;charset=utf-8"
        );
        setNotice(kind === "report" ? "Report download requested. Review addresses and paths before sharing." : "Collector download requested. Run it manually on the other machine.");
      } catch (cause) {
        if (current()) setError(errorMessage(cause));
      } finally {
        if (current() && kind === "report") setDownloadBusy(false);
      }
    }
    function openEvidence(side, stage, event) {
      evidenceTrigger.current = event.currentTarget;
      setEvidence({ side, stage });
    }
    function closeEvidence() {
      setEvidence(null);
      evidenceTrigger.current?.focus();
    }
    return h(
      "main",
      { className: "nx-root" },
      h("style", null, styles),
      h(
        "div",
        { className: "nx-shell" },
        h(
          "header",
          { className: "nx-header" },
          h("div", { className: "nx-brand" }, h(NetworkMark), h(
            "div",
            null,
            h("div", { className: "nx-eyebrow" }, "NETWORK DIAGNOSTICS"),
            h("h1", null, "Network X-ray"),
            h("p", { className: "nx-tagline" }, "Same URL. Two perspectives.")
          )),
          h(
            "div",
            { className: "nx-header-meta" },
            h(Badge, null, "On-demand · read-only"),
            h("span", { className: "nx-owner", title: owner }, "Backend scope: ", owner)
          )
        ),
        h(
          "section",
          { className: "nx-panel nx-compose", "aria-labelledby": "nx-capture-heading" },
          h(
            "div",
            { className: "nx-section-heading" },
            h(
              "div",
              null,
              h("span", { className: "nx-eyebrow" }, "01 / CAPTURE"),
              h("h2", { id: "nx-capture-heading" }, "Trace a single request")
            ),
            h("span", { className: "nx-caption" }, "DNS → TCP → TLS → HTTP")
          ),
          h(
            "form",
            { className: "nx-probe-form", noValidate: true, onSubmit: (event) => {
              event.preventDefault();
              if (!busy) runProbe(url, label);
            } },
            h(Field, { label: "Target URL" }, h("input", {
              type: "url",
              value: url,
              placeholder: "https://service.example/",
              maxLength: 2048,
              autoComplete: "off",
              spellCheck: false,
              onChange: (event) => setUrl(event.target.value),
              "aria-describedby": "nx-url-help"
            })),
            h(Field, { label: "Name this backend’s vantage" }, h("input", { value: label, maxLength: 48, onChange: (event) => setLabel(event.target.value) })),
            h(Button, { primary: true, type: "submit", disabled: Boolean(busy) }, busy === "probe" ? "Waiting for capture…" : "Run probe", h("span", { "aria-hidden": true }, " ↗"))
          ),
          h("p", { id: "nx-url-help", className: "nx-caption" }, "Explicit HTTP(S) URL only. No credentials, query strings, or fragments. Runs on this backend—not necessarily this browser’s machine."),
          h("div", { className: "nx-policy" }, h("strong", null, "Direct · no proxy"), "Single selected address · HEAD only · verified TLS · no redirects followed · no response body"),
          h(Message, { error: true }, error),
          h(Message, null, busy === "import" ? "Validating and saving the bundle…" : notice),
          h(
            "details",
            { className: "nx-collector" },
            h("summary", null, h("span", null, "Add the other perspective"), h("span", { className: "nx-caption" }, "Portable collector + JSON import")),
            h(
              "div",
              { className: "nx-collector-body" },
              h(
                "ol",
                null,
                h("li", null, "Download the standalone collector. It needs Python 3.10+; no Hermes installation."),
                h("li", null, "Copy it to the other machine. Run ", h("code", null, "python3 network-xray-collector.py --help"), " for the exact command. Use the same URL and a distinct vantage label."),
                h("li", null, "Transfer the saved JSON bundle back, then import it here. Nothing runs remotely from this page.")
              ),
              h(
                "div",
                { className: "nx-actions" },
                h(Button, { onClick: () => download("collector") }, "↓ Download collector"),
                h(
                  "label",
                  { className: `nx-button nx-file-button${busy ? " nx-disabled" : ""}` },
                  "↑ Import peer bundle",
                  h("input", { type: "file", accept: ".json,application/json", disabled: Boolean(busy), onChange: importFile, "aria-label": "Import peer bundle" })
                )
              ),
              h("p", { className: "nx-caption" }, "Maximum 128 KiB. Server validates the bundle. A content hash is not proof of origin; imported observations are unauthenticated.")
            )
          )
        ),
        h(
          "section",
          { className: "nx-comparison", "aria-labelledby": "nx-compare-heading" },
          h(
            "div",
            { className: "nx-section-heading" },
            h(
              "div",
              null,
              h("span", { className: "nx-eyebrow" }, "02 / COMPARE"),
              h("h2", { id: "nx-compare-heading" }, "Find the first difference")
            ),
            h(
              "div",
              { className: "nx-actions" },
              h(Button, { onClick: refreshHistory, disabled: historyState.loading }, historyState.loading ? "Loading history…" : "↻ Refresh history"),
              h(Button, { onClick: () => download("report"), disabled: !comparison || downloadBusy }, downloadBusy ? "Preparing report…" : "↓ Export report")
            )
          ),
          h(Message, { error: true }, historyState.error),
          h("div", { className: "nx-selectors" }, ["left", "right"].map((side) => h(
            Field,
            { key: side, label: `${side === "left" ? "A" : "B"} / ${side === "left" ? "First" : "Second"} perspective` },
            h(
              "select",
              { value: sides[side].id || "", onChange: (event) => select(side, event.target.value), "aria-label": `${side === "left" ? "First" : "Second"} perspective` },
              h("option", { value: "" }, history.length ? "Choose a saved capture…" : "No saved captures yet"),
              history.map((item) => h("option", { value: item.id, key: item.id }, `${item.label} · ${item.overall} · ${item.origin} · ${timestamp(item.captured_at)} · ${item.url}`))
            )
          ))),
          h(Message, { error: true }, compareState.error),
          compareState.loading && h(Message, null, "Comparing recorded observations…"),
          comparison && h(
            "div",
            { className: `nx-verdict nx-verdict-${comparison.verdict}`, role: "status" },
            h("div", { className: "nx-verdict-symbol", "aria-hidden": true }, comparison.first_divergence ? "≠" : "="),
            h(
              "div",
              null,
              h("div", { className: "nx-eyebrow" }, VERDICTS[comparison.verdict] || comparison.verdict),
              h("h3", null, comparison.headline),
              h("p", null, comparison.first_divergence ? `First observed difference · ${comparison.first_divergence.toUpperCase()}` : "No stage difference identified in the available evidence.")
            )
          ),
          !comparison && !compareState.loading && !sides.left.id && !sides.right.id && h(
            "div",
            { className: "nx-empty-intro" },
            h("h3", null, "Two captures. One clear comparison."),
            h("p", null, "Run a probe here, import a capture from another vantage, then choose both above. Nothing runs until you ask.")
          ),
          h("div", { className: "nx-ladders" }, ["left", "right"].map((side) => h(Perspective, {
            key: side,
            side,
            state: sides[side],
            divergence: comparison?.first_divergence,
            selected: evidence,
            onEvidence: openEvidence,
            onRetry: () => select(side, sides[side].id)
          }))),
          evidence && h(Evidence, { selection: evidence, envelope: sides[evidence.side].envelope, panelRef: evidenceRef, onClose: closeEvidence }),
          comparison && h(Findings, { comparison, onPrepare: (test) => {
            setExperiment({ ...test });
            setConfirmed(false);
          } }),
          experiment && h(
            "section",
            { className: "nx-confirm nx-panel", "aria-labelledby": "nx-confirm-heading" },
            h("span", { className: "nx-eyebrow" }, "EXPLICIT LOCAL EXPERIMENT"),
            h("h3", { id: "nx-confirm-heading" }, experiment.title),
            h("p", null, "This will run on the currently connected backend only. It does not run on the imported peer."),
            h(
              "dl",
              { className: "nx-facts" },
              h("dt", null, "Exact URL"),
              h("dd", null, experiment.url),
              h("dt", null, "Connect IP override"),
              h("dd", null, experiment.connect_ip || "None — normal DNS selection")
            ),
            experiment.connect_ip && h("p", { className: "nx-caption" }, "Original hostname, Host header, and TLS SNI are preserved. This is an explicit override, not a normal-DNS success."),
            h(Field, { label: "Local experiment vantage name" }, h("input", { value: label, maxLength: 48, onChange: (event) => setLabel(event.target.value) })),
            h(
              "label",
              { className: "nx-check" },
              h("input", { type: "checkbox", checked: confirmed, onChange: (event) => setConfirmed(event.target.checked) }),
              `I confirm: run this test on this backend as “${label}”.`
            ),
            h(
              "div",
              { className: "nx-actions" },
              h(Button, {
                primary: true,
                disabled: !confirmed || Boolean(busy),
                onClick: () => runProbe(experiment.url, label, experiment.connect_ip)
              }, busy === "probe" ? "Waiting for capture…" : "Run confirmed test here"),
              h(Button, { onClick: () => setExperiment(null) }, "Cancel")
            )
          )
        ),
        h(
          "footer",
          { className: "nx-footer" },
          h("span", null, "Evidence, not a root-cause verdict."),
          h("span", null, "Point-in-time captures · one address per probe · browser trust and proxies may differ")
        )
      )
    );
  }
  function NetworkMark() {
    return h(
      "svg",
      { className: "nx-mark", viewBox: "0 0 48 48", fill: "none", "aria-hidden": true },
      h("rect", { x: 1, y: 1, width: 46, height: 46, rx: 12, stroke: "currentColor", opacity: ".3" }),
      h("path", { d: "M10 24h8l4-10 6 20 4-10h6", stroke: "currentColor", strokeWidth: 2, strokeLinejoin: "round", strokeLinecap: "round" })
    );
  }
  function Perspective({ side, state, divergence, selected, onEvidence, onRetry }) {
    const probe = state.envelope?.probe;
    return h(
      "article",
      { className: "nx-perspective", "aria-label": `${side === "left" ? "First" : "Second"} perspective ladder` },
      h(
        "header",
        { className: "nx-perspective-header" },
        h("span", { className: "nx-letter" }, side === "left" ? "A" : "B"),
        h(
          "div",
          { className: "nx-perspective-title" },
          h("h3", null, probe?.vantage.label || "Awaiting a capture"),
          h("span", { className: "nx-caption" }, probe ? timestamp(probe.captured_at) : "Choose a saved result above")
        ),
        probe && h(Badge, { tone: overall(probe) }, overall(probe))
      ),
      state.loading && h(Message, null, "Loading recorded evidence…"),
      state.error && h("div", { className: "nx-side-error" }, h(Message, { error: true }, state.error), h(Button, { onClick: onRetry }, "Retry this capture")),
      probe && h(
        "div",
        { className: "nx-probe-meta" },
        h(Badge, null, state.envelope.origin === "local" ? "Local capture" : "Imported · unauthenticated"),
        h("span", { className: "nx-caption" }, probe.vantage.platform, " · Python ", probe.vantage.python),
        h("code", { className: "nx-target" }, probe.target.url),
        h("div", { className: "nx-caption" }, "Capture: ", probe.capture.status, " · ", formatDuration(probe.capture.duration_ms)),
        probe.capture.error && h(Message, { error: true }, `${probe.capture.error.code}: ${probe.capture.error.message}`),
        h("div", { className: `nx-override${probe.target.connect_ip ? " nx-override-active" : ""}` }, probe.target.connect_ip ? `Explicit connect-IP override: ${probe.target.connect_ip} · original Host/SNI retained` : "No IP override · DNS-selected address"),
        h("div", { className: "nx-caption" }, "Direct / no proxy · single address · HEAD · TLS verified when applicable")
      ),
      h("ol", { className: "nx-stage-list" }, STAGES.map((name, index) => {
        const stage = probe?.stages.find((item) => item.name === name);
        const status = stage ? STATUS[stage.status] || STATUS.unknown : { symbol: "·", label: "No capture" };
        const isSelected = selected?.side === side && selected?.stage === name;
        return h(
          "li",
          { key: name, className: `nx-stage-item${divergence === name ? " nx-divergence" : ""}` },
          h(
            "button",
            {
              type: "button",
              className: `nx-stage nx-${stage?.status || "empty"}${isSelected ? " nx-selected" : ""}`,
              disabled: !stage,
              onClick: (event) => onEvidence(side, name, event),
              "aria-expanded": Boolean(isSelected),
              "aria-controls": stage ? "nx-evidence" : void 0,
              "aria-label": `${probe?.vantage.label || side}: ${name.toUpperCase()} ${status.label}; view evidence`
            },
            h("span", { className: "nx-stage-symbol", "aria-hidden": true }, status.symbol),
            h(
              "div",
              { className: "nx-stage-content" },
              h(
                "div",
                { className: "nx-stage-top" },
                h("strong", null, name.toUpperCase()),
                h("span", { className: "nx-stage-status" }, status.label)
              ),
              h("p", null, stage?.summary || ["Resolve the hostname", "Connect to one address", "Verify the certificate", "Read HTTP response headers"][index])
            ),
            h(
              "div",
              { className: "nx-stage-time" },
              stage ? formatDuration(stage.duration_ms) : "—",
              stage && h("span", { className: "nx-evidence-link" }, "Evidence ↗")
            )
          )
        );
      }))
    );
  }
  function Evidence({ selection, envelope, panelRef, onClose }) {
    const stage = envelope?.probe.stages.find((item) => item.name === selection.stage);
    if (!stage) return null;
    const facts = { ...stage.details, ...stage.error ? { error_code: stage.error.code, error_message: stage.error.message } : {} };
    return h(
      "section",
      {
        id: "nx-evidence",
        className: "nx-panel nx-evidence",
        ref: panelRef,
        tabIndex: -1,
        "aria-labelledby": "nx-evidence-heading",
        onKeyDown: (event) => {
          if (event.key === "Escape") onClose();
        }
      },
      h(
        "div",
        { className: "nx-section-heading" },
        h(
          "div",
          null,
          h("span", { className: "nx-eyebrow" }, "RECORDED STAGE EVIDENCE"),
          h("h3", { id: "nx-evidence-heading" }, `${stage.name.toUpperCase()} / ${envelope.probe.vantage.label}`)
        ),
        h(Button, { onClick: onClose, "aria-label": "Close stage evidence" }, "Close ×")
      ),
      h("p", null, stage.summary, " · ", STATUS[stage.status]?.label || "Unknown", " · ", formatDuration(stage.duration_ms)),
      Object.keys(facts).length ? h("dl", { className: "nx-facts" }, Object.entries(facts).flatMap(([key, value]) => [
        h("dt", { key: `${key}-key` }, key),
        h("dd", { key: `${key}-value` }, h("code", null, displayValue(value)))
      ])) : h("p", { className: "nx-caption" }, "No stage details were recorded. Skipped or unknown is not proof of failure."),
      h(
        "p",
        { className: "nx-caption" },
        "Captured ",
        timestamp(envelope.probe.captured_at),
        " · ",
        envelope.origin,
        " · Probe ",
        envelope.probe.id
      )
    );
  }
  function Findings({ comparison, onPrepare }) {
    const groups = [
      { kind: "observation", title: "What the evidence shows", subtitle: "OBSERVATIONS" },
      { kind: "hypothesis", title: "What might explain it", subtitle: "HYPOTHESES · NOT PROVEN" }
    ];
    return h(
      "div",
      { className: "nx-analysis" },
      h("div", { className: "nx-findings-grid" }, groups.map((group) => h(
        "section",
        { key: group.kind, className: "nx-finding-section" },
        h("span", { className: "nx-eyebrow" }, group.subtitle),
        h("h3", null, group.title),
        comparison.findings.some((finding) => finding.kind === group.kind) ? h("ul", null, comparison.findings.filter((finding) => finding.kind === group.kind).map((finding, index) => h(
          "li",
          { key: index },
          h("span", { className: "nx-finding-stage" }, finding.stage.toUpperCase()),
          finding.text
        ))) : h("p", { className: "nx-caption" }, group.kind === "hypothesis" ? "No specific hypothesis is supported by these captures." : "No additional observations recorded.")
      ))),
      comparison.next_tests.length > 0 && h(
        "section",
        { className: "nx-next-tests" },
        h("span", { className: "nx-eyebrow" }, "03 / TEST A HYPOTHESIS"),
        h("h3", null, "A deliberate next step"),
        comparison.next_tests.map((test, index) => h(
          "div",
          { className: "nx-next-test", key: index },
          h("div", null, h("h4", null, test.title), h("p", null, test.reason), h("p", { className: "nx-caption" }, "Local backend only · confirmation required")),
          h(Button, { onClick: () => onPrepare(test) }, "Review test →")
        ))
      ),
      h(
        "section",
        { className: "nx-limitations" },
        h("h3", null, "Limits of this comparison"),
        h("ul", null, [.../* @__PURE__ */ new Set([...comparison.limitations, ...comparison.findings.filter((item) => item.kind === "limitation").map((item) => item.text)])].map((text, index) => h("li", { key: index }, text)))
      )
    );
  }
  return App;
}

// ui/desktop-entry.js
function createNativeApi(ctx, state) {
  return {
    request: (path, options = {}) => ctx.rest(path, options),
    ownerKey: () => JSON.stringify([state.connectionId.get(), state.profile.get()]),
    subscribeOwner(callback) {
      const offConnection = state.connectionId.subscribe(callback);
      const offProfile = state.profile.subscribe(callback);
      return () => {
        offConnection();
        offProfile();
      };
    }
  };
}
var desktop_entry_default = {
  id: "network-xray",
  name: "Network X-ray",
  register(ctx) {
    const App = createApp(React, createNativeApi(ctx, host.state));
    ctx.registerMany([
      { id: "page", area: ROUTES_AREA, data: { path: "/network-xray" }, render: () => React.createElement(App) },
      { id: "nav", area: SIDEBAR_NAV_AREA, data: { path: "/network-xray", label: "Network X-ray", codicon: "pulse" } }
    ]);
  }
};
export {
  createNativeApi,
  desktop_entry_default as default
};
