# Routing contract v1.0

The authoritative machine-readable request schema is emitted by:

```sh
python scripts/route.py --schema
```

Python 3.10+; standard library only. Input is one UTF-8 JSON object, at most 2 MiB.
Unknown fields, duplicate JSON keys, non-finite numbers and invalid types are rejected.
The helper reads only the input path, writes JSON to stdout, and never executes models.
It is a planning aid, not a security enforcement service.

## Envelope

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly `1.0` |
| `host` | Host identifier and operations genuinely exposed in this session |
| `task` | Kind, natural language, intent, risk, required capabilities; optional token reserve, privacy, safe boundary, depth, current candidate |
| `policy` | Preferences and explicit permissions; omitted permissions mean none |
| `models` | Endpoint candidates from an authorized inventory, not the world's model catalog |
| `evidence` | Provenance-bearing observations for the exact model configuration and task |

No prompt, credential, raw authorization header, or tool-permission grant is accepted.
Keep the request local; do not commit personal inventory or private evaluations.

## Model records

`id` is the unique endpoint candidate identifier. `api_model_id` is the exact value
the host may pass to its provider tool. `model_key` identifies the evaluated revision
AND configuration (effort, quantization, etc.); mappings are explicit caller inputs.
Two endpoints may share one model key only when their evaluated configurations match.
Discovery reserves the `unmapped:` prefix for endpoints awaiting identity review.
Evidence carrying that prefix is ignored even if its key matches an endpoint.
An otherwise eligible unmapped endpoint prevents a complete comparison cohort.
The router returns `insufficient_evidence` until all eligible identities are covered.

Required fields: `id`, `model_key`, `provider`, `api_model_id`, `access`, `observed_at`,
`access_source`, `capabilities`, `actions`, `local`. Optional capacity fields are
`context_window` and `max_output_tokens`. Null means unknown, not unlimited.

Costs and latency are request-specific caller-supplied observations/estimates:
`estimated_cost_usd`, `cost_upper_bound_usd`, `estimated_latency_ms`.
A cost bound must include all expected billable reasoning, output, tools, retries,
and cache behavior for this request. Missing costs are NOT zero. Subscriptions are
NOT assumed free. These assertions are not provider billing guarantees; the executor
must enforce actual spending/timeout controls. Refresh them with the inventory.

For `declared` and `verified` candidates, `access_source` must identify the
independent basis for that claim. A whitespace-only source yields the exclusion reason
`access_source_missing`. The reserved `user-provided-catalog` label and
`host-catalog:` prefix yield `access_source_catalog_only` for either claim.
The bundled `synthetic-fixture` source permits recommendations only. Other
source descriptions remain caller assertions for the host to review.

The context check uses input plus output reserve. The caller must include system
instructions, tools, multimodal token accounting and reasoning reserves as applicable.

## Evidence records

Required: `source_id`, `origin_id`, `cohort_id`, `model_key`, `task`, `language`,
`metric`, `harness`, `kind`, `direction`, `value`, `observed_at`, `source_url`,
`license`, `synthetic`. Optional: `ci_lower`, `ci_upper`, `sample_size`.

Use a canonical HTTPS source URL without credentials or query parameters; put the
version/snapshot identifier in `cohort_id`. Record original evaluation/publication
date, not fetch time. `origin_id` identifies the underlying benchmark family, not
its mirrors. Correlated composites and constituent benchmarks require a curated
shared origin or explicit exclusion; this helper cannot discover hidden dependence.

A cohort fixes benchmark version, dataset split, metric/unit, date, prompting,
harness and evaluation budget. No automatic alias guessing or language fallback.
Matching a model's base name does not establish matching configuration or harness.
The caller must assess whether a benchmark harness transfers to the target host;
this release does not estimate that transfer penalty.

`kind=popularity` is ignored. Capability and preference observations remain labeled.
A sample size or confidence interval is metadata, not a guarantee of unbiased tests.
Confidence intervals must enclose the observation and have both bounds or neither.
Do not invent missing intervals, sample counts, scores, or licenses.

### Source attribution

For each reported cohort, `records` contains one scored observation per model
key. If multiple sources supplied the same observation, `additional_sources`
lists the other citations by model key, with their source IDs, URLs and stated
licenses. Repeating an identical citation adds no entry. Each distinct
publication retains the license statement supplied for it. Conflicting
statements about the same observation at the same URL produce `invalid_input`.
Check the original publication and reconcile the statements before retrying.
Mirror citations contribute no extra vote or independent origin.

