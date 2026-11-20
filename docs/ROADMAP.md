# Roadmap and acceptance criteria

## v0.1 alpha: portable foundation

Implemented in this change: installable skill folder, progressive instructions,
offline catalog import, validated request contract, constrained deterministic ranking,
explanations, synthetic example, unit/CLI tests, CI definition and contribution guidance.
Not implemented: live fetching, native host execution or calibrated predictions.

## P0: establish real interoperability

1. **Host conformance:** test installation and recommendation on at least two distinct
   hosts. Record host/version/date and pass/fail for every step in HOST-TESTS.md.
   Verify one real model-aware delegation path with user-authorized access. No paid
   probes without approval. Fall back correctly when the host cannot select models.
2. **Inventory adapters:** add host-native discovery with an explicit permission
   contract. Prove catalog-listed models cannot be upgraded to callable automatically.
   Test offline, denied, stale, rate-limited and no-model environments.
3. **Arena importer:** pin an official dataset revision, review attribution and reuse
   terms, validate schema, require explicit configuration-aware identity mapping,
   and produce normalized records without a website scraper. Golden tests must use
   permitted/synthetic fixtures and preserve confidence intervals and provenance.

## P1: useful and trustworthy comparisons

4. Add task-specialized sources (tool use, coding, language) with rights review and
   source-lineage handling. Add Artificial Analysis as optional authorized access;
   preserve OpenRouter usage as popularity, not quality. No paid dependency in core.
5. Improve partial-coverage handling with a documented, evaluated method; never silently
   impute missing scores. Add a model-identity registry with explicit mapping provenance.
6. Evaluate routing against fixed eligible-model, cheapest-eligible and user-choice
   baselines on the SAME held-out tasks. Measure accepted-task rate, total cost per
   accepted task, P95 end-to-end latency, abstention, and policy violations. Report
   uncertainty, failed runs, routing overhead, and repeated-trial conditions.

## P2: adaptive routing, only with evidence

Add calibrated success estimates only after held-out calibration checks. Consider
Pareto selection, contextual features, budget-aware exploration and source correlation
models. Keep opt-in local feedback; do not collect prompts or inventory centrally.

## Release gate

Passing unit tests alone is insufficient. Require reviewed data rights, documented
host support, live smoke tests, security review, reproducible installation, and a
versioned changelog before a stable release. No promised savings or universal support.
No fixed release date is asserted until contributors and test access are established.
