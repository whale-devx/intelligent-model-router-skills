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
python scripts/adapters/arena.py latest-00000-of-00001.parquet mappings.json
~~~

Start with an empty JSON array in mappings.json. Each entry is a caller-reviewed
attestation of configuration equivalence. Example using fictional identifiers:

~~~json
[{"organization":"Example","model_name":"Example (High)","host_id":"my-host",
  "endpoint_id":"endpoint-1","provider":"example","api_model_id":"example-v2",
  "configuration":"revision v2, high reasoning","model_key":"example/v2@high"}]
~~~

Verify every mapping against the current host and inventory before adding its
evidence to a request. A configuration-specific model_key is the router's join
key. Keep distinct revisions and reasoning settings separate. Do not map a row
if its configuration is uncertain. The mapping neither creates inventory nor
confirms access. The report contains local endpoint IDs; keep it private.

The JSON report includes request-compatible evidence, corresponding lineage in
the same order, source revision, checksum and excluded-row counts. Original
publication dates drive the router's freshness filter. Null bounds and counts
remain unknown. Detailed harness/version information is unavailable. Attribution
for adapted scores: Arena, [Leaderboard Dataset and pinned metadata](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/blob/d3517dc2bbc13f82d925d8524f9c5cb5e4563d36/README.md),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Indicate that the
English subset was filtered and its fields normalized when sharing results.
The model license column describes the model separately.
