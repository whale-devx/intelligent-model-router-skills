# Authorized host model discovery

[Skill instructions](../SKILL.md) · [Host protocol](host-protocol.md) · [Routing contract](contract.md)

**An opt-in adapter, not a new provider or a model executor.** Prefer the current
host's exposed model-list tool. This optional Python 3.10+ standard-library helper
can read a specific, already-running local service after explicit authorization.
It never starts a host, scans ports, reads credential stores, or calls inference.

## Supported contracts

| Adapter | Single GET | Contract boundary |
| --- | --- | --- |
| `opencode-v2` | `/api/model` | OpenCode's experimental location/data model-list envelope; enabled chat models only |
| `ollama` | `/api/tags` | Ollama's model-list response; does not attest local inference, tools or context |

OpenCode's older `/provider` and `/config/providers` APIs are **not** interchangeable
with this adapter. Select the adapter explicitly; there is no version guessing or
fallback probing. A 404 or changed schema is a reported failure, not an empty success.
This adapter's protocol is source-reviewed and fixture-tested; that is not proof of
compatibility with every OpenCode release or a live authenticated user account.

The schema shipped in OpenCode v1.19.6 places the underlying model ID in
`api.id` for the `native` and `aisdk` variants. Its empty model uses zero
context and output limits. The adapter reports those capacities as unknown.
The release schema and route were checked against upstream source and tested
with local fixtures. [Release model schema](https://github.com/anomalyco/opencode/blob/f4e363c8295fa90a03dddc451882fffe8fbce357/packages/schema/src/model.ts) · [Release route](https://github.com/anomalyco/opencode/blob/f4e363c8295fa90a03dddc451882fffe8fbce357/packages/protocol/src/groups/model.ts)

The other supported OpenCode schema was reviewed at upstream commit
`b958fc84d73e34a2fa021c285cd38c6de674adb9` on 2026-11-20:
[route](https://github.com/anomalyco/opencode/blob/b958fc84d73e34a2fa021c285cd38c6de674adb9/packages/protocol/src/groups/model.ts),
[model schema](https://github.com/anomalyco/opencode/blob/b958fc84d73e34a2fa021c285cd38c6de674adb9/packages/schema/src/model.ts),
[location envelope](https://github.com/anomalyco/opencode/blob/b958fc84d73e34a2fa021c285cd38c6de674adb9/packages/schema/src/location.ts).
The [official API reference](https://opencode.ai/docs/api) calls this route experimental
and notes that the snapshot can precede plugin settlement.
Ollama's [list API](https://docs.ollama.com/api/tags) and
[cloud documentation](https://docs.ollama.com/cloud) explain why a local endpoint
must not be treated as proof that inference stays on the machine.

## Permission contract

The host/user must authorize the exact local service and project scope before the
agent runs this helper. `--allow-local-network` records that intent; it is not a
security boundary or proof that consent was obtained. Never add it silently to make
an error disappear. Installation does not authorize network discovery.

Only explicit `http(s)://127.0.0.1:PORT` and `http(s)://[::1]:PORT` origins are
accepted. No default endpoint, DNS names (including `localhost`), userinfo, arbitrary
paths, query strings, proxies, redirect following, retry or TLS-verification bypass.
The helper performs one GET to the adapter's fixed path. The timeout is 5 seconds by
default, bounded to 30 seconds, and the response limit is 2 MiB. Narrow provider/model
filters if the normalized inventory would exceed 256 candidates; no silent truncation.

A loopback service remains a trust boundary: an existing host may initialize plugins
or contact external catalog services while handling a listing. The helper cannot
control the host's internal activity. Do not use it on an untrusted service.

## Use an existing local host

Resolve `<skill-directory>` from your host's installed skill location. Replace the
example port with the port of the host you actually authorized; do not scan for it.
Keep private output out of Git, public issues, and prompts sent to benchmark sites.

```sh
python <skill-directory>/scripts/adapters/discover_host.py --adapter opencode-v2 --instance-id work-project --base-url http://127.0.0.1:4096 --allow-local-network
```

Optional `--provider <exact-id>` and `--model <exact-host-model-id>` filters are
repeatable. `--expected-directory <exact-directory>` rejects an OpenCode response
for a different scope. This version reads the server's default location; it does not
change locations or send directory-selection queries. The report contains only a
scope hash, not the returned directory. A hash is an identifier, not anonymization.
Use distinct non-secret instance labels for different hosts/projects.

For an existing Ollama service:

```sh
python <skill-directory>/scripts/adapters/discover_host.py --adapter ollama --instance-id local-runtime --base-url http://127.0.0.1:11434 --allow-local-network
```

If the local host requires HTTP Basic auth, `--auth-stdin` accepts exactly a JSON
object with `username` and `password` from an approved host-side pipe. There is no
password argument, environment scan, credential-file lookup, login, or authorization
endpoint call. Do not paste credentials into chat or commands. Without approved
credential delivery, use snapshot mode instead. No host credentials are persisted
or included in output. Authentication is optional and limited to the approved local
origin; it does not authenticate directly to a model provider.

## Offline snapshots

The same normalizers accept an explicit authorized response saved locally. Supply
its **original observation date**, not today's date just because it was imported.
Snapshots older than seven days (configurable with `--max-age-days`) or future-dated
snapshots fail with `stale_snapshot`. Live mode uses UTC today and forbids overriding
that observation date. Neither date proves when the host's internal catalog updated.

```sh
python <skill-directory>/scripts/adapters/discover_host.py --adapter opencode-v2 --instance-id work-project --input <private-listing.json> --observed-at YYYY-MM-DD
```

Use `--input -` for stdin. Snapshot mode never opens a connection. A listing can
contain private settings: do not commit the raw file. Only a whitelist of model
identifiers, typed capabilities, limits, variant IDs and revision hints is retained.
Headers, bodies, settings, credentials and price tables are discarded.

## Interpret the report

| Field | Meaning |
| --- | --- |
| `status` | `discovered`, `no_models`, or a bounded error code |
| `inventory.models` | Records compatible with the router's existing `models` contract |
| `observations` | Exact host/provider IDs, variant IDs or Ollama digest/quantization hints; not benchmark mappings |
| `observed_at` | Listing observation date, not successful inference or verified entitlement |
| `host_version` | `null`; this helper does not probe a version endpoint |
| `scope_sha256` | OpenCode directory fingerprint; no raw directory is copied |
| `source_mode` | `live` or `snapshot` |
| `skipped` | Counts of disabled, deprecated, non-chat or explicitly filtered models |
| `execution_status` | Always `not_executed` |

Every discovered model stays **`access: listed`**, **`actions: [recommend]`**,
**`model_key: unmapped:...`** and **`local: null`**. It is intentionally not yet eligible
for routing execution. Do not edit these labels merely to force a chosen result.
`discovered` means a catalog was read, not that the account can invoke every row.
A connected provider, enabled model, zero price, or HTTP 200 does not prove callability.

For OpenCode, `api_model_id` is the exact **host model ID** (`id`), while the separate
`observations.provider_model_id` preserves `api.id` or `modelID` for the underlying provider.
These can differ from the host ID. A row containing both provider forms must agree
on the ID. No alias, API ID, reasoning effort, or quantization is guessed.
Variants are listed but not selected or expanded into supposedly evaluated models.
Capabilities and limits are host-reported assertions, not independent measurements.
If a separate input limit is smaller than context, the routing context ceiling is
conservatively capped at that input limit; no output allowance is invented.

For Ollama, `/api/tags` alone does not provide dependable context/tool metadata, so
these stay unknown. Both this helper and the older offline catalog importer now leave
`local` unknown. The previous `ollama-tags => local: true` inference was unsafe for
cloud-backed models.

## Feed an authorized inventory into routing

Keep the original report. A trusted host/user must establish access, exact benchmark
configuration identity, required capabilities and execution permissions separately.
Then use the reviewed `inventory.models` in the request described by the
[routing contract](contract.md). Do not pass the entire discovery report as a routing
request. Listing-only records are rejected by existing access gates, by design.

Source refresh is not a paid probe. A later verification adapter needs its own
permission contract and an execution receipt. This change does not include that
adapter, live leaderboard ingestion, subagent creation, or automatic model switching.

## Failures and tests

No partial inventory is emitted on malformed responses. Errors contain fixed messages,
not source bodies or paths. They distinguish access denial, rate limiting, unsupported
API, refused redirects, oversized data, invalid schema, stale snapshots, wrong scope,
timeout, and unavailable hosts. No failure silently starts a host or tries another
provider. Exit code 0 means listing success (including no models), 2 means an expected
permission/availability/freshness barrier, and 1 means invalid input/protocol. Argument
parsing errors use argparse's exit code 2.

Tests use synthetic source rows and real HTTP requests to **fixture servers** on
loopback, including credentials used only for the test. They are not live OpenCode or
Ollama account tests. Keep installation, protocol correctness, live model discovery,
model activation and delegation evidence separate.
