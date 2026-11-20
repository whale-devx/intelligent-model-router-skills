# Discovery and host protocol

## Three facts, not one

`catalog-listed` means a name appears in a response. `entitled` means the user's
account/policy permits access. `callable` means the particular host and endpoint
can execute the requested operation. Do not infer the latter two from the first.
Subscription access and API credentials are distinct access mechanisms; use only
the current host's documented entitlement path. No credential extraction.

## Capability negotiation

Ask the current host for its exposed model inventory and actual operations. The
portable vocabulary is `recommend`, `delegate`, `switch`, `invoke`. These are
contract labels, NOT names of universally available tools. Map them only to tools
present in the current session and validate each tool's schema before use.

Inventory precedence: authorized host-native inventory, explicitly authorized
provider inventory, user-selected local runtime inventory, then manual declaration.
Do not probe localhost, scan the network, read authentication files, or spawn a new
CLI to impersonate another subscription. A missing discovery API is not permission
to bypass the host.

`verified` must have an access source and observation date supported by host/account
information or a previously authorized successful call. It is a caller assertion,
not cryptographic proof; the receiving host must verify it again before execution.
`declared` is sufficient for a qualified recommendation only. `listed`, `unknown`,
and `unavailable` are ineligible. The default inventory validity window is 7 days;
a host can require much fresher data. A stale entry must not be silently refreshed.

## Offline catalog import

The helper consumes a file that the user or an authorized host already obtained.
It makes no network calls and preserves no credentials from the catalog.

```sh
python scripts/discover.py --input catalog.json --format openai-list --provider example --observed-at 2026-11-20
python scripts/discover.py --input tags.json --format ollama-tags --provider local --observed-at 2026-11-20
python scripts/discover.py --input inventory.json --format inventory
```

Paths above are relative to this skill directory. `openai-list` accepts
`{"data":[{"id":"example-model"}]}`. `ollama-tags` accepts
`{"models":[{"name":"example-model:tag"}]}`. An inventory is `{"models":[...]}`
using the request's model schema. Copy its `models` array into a full request.

Imported catalogs set access to `listed`, capabilities to an empty array, and the
benchmark identity to `unmapped:...`. This is intentionally NOT a ready-to-route
inventory. Fill verified capability/identity/access details from trustworthy sources.
The observation date must reflect the original observation, not a fabricated refresh.

## Subagent handoff

Before creating a subagent, record its goal, input summary, allowed tools, output
contract, budget, maximum depth, and acceptance checks in the host's own mechanism.
The routing request does not carry private prompts or grant tools. Only the host
may transfer the actual task. Check model selection really affects that subagent;
otherwise disclose model inheritance and return a recommendation.

For automatic task routing, set `safe_boundary` only after outstanding tools finish
and state can be transferred safely. Never reset context silently or replay a side
effect. `delegate` has a depth limit in both auto and subagent modes.

## Compatibility evidence (documentation reviewed 2026-11-20)

| Surface | Documented integration basis | This repository's validation |
| --- | --- | --- |
| Agent Skills format | Portable SKILL.md plus optional scripts/references | Manifest and standalone folder tests |
| Claude Code | Skill loading and configurable subagent models | Documentation reviewed; no live-host test yet |
| OpenAI skill surfaces | OpenAI's skill authoring documentation | Documentation reviewed; no live-host test yet |
| Other hosts | Must support the skill format or accept its instructions | No host-specific support claim |

Primary references: [Agent Skills](https://agentskills.io/specification),
[Claude Code skills](https://code.claude.com/docs/en/skills),
[Claude Code subagents](https://code.claude.com/docs/en/sub-agents),
[OpenAI skill authoring](https://developers.openai.com/codex/skills).
Reading documentation is not an integration test. Add dated, reproducible host/version
smoke-test records before declaring any host fully supported.
