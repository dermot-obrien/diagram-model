<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# diagram-model

The `model` skill: an [Agent Skill](https://agentskills.io/specification) that treats a diagram and a document as two views of one model of boxes and lines. It generates a draw.io diagram from Markdown tables, keeps the two in step without losing your layout, catches where they disagree (a row nobody drew, an arrow re-pointed without its data following), renders views and builds an animated walkthrough of each scenario.

Nothing in it knows what the boxes mean, so it serves an architecture pattern, a network topology, a process flow or a data lineage alike; your workspace's binding file holds the vocabulary. It is pure Python standard library, needs no installation, and assumes no particular agent or IDE. The [architecture-pattern](https://github.com/dermot-obrien/architecture-pattern) skill is built on it, and [markdown-deck](https://github.com/dermot-obrien/markdown-deck) uses it when present. It began as part of [AI-Assisted Work](https://github.com/dermot-obrien/ai-assisted-work); see [Origin](#origin).

## Install

The skill is one folder, [`skills/model/`](skills/model/). Install it by putting that folder in a skills folder your agent reads: in the workspace, for everyone who clones the project, or in your user folder, for every project you open.

| Agent | Workspace folder | User folder |
|---|---|---|
| VS Code with GitHub Copilot | `.github/skills/`, `.agents/skills/` or `.claude/skills/` | `~/.copilot/skills/`, `~/.agents/skills/` or `~/.claude/skills/` |
| Cursor | `.cursor/skills/`, `.agents/skills/` or `.claude/skills/` | `~/.cursor/skills/`, `~/.agents/skills/` or `~/.claude/skills/` |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.agents/skills/` | `~/.agents/skills/` or `~/.codex/skills/` |
| Gemini CLI | `.agents/skills/` | `~/.gemini/skills/` or `~/.agents/skills/` |

`.agents/skills/` is the shared convention most agents read, and Amp, Zed, Windsurf, Cline and others read it too. A team whose members use different agents can install once there and, for Claude Code, once more in `.claude/skills/`. Skills installed by different tools still find each other ([configuration](docs/configuration.md#sibling-skills-and-inputstoml)).

### By hand, any agent

PowerShell, into the workspace (for the user folder, put `$HOME\.agents\skills` in place of `.agents\skills`):

```powershell
git clone --depth 1 https://github.com/dermot-obrien/diagram-model.git $env:TEMP\diagram-model
New-Item -ItemType Directory -Force .agents\skills | Out-Null
Copy-Item -Recurse $env:TEMP\diagram-model\skills\model .agents\skills\model
Remove-Item -Recurse -Force $env:TEMP\diagram-model
```

bash, into the workspace (for the user folder, put `~/.agents/skills` in place of `.agents/skills`):

```bash
git clone --depth 1 https://github.com/dermot-obrien/diagram-model.git /tmp/diagram-model
mkdir -p .agents/skills
cp -r /tmp/diagram-model/skills/model .agents/skills/model
rm -rf /tmp/diagram-model
```

Add `--branch model--v0.8.0` to the clone to pin a release; each release is tagged `model--v<version>`. To update, delete the folder and copy it again.

### With an installer

```bash
# GitHub CLI 2.90 or later, for any agent
gh skill install dermot-obrien/diagram-model model
#   --agent github-copilot|cursor|claude-code|codex|gemini-cli|... chooses the host
#   --scope user installs for every project; --pin model--v0.8.0 locks the version

# The skills CLI
npx skills add dermot-obrien/diagram-model/skills/model

# Gemini CLI
gemini skills install https://github.com/dermot-obrien/diagram-model.git --path skills/model --scope user --consent
```

The repository is also a Claude Code plugin marketplace, so other plugins can depend on it by version:

```text
/plugin marketplace add dermot-obrien/diagram-model
/plugin install model@diagram-model
```

Pinned and auditable, for a regulated or air-gapped consumer: copy by hand with `--branch model--v<version>` as above, commit the folder, and name the tag in the commit message. The diff between two copied versions is the audit trail. (`git subtree add` of this repository would put the whole repository, not the skill folder, under its prefix, where no agent finds `SKILL.md`.)

[`bundle.json`](bundle.json) describes the skill for installers that read the AI-Assisted Work bundle manifest, with `python bin/model.py doctor` as the check to run after installing.

### Requirements

Python 3.9 or newer; 3.11 or newer to read a binding file. draw.io desktop (the installed build, not the portable one) only to render images, which can instead be exported by hand. PyYAML only to read YAML.

## Quick start

From the workspace root, with the skill in `.agents/skills/model` and a document `shop.md` holding `## Components` and `## Interfaces` tables:

```bash
python .agents/skills/model/bin/model.py doctor
python .agents/skills/model/bin/model.py emit shop.md --to drawio --out components.drawio
python .agents/skills/model/bin/model.py validate shop.md --against components.drawio
python .agents/skills/model/bin/model.py sync shop.md components.drawio
python .agents/skills/model/bin/model.py animate shop.md --diagram components.drawio
```

Or ask your agent to "generate a diagram from the tables in shop.md" or "check components.drawio matches shop.md". The [quick start](docs/quick-start.md) goes from nothing to a checked diagram, a rendered view and a walkthrough in about ten minutes, in PowerShell and bash.

## Documentation

| Page | For |
|---|---|
| [Quick start](docs/quick-start.md) | A first real result, step by step |
| [Concepts](docs/concepts.md) | The model, which representation owns what, the diagram conventions, findings and rules, sync, views, the walkthrough, local identifiers, abstraction, composition and links |
| [Configuration](docs/configuration.md) | Every binding file key, front matter key and environment variable, with defaults and precedence; the `inputs.toml` contract |
| [Commands](docs/commands.md) | Every command and flag, output and exit code |
| [Troubleshooting](docs/troubleshooting.md) | Each error and warning message, and every rule id, with the fix |
| [Examples](docs/examples.md) | The worked example and where each feature is shown |
| [SKILL.md](skills/model/SKILL.md) | What the agent reads: when to use the skill and the procedures it follows |
| [Composing patterns](skills/model/references/composition.md), [Linking boxes](skills/model/references/links.md) | Reference detail the skill loads when needed |
| [CHANGELOG](CHANGELOG.md), [CONTRIBUTING](CONTRIBUTING.md) | Releases, and how to change the skill |

## Agent Skills conformance

`model` conforms to the [Agent Skills specification](https://agentskills.io/specification). Its `SKILL.md` carries only the fields the specification defines, its `name` is the name of the directory it is installed into (`skills/model` here, and `model` under whichever skills directory an installer uses), every `metadata` value is a string, and the file stays within the specification's guidance of 500 lines and 5,000 tokens, with detail in files it links by a relative path one level deep. The `x-` keys in `metadata` are this project's own, which the specification allows.

CI checks this on every pull request and every push to `main`, with `skills-ref`, the specification's reference validator, beside this repository's own `scripts/validate-skills.mjs`, which also checks that relative links resolve. To run the same checks locally, from the repository root:

```bash
python -m pip install "git+https://github.com/agentskills/agentskills@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref"
skills-ref validate skills/model
node scripts/validate-skills.mjs skills
```

On Windows, set `PYTHONUTF8=1` before running `skills-ref`, which otherwise reads `SKILL.md` in the system's code page.

## Versions and identifiers

The skill is identified by a Package URL of the `generic` type, `pkg:generic/dermot-obrien/diagram-model/model`, which names no host, so a mirror or a move changes where it is fetched from but not what it is called. It has its own Semantic Version in `SKILL.md` (`metadata.version`), and each release is tagged `model--v<version>`. A skill that needs this one declares it in `metadata.x-skill-requires` as `pkg:generic/dermot-obrien/diagram-model/model ^0.8.0`; `doctor` reads that form, and the older `model@^0.6.0`, to find it. This follows DD-11 of [AI-Assisted Work](https://github.com/dermot-obrien/ai-assisted-work/blob/main/docs/about/design-decisions.md).

## Origin

`model` was developed as a skill of [AI-Assisted Work](https://github.com/dermot-obrien/ai-assisted-work), by the same author, and was extracted into this repository on 2026-09-29 at version 0.5.0 so it can be used without that framework. [NOTICE](./NOTICE) records the exact source commit; the history before extraction is the history of `skills/model` there.

## Licence

Content under [CC BY 4.0](LICENSES/CC-BY-4.0.txt) and code under [Apache-2.0](LICENSES/Apache-2.0.txt). See [LICENSE](./LICENSE), and keep [NOTICE](./NOTICE) with any copy or derivative.
