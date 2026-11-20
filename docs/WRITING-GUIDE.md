# Documentation style and GitHub formatting

[Project home](../README.md) · [Documentation](README.md) · [Contributing](../CONTRIBUTING.md)

Make it easy to understand the project, install the skill, and judge its limits.
A more attractive page must never imply capabilities that have not been tested.

## Page structure

The repository README is the entry point: purpose, current limitations, installation,
first request, workflow, current status, and next steps. Keep implementation details
in reference files and contributor procedures out of the main installation path.

Use one level-one heading per page and descriptive level-two headings. Keep links
between repository files relative, so they follow the current branch. Give each
page a way back to the documentation hub. The hub is a Markdown index, not a custom
GitHub sidebar or a separate website.

## Formatting with a purpose

| Feature | How this project uses it |
| --- | --- |
| `<picture>` | Repository-owned SVG banner with light/dark variants and descriptive alt text |
| Badges | A live workflow badge and explicit stage/license labels; no invented test, coverage, or adoption numbers |
| Section links | Short routes to installation, status, workflow, and documentation |
| Tables | Small comparisons with concise headers, not wide page-layout grids |
| `<details>` / `<summary>` | Optional installation details and troubleshooting; never hide important limitations |
| GitHub alerts | Essential status or permission warnings, normally no more than two per page |
| Mermaid | Source-controlled workflow with a nearby plain-text explanation |
| Fenced code blocks | Copyable commands, labeled synthetic output, and language identifiers |
| Task lists | Roadmap acceptance criteria; check only work backed by evidence |

Avoid custom CSS/JavaScript, autoplay, flashing images, large logo walls, and
unnecessary animated badges. GitHub controls the rendering environment.

## Accessibility and language

Use text headings and instructions even when a banner is present. Give images
meaningful alternatives. Describe diagrams in prose, and do not rely on color
alone to communicate state. Keep tables narrow and code blocks independently
copyable. Check light/dark themes and narrow screens.

Maintain English and Thai entry points together. Commands, alpha status, security
boundaries, and unimplemented features must agree between them. Reference documents
can stay in English, with their language and purpose clear from navigation.

## Status claims

Distinguish installer support, installed files, host activation, model discovery,
and confirmed execution. An offline CI pass is not host certification. A benchmark
ranking is not a success probability. Show synthetic examples as synthetic.

A source guide lists evidence options; it does not mean a live connector exists.
Do not add release/download badges for packages or releases that do not exist.
The CI badge follows `main`; a pull request must link its own run when reporting tests.

## Review checklist

- [ ] Purpose, install command, and alpha limitations are easy to find.
- [ ] English and Thai commands and status agree.
- [ ] Relative links and section anchors resolve.
- [ ] Images have alternatives and render in both themes.
- [ ] Code fences, details blocks, tables, and Mermaid parse correctly.
- [ ] Mobile content does not require page-wide horizontal scrolling.
- [ ] Claims match code, test receipts, and host evidence.
- [ ] No secrets, private prompts, or user inventories are included.

## Formatting references

These are the GitHub documentation pages used for this presentation refresh,
reviewed on 2026-11-20. They describe formatting support, not project capabilities.

- [Quickstart for writing on GitHub](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github)
- [Basic writing and formatting syntax](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)
- [Creating diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)
- [Creating and highlighting code blocks](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-and-highlighting-code-blocks)
- [Syntax for issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
