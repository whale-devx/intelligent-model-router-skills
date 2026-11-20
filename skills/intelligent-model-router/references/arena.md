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

The JSON report includes request-compatible evidence, corresponding lineage in
the same order, source revision, checksum and excluded-row counts. Original
publication dates drive the router's freshness filter. Null bounds and counts
remain unknown. Detailed harness/version information is unavailable. Attribution
for adapted scores: Arena, [Leaderboard Dataset and pinned metadata](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/blob/d3517dc2bbc13f82d925d8524f9c5cb5e4563d36/README.md),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Indicate that the
English subset was filtered and its fields normalized when sharing results.
The model license column describes the model separately.
