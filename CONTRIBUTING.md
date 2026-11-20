# Contributing

Small, evidence-backed changes are welcome. Open an issue describing the problem,
expected behavior, and reproducible acceptance tests before adding a large integration.
Keep the project a portable skill: no mandatory provider, gateway, server, or API key.

Run `python -m unittest discover -s tests -v` and the documented offline example.
Keep runtime dependencies at zero unless a separately optional adapter needs them.
Preserve the public request schema and report breaking changes explicitly.

For source adapters, include acquisition permission, attribution/redistribution review,
source revision, sanitized fixtures, identity-mapping tests and provenance/deduplication.
For host adapters, include host version, supported operations, exact permission behavior,
and reproducible smoke-test evidence. Documentation review is not an integration test.
Never commit credentials, private prompts, account inventories or unlicensed datasets.

Distinguish synthetic fixtures, local measurements and published benchmarks. Do not add
performance badges or savings claims without a reproducible experiment and baselines.
Use English for primary technical docs; translations are welcome with synchronized terms.

By submitting contributions you agree they may be distributed under this project's
Apache-2.0 license and confirm you have the right to submit them.
