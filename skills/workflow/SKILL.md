---
name: workflow
description: Use when the same HTTP service works on one machine but not another. Compare evidence with Network X-ray.
---

# Network X-ray

Use these tools for a specific user-requested or approved HTTP(S) endpoint, not broad discovery or scanning.

1. Confirm the exact URL and which machine the user means. `network_xray_probe` runs on THIS Hermes backend, not necessarily the desktop or phone. Choose a neutral explicit vantage label.
2. Explain that these are direct connections: proxy settings, browser cookies, authentication and browser-specific trust stores are not used. No query strings, redirects or bodies. HEAD may be handled differently from GET by a service.
3. Probe the requested endpoint. Read the actual stages, captured time and capture status; a collector timeout is inconclusive, not proof of DNS failure. Only one resolved address is connected per run.
4. For the other machine, the user runs the portable collector from the plugin's Desktop page or `hermes network-xray collector`, then imports its JSON with `network_xray_import`. Do not claim a remotely labelled local probe ran remotely. Imported bundles are recorded, unauthenticated observations; a digest checks content, not origin.
5. List saved records with `network_xray_history`. Compare exact IDs with `network_xray_compare`, for the same URL. Distinguish observations from hypotheses. Different DNS addresses or certificates can be normal CDN behaviour; neither proves an attack or root cause.
6. Offer at most one discriminating follow-up. A `connect_ip` experiment requires the user's explicit approval for that address and runs on THIS backend with the original Host/SNI and certificate verification. Never silently execute suggestions, disable TLS validation or modify DNS/firewalls/proxies to force success.
7. The Desktop Network X-ray page shows stage ladders and evidence; export is a script-free standalone HTML report. Review private IPs/URLs/headers before sharing. Do not publish private evidence without permission.

Useful commands: `hermes network-xray probe URL --label LABEL`, `hermes network-xray import peer.json`, `hermes network-xray history`, `hermes network-xray compare LEFT_ID RIGHT_ID`, and `hermes network-xray compare LEFT_ID RIGHT_ID --html`.

Failures must remain visible. Never substitute plausible-looking JSON, a synthetic test fixture or a previous healthy result for a failed probe.
