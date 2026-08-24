# Security Policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/ChuckBuilds/TECO-HA-AddOn/security/advisories/new)
rather than opening a public issue. Include what you observed, how to reproduce it,
and what an attacker could reach.

This is a personal fork maintained in spare time — expect a first response within
about a week. Issues in the upstream project belong at
[jjarboe01/TECO-HA-AddOn](https://github.com/jjarboe01/TECO-HA-AddOn).

## What this add-on handles

It logs into your utility account and keeps a local archive of your bills. Worth
knowing what that means:

- **Your TECO username and password** are stored by the Home Assistant Supervisor
  in `/data/options.json` and passed to the process as environment variables. They
  are never logged and never written to the bill cache.
- **Your billing archive** — service periods, usage, cost, meter reads, contract
  account numbers — lives in `/data/cache/` inside the add-on container and is
  included in Home Assistant backups. Treat those backups as sensitive.
- **A headless Chromium** browses `account.tecoenergy.com` as you. It runs with
  `--no-sandbox` because add-on containers run as root, where Chromium refuses to
  start otherwise; it is confined by the container and only ever navigates TECO.

## Exposure model

- **The dashboard is served over Home Assistant ingress**, which HA authenticates.
  Nothing extra is needed for normal use.
- **The API port is not published by default.** If you publish `8089` in the
  add-on's Network tab, `/data`, `/export` and `/bills` become reachable from your
  LAN — **set `auth_token` when you do**. The add-on logs a warning at startup if
  no token is set.
- Requests skip the token only when they genuinely arrive from the Supervisor
  network (`172.30.32.0/23`). The `X-Ingress-Path` header alone is not accepted as
  proof of ingress — headers are attacker-controlled. See `tests/test_auth.py`,
  which is run by CI to keep that from regressing.

## Hardening in place

| | |
|---|---|
| Ingress exemption | Bound to the Supervisor source address, not a header |
| Token comparison | `secrets.compare_digest` (constant time) |
| API port | Unpublished by default; opt-in per install |
| Interactive API docs | Disabled (`/docs`, `/redoc`, `/openapi.json`) |
| CI actions | Pinned to commit SHAs, not movable tags |
| Workflow token | `permissions: contents: read` |
| Dependencies | Bounded ranges, tracked by Dependabot |
| Secrets in git | Credentials, fixtures, caches and dumps are gitignored |

## Known limitations

- Sensor states are pushed to Home Assistant over the Supervisor API using the
  token the Supervisor injects. Any add-on with `homeassistant_api: true` has
  comparable access.
- The bill cache is not encrypted at rest. It is protected by the same boundary as
  the rest of your Home Assistant data.
