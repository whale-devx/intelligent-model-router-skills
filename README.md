# Intelligent Model Router Skills

**Use the models you already have, more deliberately.**

A provider-neutral [Agent Skill](https://agentskills.io/specification) for choosing
models before an automatic task handoff or subagent creation. It discovers access
through the host/user, checks constraints, compares relevant evidence, and returns
an explainable routing plan. The host remains responsible for execution.

**Status: 0.1.0-alpha.1 — offline reference implementation.** Not a hosted gateway,
agent framework, live leaderboard service, or claim of universal model switching.

[ภาษาไทย](docs/README.th.md) · [Skill](skills/intelligent-model-router/SKILL.md) ·
[Contract](skills/intelligent-model-router/references/contract.md) ·
[Source guide](skills/intelligent-model-router/references/sources.md) ·
[Roadmap](docs/ROADMAP.md)

## What works now

| Capability | This alpha |
| --- | --- |
| Portable skill | Standard SKILL.md with progressive reference loading |
| Inventory discovery | Host/user protocol plus offline catalog/inventory import |
| Deterministic decisions | Validated JSON, access/privacy/capacity/budget gates |
| Multi-source evidence | Explicit provenance, exact identities, complete cohorts, origin deduplication |
| Preferences | Quality, bounded cost, latency; unknown values are never treated as free |
| Auto/subagent use | Host-aware action plans with permissions, safe boundaries and depth limits |
| No Python available | Instruction-only recommendations with the same constraints |
| Model execution / live source APIs | Not implemented; host integration is explicit and optional |

No default inference provider. No mandatory API key, server, database, telemetry, or
runtime dependency. The optional Python helpers use only the standard library.

## Install

Once this branch is merged into the default branch, an Agent Skills-compatible
installer such as the [skills CLI](https://github.com/vercel-labs/skills) can discover:

```sh
npx skills add whale-devx/intelligent-model-router-skills --skill intelligent-model-router
```

Review the installer and select your actual host. Installation alone does not grant
model switching or subagent permissions. A host's built-in Auto routing is not overridden.

For a manual install, copy the entire `skills/intelligent-model-router/` directory
into your host's documented skill location. Do not copy only SKILL.md: references,
assets, scripts, and the bundled license belong together. Do not overwrite an existing
installation without reviewing the change. No host-specific automatic installer is bundled.

## Try the offline demonstration

From a checkout, with Python 3.10+:

```sh
python skills/intelligent-model-router/scripts/route.py \
  --input skills/intelligent-model-router/assets/example-request.json \
  --as-of 2026-11-20
python -m unittest discover -s tests -v
```

The fixture uses **fictional models and synthetic scores**. It selects `example-b`
under its bounded-cost preference, but returns `action: recommend` and
`execution_status: not_executed`. Synthetic evidence can NEVER plan execution.
The fixed date makes the demonstration reproducible; live requests use UTC today.

```json
{
  "status": "selected",
  "selected": {"id": "example-b"},
  "action": "recommend",
  "execution_status": "not_executed",
  "estimated_success_probability": null
}
```

This is an abbreviated result, not a benchmark or performance claim.

## Use with your agent

> Before creating subagents, use intelligent-model-router to discover the models
> available in this host. Choose models for each actual task using permitted evidence.
> Keep the current permissions and budget. Recommend only when the host cannot delegate.

The host or user supplies a trustworthy inventory and task-matched evidence.
The helper accepts only the models in that inventory, not every model on a leaderboard.
A model appearing in a catalog remains `listed` until access and capabilities are verified.

If evidence is missing or incomparable, the helper abstains with
`insufficient_evidence`. It does not invent rankings, availability, prices or success
probabilities. See the [host protocol](skills/intelligent-model-router/references/host-protocol.md)
for the distinction between access discovery, recommendation, and actual execution.

## Architecture

```text
Host/user inventory + task constraints + permitted benchmark/local evidence
                                  |
                  Portable Skill instructions
                                  |
                Optional offline decision helper
                                  |
        Explainable recommendation / proposed host operation
                                  |
      Host revalidates permissions and performs authorized execution
```

The helper produces plans only. Native host adapters, live source importers, learned
routing, Pareto optimization, and calibrated probability estimation are future work.
No live-host integration or savings/accuracy improvement is claimed by this release.

## Development and safety

Tests cover input validation, eligibility, missing/stale evidence, source deduplication,
relative rank fusion, synthetic-data isolation, permissions, subagent depth, CLI behavior,
and copying the skill out of the repository. CI is defined for Linux/Windows and
Python 3.10/3.13; a matrix entry is supported only after its run actually succeeds.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md),
[host smoke tests](docs/HOST-TESTS.md), and [ROADMAP.md](docs/ROADMAP.md).
Keep credentials, personal model inventories and raw benchmark exports out of commits.
Store private requests under `.router-local/`, whose contents are ignored by Git.

## License and attribution

Project code and authored instructions use [Apache-2.0](LICENSE). Third-party datasets,
benchmarks and trademarks remain subject to their own terms. The source guide is not
a redistribution license. This project is not endorsed by any benchmark or model provider.
