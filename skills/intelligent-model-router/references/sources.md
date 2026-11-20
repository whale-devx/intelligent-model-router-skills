# Evidence sources and data rights

Source pages reviewed 2026-11-20. This is a reference catalog, NOT an implemented
connector list. No third-party scores or datasets are bundled in this release.
A public webpage is not permission to scrape, redistribute, or use a private API.
Use official exports or authorized access only; preserve original provenance.

| Source | Potential signal | Integration / rights boundary |
| --- | --- | --- |
| [Arena](https://arena.ai/leaderboard) / [official dataset](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset) | Task-specific preference and agent evaluation | Dataset card declares CC BY 4.0; source-specific importer and attribution review pending |
| [Artificial Analysis](https://artificialanalysis.ai/api-reference) | Intelligence, price and performance observations | Official API requires an account/key and attribution; review applicable data terms before reuse |
| [Scale Labs](https://labs.scale.com/leaderboard) | Specialized coding, reasoning, agent and safety evaluations | Preserve individual benchmark version and harness; no automated connector approved here |
| [OpenRouter Rankings](https://openrouter.ai/rankings) | Usage measured by tokens processed | Context/catalog signal only; popularity MUST NOT enter quality ranking |
| [Intelligence / Design Arena](https://www.intelligence.ai/leaderboards) | Website, frontend, fullstack and other artifact categories | Check shared provenance with Design Arena and aggregators; data rights not established here |
| [Epoch AI](https://epoch.ai/benchmarks) | Benchmark observations and composite capability research | Avoid counting a composite and its constituent tests as independent evidence |
| [BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html) | Function/tool-call performance | Preserve release, category, evaluation method and cost units |
| [SWE-bench](https://www.swebench.com/) | Repository task resolution | Model plus agent/harness result; never transfer as a model-only guarantee |
| [SEA-HELM](https://leaderboard.sea-lion.ai/) | Southeast Asian language capabilities, including Thai | Preserve language, task category and evaluation configuration |
| [Terminal-Bench](https://www.tbench.ai/) | Terminal agent task resolution | Preserve version, agent harness, budget, and uncertainty |
| [LiveBench](https://livebench.ai/) | Candidate for additional benchmark coverage | Homepage is JS-rendered in this review; methodology/data-access verification remains open |

## Import checklist

Before adding a real observation, establish exact model/configuration mapping,
benchmark version/split, metric direction and units, comparable harness and budgets,
original evaluation date, uncertainty, source lineage, and access/redistribution terms.
Keep raw downloaded data outside the public repository unless its license permits it.
"License unknown" is not a redistribution grant.

Prefer task-specific evidence to overall rankings. A tool-use score is not proof of
safe authorization behavior. A Thai language score is not proof of Thai legal or
accounting accuracy. A visual preference score is not accessibility conformance.
The host should use local acceptance checks for the actual task.

## Adapter contribution contract (planned)

An adapter must expose its source version, permitted acquisition method, data-rights
review, explicit identity map, original date, and normalized records conforming to
the request schema. Include sanitized fixtures, stale-data tests, changed-schema tests,
mirror-deduplication tests, and error behavior. No implicit browser scraping, network
scan, hidden credential access, paid inference probe, or model installation.

The current skill can use evidence the host/user has already obtained and normalized.
Live fetch, refresh scheduling, cryptographic provenance, calibrated success estimates,
and automatic model-alias resolution are not implemented.
