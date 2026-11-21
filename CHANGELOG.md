# Changelog

## Unreleased

- Explain evidence-related abstention with the missing model keys and the
  number of independent origins covering the eligible inventory.

- Include a copyable Arena attribution notice in normalized reports. It links
  to the pinned dataset and license and describes the import transformation.

- Ignore benchmark rows keyed to discovery placeholders. Arena imports can check
  each mapped endpoint against a local routing request and retain shared
  configuration lineage without counting an observation twice.
- Read the provider model ID from OpenCode v1.19.6 model records and represent
  their zero token limits as unknown.

- Add opt-in, read-only OpenCode experimental v2 model-list and Ollama tags adapters.
- Require explicit local-service authorization; support offline snapshots with original
  observation dates, bounded requests, redacted failures and exact identity fields.
- Keep discovered models listed/unmapped and recommendation-only; do not infer model
  entitlement, execution permission, benchmark configuration, or free pricing.
- Fix the older Ollama catalog importer: a local endpoint no longer implies local
  inference. `local` now remains unknown unless separately established by the caller.
- Add synthetic protocol, loopback HTTP, CLI and router-contract regression tests.
- Preserve the offline router, provider neutrality and optional-script installation.
- Require the original observation date when importing raw catalogs with
  `discover.py`. Normalized inventories retain their per-model dates.
- Exclude access claims backed only by catalog provenance. The bundled demo
  inventory remains recommendation-only even with other benchmark inputs.

No live-host activation, paid inference, model switching, subagent creation, release
publication or universal host compatibility is certified by this change.

## 0.1.0-alpha.1 (proposed)

- Add a provider-neutral Agent Skill for task routing and subagent model selection.
- Add offline catalog import and deterministic routing plans with strict input validation.
- Preserve source origin, cohort, language, metric, configuration and uncertainty metadata.
- Enforce access, privacy, capacity, budget and host-action planning constraints.
- Add synthetic examples, regression tests, CI definition, English/Thai documentation.
- Keep execution, live source integrations and calibrated predictions out of alpha scope.

This heading is not a published package, Git tag, or verified host-support claim.
