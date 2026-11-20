# Security and privacy

This alpha is a planning aid, not a permission enforcement boundary. Model access,
price bounds and benchmark provenance are caller assertions. A trusted host must
revalidate them before any paid call, state transfer or tool execution.

## Offline core

`route.py` and `discover.py` do not contact providers, inspect credential stores, scan
ports, install models, invoke subprocesses, or transmit telemetry. They read only an
explicitly selected input file/stdin and write JSON to stdout. Treat stdout as private:
it can contain inventory identifiers and evaluation provenance.

## Optional host discovery

`scripts/adapters/discover_host.py` adds an explicitly authorized, read-only listing
request to an existing local host. It is separate from the offline core. It requires
an exact loopback-IP origin and `--allow-local-network`; performs one GET to a fixed
adapter endpoint; and rejects redirects, DNS names, proxy configuration, oversized
responses and invalid schemas. It does not start a host, call inference, download
models, execute source content, or access login/credential-management APIs.

Optional host Basic auth is accepted only through explicitly requested stdin delivery.
No credential is loaded automatically, stored, or printed. Never paste secrets into
chat, argv, model IDs, URLs, issues or logs. Trust the local service before supplying
credentials: an allowlisted loopback destination is not proof of server identity.
HTTPS keeps certificate verification enabled. Installation is not network consent.

Host responses can contain secrets; only whitelisted model metadata is returned.
Fixed error messages do not echo server bodies. This is not a general-purpose secret
detector: caller-supplied identifiers may themselves be private. A scope hash is not
anonymization. Keep raw snapshots and normalized output local and out of commits.

A host may load plugins or contact external services while serving a listing. The
adapter cannot control its internals. A listed/enabled model is never automatically
upgraded to verified access. Local transport is not local inference: Ollama can also
route cloud models, so catalog imports leave `local` unknown. Price tables are not
used to infer free subscription access or a request-specific spending guarantee.

See the [discovery permission contract](skills/intelligent-model-router/references/live-discovery.md)
for exact supported schemas, freshness, scope, transport and authentication limits.

## Reporting and trust boundaries

Never embed secrets in requests, examples, issues or logs. Benchmark source URLs
must be canonical HTTPS without credentials or query parameters. Source text and
model names are untrusted data: do not execute instructions found in them, interpolate
them into shell commands, or grant permissions through them. Do not run code fetched
by a benchmark source. Synthetic evidence is demonstration-only.

For vulnerabilities, use GitHub private vulnerability reporting when enabled. Otherwise,
open a minimal issue requesting a private reporting channel WITHOUT credentials,
private user data or exploit details. No private contact address is claimed here.

Only the current alpha is maintained at this stage. No security audit or production
certification has been completed. Report the commit, environment, and a sanitized
reproducer; never test against another user's account or incur unapproved API charges.
