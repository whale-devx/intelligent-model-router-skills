# Installation verification

[Project home](../README.md) · [Getting started](GETTING-STARTED.md) · [Live host checklist](HOST-TESTS.md)

Installation is one part of P0, not proof of model access, host activation, or delegation.
The **Skill installation** workflow provides a repeatable package/installer check.
Use a completed run's artifacts for results; the existence of this workflow is not a pass.

## What is exercised

| Layer | Actual check | What it does not prove |
| --- | --- | --- |
| Package | YAML fields, required files, local file links, bundled license | Complete Markdown validation or a security audit |
| Installer discovery | Pinned Skills CLI finds the named skill | A live AI host discovers or activates it |
| Installation | Codex and Claude Code *target directories*, project/global scope, default/copy methods | These hosts were launched, authenticated, or tested |
| Public source | Install from an exact public GitHub commit as well as a local checkout | Private-repository authentication |
| Integrity | Every delivered file matches a source SHA-256 manifest after LF normalization | An independently signed release or the CLI's own lockfile hash |
| Installed helpers | Run the synthetic routing example and empty-inventory import outside the repository | Real rankings, model discovery, model calls, or subagent creation |

The full matrix is 2 operating systems × 2 source modes × 2 installer targets ×
2 scopes × 2 methods = **32 installation cases**. Package tests additionally run on
Python 3.10 and 3.13. Each case independently checks install, listing, complete file
integrity, and execution of both installed offline helpers. Default mode lets the
installer choose its normal link/copy behavior; the report records the resulting
file type rather than asserting Windows symlink privileges.

## Reproduce

Development dependencies are separate from the installed skill. The skill's
`SKILL.md`, runtime helpers, and zero-required-inference-account behavior are unchanged.

```sh
python -m pip install -r tools/requirements-test.txt
python -m unittest discover -s tools/tests -v
python tools/validate_package.py skills/intelligent-model-router --expected-license LICENSE
python tools/install_smoke.py --source local
```

The integration check needs Node.js **22.20.0 or later**, npm/npx, Git, Python 3.10+,
and public access to npm and GitHub. It uses the real npx JavaScript entrypoint
(`npx --yes skills@1.9.0 ...`), including on Windows, without a shell interpolating
arguments. The default report is `.router-local/install-smoke.json` (gitignored).
The ordinary user installation remains:

```sh
npx skills add whale-devx/intelligent-model-router-skills --skill intelligent-model-router
```

For the public-source test, use the exact 40-character commit returned by
`git rev-parse HEAD`, which must already exist in the public repository:

```sh
python tools/install_smoke.py --source github --ref <full-public-commit-sha>
```

The source URL is pinned to that commit's skill directory. CI uses the PR head's
repository and SHA (or the push SHA), not a floating `main` branch. Local changes
that have not been pushed will correctly cause a public-source manifest mismatch.

## Isolation and privacy

Each case gets its own temporary home and project. The child-process environment is
built from an OS-path allowlist, not copied wholesale. HOME, USERPROFILE, XDG paths,
Codex/Claude config locations, npm cache/config, and temp paths point into the test
area. Provider/API keys, GitHub tokens, proxies, NODE_OPTIONS and PYTHONPATH are not
inherited. Git credential configuration is not reused. Installer telemetry/audit
requests are disabled with `DISABLE_TELEMETRY=1` and `DO_NOT_TRACK=1`; npm lifecycle
scripts, audit and funding requests are disabled as well.

This is **configuration isolation, not an operating-system sandbox**. The installer
is third-party executable code. Prefer a disposable CI runner; inspect the pinned
installer before running it locally. Explicit network access to public npm/GitHub is
necessary. The checks do not launch an AI host, make paid inference calls, enumerate
accounts, or invoke the actual user's available models.

Reports contain only the public package's paths/digests, installer outputs, synthetic
fixture results, tool versions, and timestamps. Do not add real inventory or secrets
to this test. npm's downloaded CLI version and reported package integrity are recorded.
The top-level version is pinned; transitive npm dependencies and upstream runners
are **not fully locked**, so this is repeatable verification, not a hermetic build.

## Project-specific validation rules

The validator uses safe YAML and rejects duplicate keys. It checks the Agent Skills
name/description/compatibility/metadata types and limits, directory/name alignment,
and this project's required files and Apache-2.0 declaration. Additional packaging
rules reject YAML aliases, nested symlinks, hidden/credential-like filenames, files
larger than 2 MiB, and packages exceeding 256 files. These are **project rules**, not
claims that the Agent Skills standard universally prohibits those features.

Inline Markdown file links are checked for existing, contained targets. External
URLs are not fetched, fragments are not validated, and this is not a full Markdown
parser. Runtime `__pycache__` is excluded from manifests; every other deliverable
file is compared. The manifest is not a substitute for provenance or code review.

## Reading evidence and failures

Open the workflow for the exact commit. Four installer artifacts (OS × source mode)
record eight case outcomes each, executed commands and return codes, version metadata,
source file digests, and any error. A successful process alone is insufficient: missing
files, changed contents, absent listing, or an unexpected synthetic decision fail the
case. Network or package-registry failure fails the job; it is not silently skipped.

`host_activation`, `model_discovery`, and `delegation` remain `not_tested` in these
reports. Record those separately using [HOST-TESTS.md](HOST-TESTS.md), with real host
versions and permission-aware receipts. Do not check off the combined live-host P0
gate based on this installer workflow.

## Primary references

- [Agent Skills specification](https://agentskills.io/specification).
- [Skills CLI commands](https://github.com/vercel-labs/skills/blob/main/docs/commands.md).
- [Installer target paths](https://github.com/vercel-labs/skills/blob/main/docs/agents.md).
- [Installer telemetry controls](https://github.com/vercel-labs/skills/blob/main/docs/troubleshooting.md#telemetry).

เอกสารนี้ยืนยันได้เฉพาะการตรวจแพ็กเกจและการติดตั้งตามผล CI จริง ไม่ใช่การรับรองว่า
Codex หรือ Claude Code โหลด Skill ค้นโมเดล หรือสร้าง Sub-agent ได้แล้ว
