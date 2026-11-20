# Documentation

[Project home](../README.md) · [ภาษาไทย](README.th.md) · [Roadmap](ROADMAP.md)

**Start with your goal.** Installation, routing decisions, and host execution are
separate steps; these guides help you follow the right path.

## Start using the skill

| Guide | What you will find |
| --- | --- |
| [Getting started](GETTING-STARTED.md) | `npx skills` installation, first prompt, expected behavior, and troubleshooting |
| [ภาษาไทย](README.th.md) | ภาพรวม วิธีติดตั้ง ตัวอย่างการใช้งาน และข้อจำกัดปัจจุบัน |
| [Current status](../README.md#current-status) | What the alpha does today and what is not yet verified |

## Understand a decision

| Reference | What you will find |
| --- | --- |
| [Skill instructions](../skills/intelligent-model-router/SKILL.md) | The workflow the host reads when activating the skill |
| [Routing contract](../skills/intelligent-model-router/references/contract.md) | Input fields, model identity, ranking, policy gates, and output semantics |
| [Discovery and host protocol](../skills/intelligent-model-router/references/host-protocol.md) | Access states, authorization, and the boundary between selection and execution |
| [Evidence sources](../skills/intelligent-model-router/references/sources.md) | How to assess benchmark sources, provenance, and data rights |

## Contribute or report a problem

| Guide | What you will find |
| --- | --- |
| [Contributing](../CONTRIBUTING.md) | Development workflow and review expectations |
| [Installation verification](INSTALLATION-TESTS.md) | Isolated npx checks, package integrity, exact versions, and CI evidence limits |
| [Host conformance](HOST-TESTS.md) | A reproducible checklist for recording real host behavior |
| [Roadmap](ROADMAP.md) | Priorities and acceptance criteria, not promised release dates |
| [Writing guide](WRITING-GUIDE.md) | GitHub formatting, accessibility, language parity, and honest status claims |
| [Security](../SECURITY.md) | Privacy boundaries and safe vulnerability reporting |
| [Changelog](../CHANGELOG.md) | Version notes |

[Report a bug or host test](https://github.com/whale-devx/intelligent-model-router-skills/issues/new/choose).
Do not post secrets, private prompts, or personal model inventories.

> [!NOTE]
> Documentation and installation support are not live-host certification. Consult
> [HOST-TESTS.md](HOST-TESTS.md) before making compatibility claims. The offline
> helper returns plans, not execution receipts.
