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

## Other agents and API-key clients

For a host with native Agent Skills support, configure its documented discovery directory and install the entire [skill directory](../skills/intelligent-model-router/). For a text-only host, explicitly supply SKILL.md as task guidance, then supply referenced files as needed. A host that cannot accept instructions or access the required inputs cannot run this workflow.

For API use, your application reads SKILL.md and includes its text in the provider's instruction field, then supplies the user's task and relevant inputs in a separate message. Keep the API key in the application's secret store and use it only for provider authentication. Resolve relative references within the installed skill directory. File edits, helper scripts and external tools require host implementations and permissions. Without tools, return a proposed edit or recommendation for the user to apply.

## First task

Use the supplied inventory and evidence. Recommend an eligible model and explain the decision. If no candidate qualifies, abstain.

Record the host and version, whether the host loaded the skill automatically or explicitly, and the actual output. Use public or synthetic inputs when sharing a report.