## Deterministic algorithm

1. Validate the contract and unique endpoint IDs.
2. Filter access, freshness, provider allowlist, required capabilities, local-only
   privacy, context/output capacity, cost bound, and estimated latency.
3. Select evidence matching the exact task, language, and model key. Ignore stale,
   future, popularity, and non-opted-in synthetic observations.
4. Require complete comparable cohorts across ALL eligible model identities. Missing
   evidence causes abstention, not a zero score. This conservative alpha intentionally
   sacrifices coverage; curate a task-relevant inventory rather than inventing data.
5. Deduplicate mirrored origin/cohort/model records; conflicting values fail closed.
   Use one most-recent complete cohort per origin. Same-date alternatives use stable
   lexical cohort/metric/harness ordering; adapters should supply one intended metric.
6. Within each cohort, each model earns 1 for a better score, 0 for worse, and 0.5
   for a tie, against each other eligible model identity. Normalize by comparisons.
   Overlapping supplied confidence intervals are treated as a conservative tie;
   this is NOT a statistical significance test. One model receives a neutral 0.5.
7. Average these relative ranks equally over selected origins. Raw Elo, accuracy,
   and other scales are NEVER averaged directly. Relative ranks lose gap magnitude
   and depend on the candidate set; they are not calibrated quality or success rates.
8. `quality` chooses the highest rank. `balanced` and `economy` minimize known
   estimated cost among candidates within `quality_tolerance` of the best rank.
   `latency` minimizes estimated latency within that tolerance. In this alpha,
   balanced/economy share this explicit bounded-cost rule, not different learned models.
   If any shortlisted candidate lacks the needed efficiency data, fall back to quality
   with a warning. Ties prefer the current candidate, then stable candidate ID.
9. Plan only the intersection of host actions, candidate actions and authorized
   actions. Unverified access and synthetic evidence permit recommendations only.
   Subagent depth limits apply to every delegation path. Auto handoff requires a safe
   task boundary. High/critical-risk planned handoffs require approval.

## Defaults and limits

Mode: `quality`; quality tolerance: `0.05`; minimum evidence origins: `1`;
evidence age: `90` days; inventory age: `7` days; max delegation depth: `1`;
authorized actions: none; synthetic evidence: disallowed; privacy: `any`.
An omitted provider allowlist permits inventory providers; an empty list permits NONE.
These are configurable alpha defaults, not scientifically established thresholds.
Set local-only privacy and stricter freshness for sensitive work.

`max_cost_usd` requires a supplied cost upper bound. `max_latency_ms` filters an
estimate and is not an execution SLA. Risk does not establish a numerical quality
floor; high-risk correctness still needs task-specific acceptance and human review.

## Decision contract

Outputs contain `schema_version`, `engine_version`, `as_of`, `status`, `selected`,
`action`, `execution_status`, `requires_approval`, `estimated_success_probability`,
`rankings`, `excluded`, `evidence`, `ignored_evidence`, `warnings`, `reasons`.

`status` is `selected`, `needs_inventory`, `no_eligible_models`, or
`insufficient_evidence`. Invalid input produces a minimal redacted `invalid_input`
envelope. `selected` is null unless a candidate was chosen. It includes endpoint ID,
model key, provider, exact API ID and access state. `action` is a recommendation or
proposed host operation; `execution_status` is ALWAYS `not_executed` in this release.
`estimated_success_probability` is always null. No fitted probability model exists.
Rankings are quality ordered; an efficiency preference may select a different row.

Exit codes: 0 selected/schema printed; 2 abstention; 1 invalid/unreadable input.
Malformed CLI arguments use argparse's exit code 2. Default date is UTC today;
`--as-of YYYY-MM-DD` is for reproducible replay, not falsifying live freshness.

### Diagnosing insufficient evidence

For `insufficient_evidence`, inspect `evidence_coverage` before adding another source.
It counts distinct eligible model keys and lists those with no matching observation
in `missing_model_keys`. Observations must pass the task, language, identity,
freshness and source-policy filters. Duplicate endpoints for one key count once.
Keep private configuration keys out of any shared report.

If the list is empty, compare `complete_origins` with `required_origins`.
For example, one evaluation might cover models A and B while another covers
only C. All three identities have evidence, yet neither cohort compares all
three. In that case `incomplete_cohorts` is 2 and `complete_origins` is 0.
A cohort enters the count when at least one eligible observation survives.
Mirrors of the same origin cannot meet a requirement for a second origin.
Collect matching evidence for the intended inventory before retrying.
