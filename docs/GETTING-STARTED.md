# Getting started

[Project home](../README.md) · [Documentation](README.md) · [ภาษาไทย](README.th.md)

Install the skill, ask your agent to use it, and inspect the resulting plan.
No inference account or API key is required for the instruction-only workflow.

## Before you start

You need a host that can load Agent Skills. Its model list, permissions, and
execution tools determine what is actually possible. The project does not yet
claim verified live-host conformance; see [the checklist](HOST-TESTS.md).

The [Skills CLI documentation](https://github.com/vercel-labs/skills#install-a-skill)
currently requires Node.js 22.20 or later (checked 2026-11-20). This requirement
belongs to the external installer, not to the skill format. The optional offline
helpers require Python 3.10+; instruction-only use does not.

## Install

Run in the project where you use your agent:

```sh
npx skills add whale-devx/intelligent-model-router-skills --skill intelligent-model-router
```

Review the installer and select your host. Project installation is the default.
For a user-level installation across projects:

```sh
npx skills add whale-devx/intelligent-model-router-skills --skill intelligent-model-router -g
```

To name a target explicitly, append `-a` and an agent identifier supported by the
installer. For example, `-a claude-code`. Installer target support is not evidence
that this project's model discovery or delegation has been tested on that host.

List installed skills:

```sh
npx skills list
```

For a user-level installation, use:

```sh
npx skills list -g
```

These commands follow the upstream [CLI reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md).
They are installation instructions, not a recorded end-to-end test result.

<details>
<summary>Manual installation without npx</summary>

Obtain a reviewed checkout of this repository. Copy the entire
`skills/intelligent-model-router/` directory into the skill location documented by
your host. Do not copy only `SKILL.md`. The references, scripts, assets, and license
must stay together. Review differences before replacing an existing installation.

Refresh or restart the host according to its documentation, then explicitly ask it
to use `intelligent-model-router`. Do not assume every host uses the same folder or
reload command.

</details>

## Installer privacy

The skill and its bundled helpers send no telemetry. The **external Skills CLI**
has its own telemetry and audit behavior. Its documentation describes
`DISABLE_TELEMETRY=1` as an opt-out. Review the
[upstream privacy settings](https://github.com/vercel-labs/skills/blob/main/docs/troubleshooting.md#telemetry)
before installation.

<details>
<summary>Installation with installer telemetry disabled</summary>

For a POSIX shell:

```sh
DISABLE_TELEMETRY=1 npx skills add whale-devx/intelligent-model-router-skills --skill intelligent-model-router
```

For PowerShell, set it in the current session before installing:

```powershell
$env:DISABLE_TELEMETRY = "1"
npx skills add whale-devx/intelligent-model-router-skills --skill intelligent-model-router
```

This concerns the installer only. Your host and model provider have separate data
policies. Installing over the network is not the same as offline skill execution.

</details>

## Your first request

```text
Use intelligent-model-router to help choose a model for my next coding task.
Use only the models exposed by this host or inventory I explicitly provide.
Preserve my privacy rules and budget. Explain the evidence and missing information.
Recommend only; do not switch models or create a subagent yet.
```

The agent should inspect the inventory made available to it, apply the task's
constraints, and use permitted evidence. If no discovery API exists, it should
ask for a model list rather than guessing access or searching credential stores.

**This alpha has no live inventory or leaderboard connectors.** You or the host
must supply trustworthy inventory and comparable evidence. No evidence is a valid
reason to abstain, not permission to manufacture model scores.

## Read the result

| Field | How to interpret it |
| --- | --- |
| `status` | Selection, missing inventory, no eligible models, or insufficient evidence |
| `selected` | The chosen endpoint and model identity, or `null` |
| `action` | A recommendation or proposed host operation |
| `execution_status` | Always `not_executed` in the offline helper |
| `estimated_success_probability` | Always `null`; there is no calibrated predictor |
| `evidence`, `warnings`, `reasons` | The basis and limits of the decision |

See the [contract](../skills/intelligent-model-router/references/contract.md) for
the full schema, exact states, and exit codes.

> [!IMPORTANT]
> A routing plan does not grant permissions. Before a model switch or subagent
> handoff, the host must support the operation, revalidate access and constraints,
> and obtain any required approval. Do not treat `not_executed` as success.

## Try the synthetic example

From a repository checkout, with Python 3.10+:

```sh
python skills/intelligent-model-router/scripts/route.py --input skills/intelligent-model-router/assets/example-request.json --as-of 2026-11-20
```

The example uses fictional models and synthetic scores, chooses `example-b`, and
returns a recommendation only. It makes no network or inference calls. The date
pins the demonstration, not the freshness of evidence for a real task.

## Troubleshooting

<details>
<summary>The installer fails or cannot find the skill</summary>

Check `node --version`, the upstream CLI's requirements, and access to npm and
GitHub. Confirm the repository and skill name are spelled exactly as in the install
command. An installer/network failure is separate from a routing failure.

Include the installer version, OS, command, and sanitized error when reporting it.
Do not post authentication tokens or private registry configuration.

</details>

<details>
<summary>The skill is installed, but the agent does not activate it</summary>

Verify that you installed to the intended host and scope. Follow the host's reload
instructions and explicitly name `intelligent-model-router` in your request.
Do not assume a successful installation guarantees automatic activation.

Record the host/version and observations using [HOST-TESTS.md](HOST-TESTS.md).

</details>

<details>
<summary>The result is needs_inventory or insufficient_evidence</summary>

Supply an authorized inventory and task-matched evidence using the
[request contract](../skills/intelligent-model-router/references/contract.md).
Preserve exact model/configuration identities, dates, and sources. Do not relabel
synthetic data or broaden permissions just to force a selected result.

</details>

<details>
<summary>The host cannot switch models or create the requested subagent</summary>

Use recommendation mode. The skill does not invent a switching API, replace the
host's Auto mode, or install a new provider. A host integration must be verified
before native delegation can be claimed.

</details>

[Report a reproducible issue](https://github.com/whale-devx/intelligent-model-router-skills/issues/new/choose)
or continue with the [host protocol](../skills/intelligent-model-router/references/host-protocol.md).
For security issues, follow [SECURITY.md](../SECURITY.md).
