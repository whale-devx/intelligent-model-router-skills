# Import Arena English text preference evidence

The optional adapter accepts the original local Parquet file for the English category
of Arena's raw text leaderboard. Other categories have different populations or
unknown language. Its task label is exactly `text` and language `en`. Retain that
scope when constructing the request. The rating measures comparative preference.

With authorization, obtain the [original pinned snapshot](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/blob/d3517dc2bbc13f82d925d8524f9c5cb5e4563d36/text/latest-00000-of-00001.parquet).
The adapter checks its exact SHA-256 before decoding. Each new upstream revision
requires a reviewed pin, schema and methodology check. No fetch mode is provided.

Install the optional Parquet reader in a separate environment and run from the skill folder:

~~~sh
python -m pip install pyarrow==22.0.0
python scripts/adapters/arena.py latest-00000-of-00001.parquet mappings.json --request request.json
~~~

Start with an empty JSON array in mappings.json. Each entry is a caller-reviewed
attestation of configuration equivalence. Example using fictional identifiers:

~~~json
[{"organization":"Example","model_name":"Example (High)","host_id":"my-host",
  "endpoint_id":"endpoint-1","provider":"example","api_model_id":"example-v2",
  "configuration":"revision v2, high reasoning","model_key":"example/v2@high"}]
~~~

Supply the [v1 routing request](contract.md) you intend to use, including its
reviewed inventory. The importer compares the host ID, endpoint ID, provider,
API model ID and configuration-specific `model_key` for every mapping. It also
looks for the exact organization and model label among the English observations
in the pinned snapshot. A mismatch exits with an error before printing evidence.
An empty mapping array is valid for inspecting coverage.

If two endpoints serve an independently confirmed equivalent configuration,
supply one mapping per endpoint with the same Arena identity, configuration
description and model key. Both endpoints appear in lineage and the observation
counts once. Every endpoint in this request sharing that key must be covered.
Other model keys may remain unmapped.

Record the source of the revision and settings when reviewing equivalence.
The request check verifies identifiers. Reasoning effort, quantization,
benchmark equivalence and current host access still need independent evidence.
Leave uncertain mappings out. Discovery keys beginning with `unmapped:` are
reserved. Keep the report local because it contains endpoint identifiers.

`request_identity_check` is `matched` when the supplied mappings pass both
checks, or `no_mappings` for an empty mapping file with a request.
Omitting `--request` preserves the standalone import mode and reports `not_run`.
`unmatched_mappings` counts distinct mapping identities missing from the
English snapshot. `unmapped` counts English source rows lacking a mapping.

### Reviewing a thinking budget

The pinned English snapshot lists two Anthropic entries for Sonnet 4.5 dated
20250929. One is labeled `High, 32K`. OpenCode v1.19.6's fallback for manual
thinking on its Anthropic SDK caps the `high` variant at 16,000 tokens and
can reduce that budget further for a smaller output limit. [Arena snapshot](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/blob/d3517dc2bbc13f82d925d8524f9c5cb5e4563d36/text/latest-00000-of-00001.parquet) · [OpenCode variant implementation](https://github.com/anomalyco/opencode/blob/f4e363c8295fa90a03dddc451882fffe8fbce357/packages/opencode/src/provider/transform.ts#L1045-L1091)

Two offline listings with the same model and `high` variant but different
request budgets (16,000 and 32,000) produced identical discovery reports.
The adapter retains variant IDs and omits request bodies. Leave the mapping
out until deployment evidence identifies the active settings and the benchmark
evidence supports the same configuration. [Discovery contract](live-discovery.md)

### Attribution and sharing

The JSON report includes request-compatible evidence, corresponding lineage in
the same order, source revision, checksum and excluded-row counts. Original
publication dates drive the router's freshness filter. Null bounds and counts
remain unknown. Detailed harness/version information is unavailable.

## Credit the source when sharing adapted scores

If you share adapted Arena scores, include the report's `source_notice`.
It names Arena, links to the pinned dataset card, source file and license,
and describes the English filter and field normalization. Add a description
of any further changes you make. To extract the notice from a saved import,
run this command in the directory containing `arena-report.json`.

~~~sh
python -c "import json; from pathlib import Path; print(json.loads(Path('arena-report.json').read_bytes())['source_notice'])"
~~~

The notice contains public source information. Keep the full report local
because `lineage` includes your configuration and endpoint identifiers.
Older reports can be regenerated from the pinned snapshot and the original
mapping file. [Arena's pinned dataset card](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/blob/d3517dc2bbc13f82d925d8524f9c5cb5e4563d36/README.md) · [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/)

The installable skill carries the project's Apache-2.0 license. Its sample
request contains synthetic observations, and its inventory template starts
empty. The Parquet file is a separate input supplied by the caller. In that
file the `license` column describes each model. The dataset card supplies
the license for the leaderboard observations. When adding another source
or replacing the pin, review the new source's terms and attribution.
