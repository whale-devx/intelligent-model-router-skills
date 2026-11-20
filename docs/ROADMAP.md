# Roadmap and acceptance criteria

[Project home](../README.md) · [Documentation](README.md) · [Host tests](HOST-TESTS.md)

**Current focus: P0 — prove real interoperability.** Installation verification is
implemented. Opt-in model-list adapters now have protocol/fixture tests; live account
access, host activation and a real authorized handoff still need separate evidence.

| Milestone | Status | What must be demonstrated |
| --- | --- | --- |
| v0.1 alpha — portable foundation | Implemented offline | Skill package, validated decisions, explanations, tests |
| P0 — real interoperability | In progress | Host-account inventory, live conformance, licensed Arena import |
| P1 — useful comparisons | Planned | Specialized evidence and same-task routing evaluations |
| P2 — adaptive routing | Evidence-gated | Calibrated estimates and opt-in local feedback |

## v0.1 alpha: portable foundation

- [x] Installable skill folder and progressively loaded instructions.
- [x] Offline catalog import and validated request contract.
- [x] Constrained deterministic ranking and explanations.
- [x] Labeled synthetic example, unit/CLI tests, and CI definition.
- [x] Contribution and security guidance.

The router remains offline. Optional discovery is separate from ranking and execution.
No native model executor, live benchmark importer, or calibrated prediction exists yet.

## P0: establish real interoperability

### 1. Host conformance

- [x] Add reproducible `npx skills` installation/package checks; see [installation evidence](INSTALLATION-TESTS.md).
- [ ] Test activation and recommendation on at least two distinct live hosts.
- [ ] Record host/version/date and pass/fail for every step in [HOST-TESTS.md](HOST-TESTS.md).
- [ ] Verify one real model-aware delegation path with user-authorized access.
- [ ] Verify recommendation fallback on a live host that cannot select models.

No paid probes without approval. Installation success and confirmed execution must
be recorded separately. Directory targets in installer tests are not running hosts.

### 2. Inventory adapters

- [x] Add opt-in listing adapters and an [explicit permission contract](../skills/intelligent-model-router/references/live-discovery.md).
- [x] Keep catalog-listed models ineligible for execution; add router-contract regression checks.
- [x] Add synthetic/loopback tests for offline snapshots, denied access, stale data, rate limits, and no models.
- [ ] Validate the OpenCode experimental v2 contract on a real authorized host/version.
- [ ] Record a real Ollama inventory without assuming local inference or tool support.
- [ ] Add trusted access-verification and exact benchmark-identity mapping evidence.

The new helpers can make real HTTP listing requests when authorized. Tests use fixture
servers, not user accounts. A successful list is not proof of callability. Other hosts
retain host-tool/manual discovery; no provider is mandatory.

### 3. Arena importer

- [ ] Pin an official dataset revision and review attribution/reuse terms.
- [ ] Validate the source schema and require configuration-aware identity mapping.
- [ ] Produce normalized records without a website scraper.
- [ ] Preserve confidence intervals and provenance in permitted/synthetic golden tests.

## P1: useful and trustworthy comparisons

### 4. Task-specialized evidence

- [ ] Add tool-use, coding, and language sources with rights review and source lineage.
- [ ] Add Artificial Analysis as optional authorized access.
- [ ] Preserve OpenRouter usage as popularity, not quality; keep core free of paid dependencies.

### 5. Partial coverage and identity

- [ ] Evaluate a documented method for partial evidence coverage without silent imputation.
- [ ] Add a model-identity registry with explicit mapping provenance.

### 6. Evaluate the router itself

- [ ] Compare fixed eligible-model, cheapest-eligible, and user-choice baselines on the **same held-out tasks**.
- [ ] Measure accepted-task rate, total cost per accepted task, P95 end-to-end latency, abstention, and policy violations.
- [ ] Report uncertainty, failed runs, routing overhead, and repeated-trial conditions.

## P2: adaptive routing, only with evidence

- [ ] Add calibrated success estimates only after held-out calibration checks.
- [ ] Consider Pareto selection, contextual features, budget-aware exploration, and source-correlation models.
- [ ] Keep feedback opt-in and local; do not collect prompts or inventory centrally.

## Release gate

> [!IMPORTANT]
> Passing unit tests alone is insufficient for a stable release. Compatibility,
> data rights, security, and reproducible installation need separate evidence.

- [ ] Reviewed data rights.
- [ ] Documented host support and live smoke tests.
- [ ] Security review.
- [ ] Reproducible release installation.
- [ ] Versioned changelog.

No promised savings or universal support. No fixed release date is asserted until
contributors and test access are established.

[Contribute to a milestone](../CONTRIBUTING.md) · [Report a host test](https://github.com/whale-devx/intelligent-model-router-skills/issues/new/choose)
