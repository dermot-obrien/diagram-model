<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Examples

## In this repository

| Where | What it shows |
|---|---|
| [skills/model/examples/example.md](../skills/model/examples/example.md) | A small model with its own vocabulary: services and an external party under `## Components` with a `Zone` column and a spare `Role` column, interfaces with an `IF-` prefix, and one scenario |
| [skills/model/examples/model.toml](../skills/model/examples/model.toml) | The binding file for it: attribute names, both table contracts with `id_pattern`, the scenario columns, and commented examples of catalogues, links, composition and style |
| [docs/quick-start.md](quick-start.md) | A model built from scratch with the default headings, taken through emit, validate, render, animate and sync |
| [skills/model/references/composition.md](../skills/model/references/composition.md) | A participation step, a role binding and a scenario's Start and Finish |
| [skills/model/references/links.md](../skills/model/references/links.md) | A link rule with a `locate` glob |
| [skills/model/tests/](../skills/model/tests/) | Every feature exercised on small inline documents and diagrams: local identifiers and mappings in `test_local_ids.py`, composite patterns in `test_composition.py`, links in `test_links.py`, the walkthrough in `test_animate.py` |

## Run the worked example

Copy the example folder somewhere to work in, so nothing is written into the skill. From the root of a clone of this repository:

PowerShell:

```powershell
$skill = (Resolve-Path skills\model\bin\model.py).Path
function model { python $skill @args }
Copy-Item -Recurse skills\model\examples $env:TEMP\model-example
cd $env:TEMP\model-example
```

bash:

```bash
skill="$PWD/skills/model/bin/model.py"
model() { python "$skill" "$@"; }
cp -r skills/model/examples /tmp/model-example
cd /tmp/model-example
```

Then, in either shell:

```
model validate example.md
model emit example.md --to drawio --out components.drawio
model validate example.md --against components.drawio
model extract example.md --format yaml
```

`model.toml` sits beside the document, so it is found without `--config`. The first `validate` prints `example.md: 4 nodes, 3 edges, 3 groups, 1 scenario (3 steps); abstraction mixed`. `extract` shows the spare `Role` column carried as the attribute `role`.

With draw.io desktop installed, render the structure and animate the scenario. The example declares no diagram in front matter, so `animate` is told which one:

```
model render components.drawio --out components.svg --layer Structure
model animate example.md --diagram components.drawio
```

## Built on this skill

- [architecture-pattern](https://github.com/dermot-obrien/architecture-pattern): the `pattern` skill, which authors an architecture pattern as one Markdown document that is also the model and the deck, and uses this skill to generate, check, render and animate its diagrams. Its templates are larger examples of a binding.
- [markdown-deck](https://github.com/dermot-obrien/markdown-deck): turns tagged Markdown into slides, reads the render records this skill writes to warn on stale diagrams, and embeds walkthroughs.
