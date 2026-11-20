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

Required fields: `id`, `model_key`, `provider`, `api_model_id`, `access`, `observed_at`,
`access_source`, `capabilities`, `actions`, `local`. Optional capacity fields are
`context_window` and `max_output_tokens`. Null means unknown, not unlimited.

Costs and latency are request-specific caller-supplied observations/estimates:
`estimated_cost_usd`, `cost_upper_bound_usd`, `estimated_latency_ms`.
A cost bound must include all expected billable reasoning, output, tools, retries,
and cache behavior for this request. Missing costs are NOT zero. Subscriptions are
NOT assumed free. These assertions are not provider billing guarantees; the executor
must enforce actual spending/timeout controls. Refresh them with the inventory.

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

For a verified selection, `reasons` explains an explicit recommendation,
retention of the current endpoint, or a missing safe boundary. When no
requested operation qualifies, it names the blockers for each operation
considered. For example, `delegate: host does not offer it.` identifies a
host capability, while `delegate: policy does not authorize it.` identifies
the request's permission limit. Automatic planning tries switch, invoke and
delegate in order. Treat reason text as explanatory prose.

Exit codes: 0 selected/schema printed; 2 abstention; 1 invalid/unreadable input.
Malformed CLI arguments use argparse's exit code 2. Default date is UTC today;
`--as-of YYYY-MM-DD` is for reproducible replay, not falsifying live freshness.
