# Use this skill with your agent

Run this in the project where you want the skill. Replace TARGET with one value from the table.

```sh
npx skills add whale-devx/intelligent-model-router-skills --skill intelligent-model-router --agent TARGET
```

| Host | TARGET | Project directory observed with Skills CLI 1.9.0 |
|---|---|---|
| Codex | codex | .agents/skills |
| Claude Code | claude-code | .claude/skills |
| Cursor | cursor | .agents/skills |
| Gemini CLI | gemini-cli | .agents/skills |
| Kiro CLI | kiro-cli | .kiro/skills |

Validation on Windows used a temporary project and the repository checkout as the source, with all five targets selected and copy mode enabled. The installer produced the skill in the three directories above. This checks installation only. Live activation and task completion require separate tests in each host. Kiro IDE was not tested.

## Upgrade or restore a project-local copy

For a Codex project installed with Skills CLI 1.9.0 and `--copy`, start from
the consuming project root. Record the working revision from the lockfile.

```sh
python -c "import json; from pathlib import Path; entry=json.loads(Path('skills-lock.json').read_bytes())['skills']['intelligent-model-router']; print(entry['source'], entry.get('commit'))"
```

Confirm the source is `whale-devx/intelligent-model-router-skills`. Back up
the full installed folder and the lockfile outside the agent's skill
directories. The installer replaces local edits inside the managed folder.
Store private requests, inventory snapshots and their original observation
dates in a separate project-owned location. If the lock entry lacks a
commit, retain a complete backup before changing the installation.

Replace `FULL_COMMIT` with the reviewed upstream SHA. The bundled fictional
request provides an offline smoke test with a fixed replay date.

```sh
npx --yes skills@1.9.0 add "https://github.com/whale-devx/intelligent-model-router-skills/tree/FULL_COMMIT" --skill intelligent-model-router --agent codex --copy --yes
python -B .agents/skills/intelligent-model-router/scripts/route.py --input .agents/skills/intelligent-model-router/assets/example-request.json --as-of 2026-11-20
```

Verify the lock commit and inspect the decision's `execution_status`, which
should be `not_executed`. For a saved raw catalog, migrate the calling
command to supply its original `--observed-at` date. If that date is
unknown, obtain a fresh authorized listing before using it as current
evidence. A normalized inventory already carries dates on its model rows.
For an OpenAI-style listing, replace the input path and date below with
the saved catalog and the day it was observed.

```sh
python -B .agents/skills/intelligent-model-router/scripts/discover.py --input CATALOG.json --format openai-list --observed-at YYYY-MM-DD
```

To roll back, repeat the install with the recorded working SHA and rerun the
smoke test. Check other skills' lock entries and preserve their current
versions. Earlier catalog importers can assign today's date to old data.
Use the original observation record when reviewing freshness after rollback.
Restore intentional local changes from the backup and reload the host.

To uninstall this project copy, run `npx --yes skills@1.9.0 remove intelligent-model-router --agent codex --yes`.
Check that its folder and lock entry are gone and that other project skills
and saved inventories are intact. This also affects agents sharing the same
project directory.

## Other agents and API-key clients

For a host with native Agent Skills support, configure its documented discovery directory and install the entire [skill directory](../skills/intelligent-model-router/). For a text-only host, explicitly supply SKILL.md as task guidance, then supply referenced files as needed. A host that cannot accept instructions or access the required inputs cannot run this workflow.

For API use, your application reads SKILL.md and includes its text in the provider's instruction field, then supplies the user's task and relevant inputs in a separate message. Keep the API key in the application's secret store and use it only for provider authentication. Resolve relative references within the installed skill directory. File edits, helper scripts and external tools require host implementations and permissions. Without tools, return a proposed edit or recommendation for the user to apply.

## First task

Use the supplied inventory and evidence. Recommend an eligible model and explain the decision. If no candidate qualifies, abstain.

Record the host and version, whether the host loaded the skill automatically or explicitly, and the actual output. Use public or synthetic inputs when sharing a report.
