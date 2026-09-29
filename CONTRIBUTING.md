# Contributing to diagram-model

Thank you for your interest in contributing. Bug reports, fixes, adapters, examples and documentation improvements to the `model` skill are all welcome.

## Ways to contribute

- Report a bug, with the smallest document and diagram that show it.
- Suggest an improvement to the extract, emit, sync and validate rules, or a new representation.
- Fix a bug or add a feature, with tests.
- Improve the documentation or the worked example.

## Process

For a small change, fork the repository, make the change and open a pull request.

For a significant change, open an issue first describing what you want to do, so it can be discussed before you invest in it. Then fork, develop and open a pull request that references the issue.

## Before you open a pull request

Run, from the repository root:

```bash
node scripts/validate-skills.mjs skills
skills-ref validate skills/model
python -m unittest discover -s skills/model/tests
```

Keep the skill generic. It is used by many organisations, so nothing in it may name or imply one: no organisation names, internal hosts, identifiers or brand palettes in code, tests or examples. An organisation's own vocabulary, catalogue and layout belong in its own repository, bound through its own `.agents/skill-bindings.toml`.

Record a user-visible change in `CHANGELOG.md` and raise the version in `skills/model/SKILL.md` (`metadata.version`), `skills/model/pyproject.toml`, `skills/model/src/model/__init__.py`, the skill's entry in `.claude-plugin/marketplace.json` and its `version` and `purl` in `bundle.json` together.

`skills-ref` is the Agent Skills reference validator; the README's [Agent Skills conformance](README.md#agent-skills-conformance) section says how to install it. CI runs both, and fails a `SKILL.md` over 500 lines or about 5,000 tokens: move detail into a file under the skill and link it.

## Repository layout

```text
diagram-model/
├── skills/model/              the skill: the only directory an installer copies
│   ├── SKILL.md               what the agent reads, Agent Skills format
│   ├── references/            detail SKILL.md links to, loaded when needed
│   ├── examples/              the worked example and its binding file
│   ├── LICENSE, LICENSES/, NOTICE   carried inside so a copied directory is complete
│   ├── pyproject.toml         optional pip install
│   ├── bin/model.py           entry point, runs from a copied directory
│   ├── src/model/
│   │   ├── schema.py          the canonical model, no domain vocabulary
│   │   ├── config.py          the binding file
│   │   ├── markdown.py        GFM tables, both directions
│   │   ├── drawio.py          mxGraph XML, both directions
│   │   ├── serial.py          JSON, YAML, CSV
│   │   ├── bindings.py        resolve and check bindings; find other skills
│   │   ├── validate.py        rules and severities
│   │   ├── sync.py            reconcile a diagram with its document, keeping geometry
│   │   ├── render.py          draw.io CLI, with capability probing, and render records
│   │   ├── animate.py         standalone HTML walkthrough of the scenarios
│   │   ├── composition.py     composite patterns
│   │   ├── links.py           links from identifiers to their pages
│   │   ├── scan.py            the models in a folder
│   │   └── cli.py
│   └── tests/
├── docs/                      the user documentation
├── .claude-plugin/            the Claude Code plugin and its one-plugin marketplace
├── bundle.json                the bundle manifest
├── scripts/                   the skill and bundle validators CI runs
├── LICENSE, LICENSES/, NOTICE, REUSE.toml
├── CHANGELOG.md
└── README.md
```

## Documentation

`SKILL.md` is for the agent and stays within the specification's size guidance: put detail in `references/` or in `docs/`, and link to it. `docs/` is for people and is not installed with the skill. When a command, flag, binding key, message or rule changes, update [docs/commands.md](docs/commands.md), [docs/configuration.md](docs/configuration.md) or [docs/troubleshooting.md](docs/troubleshooting.md) in the same pull request, and re-run the [quick start](docs/quick-start.md) if its output could change. A change under `docs/` alone needs no version bump.

## Releases

Each skill is versioned and released on its own, as DD-11 of AI-Assisted Work sets out. A release is a commit on `main` whose versions agree for that skill, tagged `<skill>--v<version>`, for example `model--v0.7.0`. Claude Code resolves a dependency range against those tags, and `gh skill install` reads them. Earlier releases were tagged after the repository, such as `diagram-model--v0.6.0`, and those tags stay where they are.

## Licensing of contributions

This repository is dual-licensed:

- Content (Markdown, skill instructions, examples): [CC BY 4.0](LICENSES/CC-BY-4.0.txt)
- Code (`bin/`, `src/`, `tests/`, `scripts/`, `pyproject.toml`, plugin manifests, CI workflows): [Apache-2.0](LICENSES/Apache-2.0.txt)

By submitting a contribution (pull request, patch, or issue containing code), you agree that it is licensed under the same terms as the file you are modifying. New code files must include an SPDX header:

```python
# SPDX-FileCopyrightText: <year> <your name or organisation>
# SPDX-License-Identifier: Apache-2.0
```

New content files are covered by the bulk rules in `REUSE.toml` and need no header. The project follows the [REUSE Specification 3.3](https://reuse.software/spec-3.3/).

## Derivative works

If you fork this repository or build on it:

1. Keep `LICENSE`, `LICENSES/`, `NOTICE` and `REUSE.toml` intact, and add your own attribution to `NOTICE` rather than replacing it.
2. Preserve the `SPDX-FileCopyrightText` and `SPDX-License-Identifier` headers in the files you carry over.
3. Mention "Based on diagram-model by Dermot O'Brien, derived from AI-Assisted Work" in your README, and link to this repository.
4. Indicate the changes you have made, as both CC BY 4.0 and Apache-2.0 require.

## Code of conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions

Open an [issue](https://github.com/dermot-obrien/diagram-model/issues).
