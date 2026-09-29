<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Configuration reference

Everything the `model` skill reads besides its inputs: the binding file, document front matter, environment variables, and the `inputs.toml` contract other skills declare. [Concepts](concepts.md#the-binding-file) explains why it works this way; [skills/model/examples/model.toml](../skills/model/examples/model.toml) is a complete worked example.

## Which file is used

| Precedence | Source |
|---|---|
| 1 | `--config FILE` on the command |
| 2 | The nearest binding file found by searching upward from the input file (from the working directory, or `--near`, for `doctor`). At each folder, in order: `.agents/skill-bindings.toml`, `skill-bindings.toml`, `model.toml`, `.model.toml` |
| 3 | Built-in defaults, when no file is found. `doctor` warns |

Reading a binding file needs Python 3.11 or newer (`tomllib`). Relative paths in it resolve from the folder holding the file: for `.agents/skill-bindings.toml` that is `.agents/`, so a file at the workspace root is `../name.csv`. An absolute path works but will not survive a clone on another machine.

Write regular expressions in single-quoted TOML literal strings, `'^(S[0-9]+)\b'`. In a double-quoted string `\b` is an escape TOML rejects.

## Top level

### bindingsVersion

| Type | Default | Example |
|---|---|---|
| string | `"1.0"` | `bindingsVersion = "1.0"` |

The binding format's version. A major other than 1 is refused with an error rather than read. Optional, but set it so a future format change is caught.

## [model]

draw.io attribute names, local identifiers, composition and links.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `node_id_attrs` | list of strings | `["node_id"]` | draw.io attributes that carry a node's identifier, tried in order when reading. When writing, an identifier goes in the first attribute whose name, less `_id`, equals the identifier's prefix in lower case (`SBB-911.1` goes in `sbb_id`), else the first. `id` cannot be used: draw.io owns it |
| `edge_id_attr` | string | `"edge_id"` | The attribute carrying an edge's identifier |
| `group_attr` | string | `"group"` | The attribute carrying a node's group |
| `kind_attr` | string | `"kind"` | The attribute carrying a node's or edge's kind |
| `local_pattern` | regex string | `""` | What a local identifier looks like, as in `'[0-9]{1,3}'`. Must lead its table cell. Wins over `local_prefix` |
| `local_prefix` | string | `""` | A reserved prefix for local identifiers followed by two or three digits, as in `"LOC-"`. Both empty means no local identifiers |
| `local_attr` | string | `"local_id"` | The attribute carrying a local identifier. Its cell id is `local-<id>` |
| `patterns_root` | path | `""` | Where participating patterns are found for `Uses`. See precedence below |
| `pattern_id` | regex string | `'[A-Z]{2,5}-[0-9]{3}'` | What a participating pattern's identifier looks like in a `Uses` cell |
| `approved_statuses` | list of strings, or a comma-separated string | `["Final", "Approved", "Active", "Published"]` | Front matter `status` values the composition's approval gate counts as approved, compared without regard to case |
| `link_site` | string | `""` | Substituted for `{site}` in `[[links]]` hrefs, without a trailing slash |
| `link_target` | `"new"` or `"same"` | `"new"` | Where a link opens: a new tab, or in place. Anything else is a configuration error |

Before 0.8.1 the default for `node_id_attrs` was `["id"]`, which draw.io reserves, so a diagram emitted with no binding file could not be read. Bind `node_id_attrs` explicitly when a workspace must work with 0.8.0 or earlier.

Precedence for `patterns_root`: `[model] patterns_root`, then `[suite.pattern] patternsRoot`, then `[suite.pattern] outputDir`. With none, each folder from the composite pattern upward is searched two levels deep, stopping at the repository root. For `approved_statuses`: `[model] approved_statuses`, then `[suite.pattern] approvedStatuses`, then the default.

```toml
[model]
node_id_attrs = ["abb_id", "sbb_id"]   # ABB-... ids go in abb_id, SBB-... in sbb_id
edge_id_attr  = "iface_id"
local_pattern = '[0-9]{1,3}'
patterns_root = "../patterns"
link_site     = "https://docs.example.org"
link_target   = "same"
```

## [[markdown.tables]]

One entry per table the document holds. Declaring any entry replaces the four default tables (`Nodes`, `Components`, `Edges`, `Interfaces`) entirely.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `section` | string | required | The heading text the table sits under, any level, matched without regard to case |
| `entity` | `"node"` or `"edge"` | `"node"` | What each row is |
| `id_pattern` | regex string | `""` | The identifier in a cell is the first match of this; empty means the cell's first word. For an edge table it is applied to the id, source and target cells alike, so it must match node identifiers as well as edge ones |
| `columns` | inline table | see below | Maps model fields to column headers, matched without regard to case |

Column keys for a node table: `id` (required), `label` (default: the `id` column, with the identifier removed), `group`, `kind`. For an edge table: `id`, `source`, `target`, `label`, `kind`. Any other column in the table becomes an attribute, its header turned into a name such as `role_in_this_architecture`.

The built-in tables, used when none is declared:

| section | entity | columns |
|---|---|---|
| `Nodes` | node | `id = "Node"`, `label = "Node"`, `group = "Group"` |
| `Components` | node | `id = "Component"`, `label = "Component"`, `group = "Group"` |
| `Edges` | edge | `id = "Edge"`, `source = "From"`, `target = "To"`, `label = "Purpose"` |
| `Interfaces` | edge | `id = "Interface"`, `source = "Provider"`, `target = "Consumer"`, `label = "Purpose"` |

```toml
[[markdown.tables]]
section    = "Components"
entity     = "node"
id_pattern = '(SVC|EXT)-[0-9]{2}'
columns    = { id = "Component", label = "Component", group = "Zone", kind = "Kind" }

[[markdown.tables]]
section    = "Interfaces"
entity     = "edge"
id_pattern = '(IF|SVC|EXT)-[0-9]{2}'
columns    = { id = "Interface", source = "Provider", target = "Consumer", label = "Purpose" }
```

## [markdown.scenarios]

| Key | Type | Default | Meaning |
|---|---|---|---|
| `section` | string | `"Scenarios"` | The heading the scenarios sit under. Each scenario is a lower heading inside it |
| `heading_pattern` | regex string | `'^(S\d+)\b[\s:.-]*(.*)$'` | Matches a scenario heading; group 1 is the key, group 2 the name |
| `columns` | inline table | `{ step = "Step", actor = "Actor", action = "Action", edge = "Interface", target = "Target", uses = "Uses" }` | Merged over the default, so you name only what differs |

`step` is the number, `actor` the box acting, `target` the box acted on, `action` the words the walkthrough shows, `edge` the interface used, and `uses` a participation step's `<ID> <KEY>` or `TBD <name>`. `Start: <box>` and `Finish: <box>` lines between a scenario heading and its table declare where the flow starts and finishes.

```toml
[markdown.scenarios]
section         = "Walkthroughs"
heading_pattern = '^(W[0-9]+)\b[\s:.-]*(.*)$'
columns         = { actor = "From", target = "To" }
```

## [markdown.mapping]

The table saying what each local identifier stands for.

| Key | Type | Default |
|---|---|---|
| `section` | string | `"Catalogue Mapping"` |
| `columns` | inline table | `{ id = "Local ID", maps_to = "Maps To", relationship = "Relationship" }`, merged over the default |

```toml
[markdown.mapping]
section = "Mappings"
columns = { maps_to = "Catalogue entry" }
```

## [[catalogues]]

CSV files of identifiers the workspace recognises. Declaring none is fine and silent; declaring one that cannot be read is an error (`catalogue_unreadable`).

| Key | Type | Default | Meaning |
|---|---|---|---|
| `path` | path | required | The CSV, relative to the binding file. Read as UTF-8, with or without a byte order mark |
| `column` | string | required | The header of the identifier column |
| `level` | `"conceptual"`, `"logical"` or `"physical"` | `""` | How abstract its identifiers are, for the derived abstraction. Anything else is a configuration error |

```toml
[[catalogues]]
path   = "../catalogue/services.csv"
column = "id"
level  = "physical"
```

## [rules]

A severity per rule: `"error"`, `"warn"` or `"off"`. Rules not named keep their defaults; any other value is a configuration error.

```toml
[rules]
node_id_mismatch = "off"
doc_not_in_diagram = "error"
```

| Rule | Default |
|---|---|
| `node_missing_id`, `node_duplicate_id` | error |
| `node_id_mismatch` | warn |
| `edge_missing_id`, `edge_unlabelled` | warn |
| `edge_dangling`, `edge_unknown_endpoint` | error |
| `step_missing_fields`, `step_not_contiguous`, `step_endpoint_mismatch` | error |
| `catalogue_unreadable`, `not_in_catalogue` | error |
| `doc_not_in_diagram`, `diagram_not_in_doc` | warn |
| `id_unmatched`, `id_attr_mismatch` | error |
| `mapping_missing` | warn |
| `mapping_unknown_local`, `mapping_invalid`, `mapping_not_in_catalogue` | error |
| `mapping_duplicates_node` | warn |
| `uses_invalid`, `uses_step_endpoints`, `participant_missing`, `participant_scenario_missing`, `composition_cycle`, `participant_unapproved`, `participant_binding`, `scenario_start_finish` | error |
| `participant_ambiguous`, `participant_join`, `participant_open`, `step_uses_mismatch` | warn |
| `link_unresolved` | warn |

[Troubleshooting](troubleshooting.md#rules) says what each one means and how to fix it.

## [style]

draw.io style strings for what `emit` and `sync` draw. Each replaces the default whole.

| Key | Styles | Default |
|---|---|---|
| `node` | Boxes | `rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#3A4654;fontSize=14;align=center;verticalAlign=middle;` |
| `edge` | Structure connectors | `edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;fontSize=12;strokeColor=#3A4654;` |
| `badge` | Scenario step numbers | `ellipse;whiteSpace=wrap;html=1;fillColor=#C25B54;strokeColor=none;fontColor=#FFFFFF;fontSize=14;fontStyle=1;` |
| `flow` | Scenario arrows | `edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;dashed=1;strokeWidth=2;strokeColor=#C25B54;fontColor=#C25B54;fontSize=12;` |
| `flow_uses` | Participation step arrows | heavier, dash-dotted `flow` with a white label background |
| `region` | Participating patterns' regions | dashed, rounded, unfilled |

```toml
[style]
node = "rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F7FA;strokeColor=#1F2933;"
```

## [[links]]

Rules that turn a declared identifier into a link, tried in order; the first whose `match` fits wins. Local identifiers are never linked. [references/links.md](../skills/model/references/links.md) has the detail.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `match` | regex string | required | Must match the whole identifier |
| `href` | string | required | The address, with `{id}`, `{site}`, `{located}` and `{rel}` substituted |
| `locate` | glob | `""` | A path relative to the binding file, `{id}` substituted; its first match supplies `{located}` and `{rel}` |
| `target` | `"new"` or `"same"` | `[model] link_target` | Overrides `link_target` for this rule |

```toml
[[links]]
match  = '(SVC|EXT)-[0-9]{2}'
locate = "../services/*/{id}-*"
href   = "https://docs.example.org/services/{located}/"
```

## [suite.&lt;skill&gt;]

Bindings for other skills in the suite. The `model` skill carries them untouched, except that it reads `[suite.pattern] patternsRoot`, `outputDir` and `approvedStatuses` as fallbacks (above), and `doctor --skill <name>` checks `[suite.<name>]` against that skill's `inputs.toml`.

```toml
[suite.pattern]
outputDir = "../patterns"
```

## Front matter

Read from a document's YAML front matter; flat keys and one level of nesting.

| Key | Type | Meaning |
|---|---|---|
| `title` | string | The model's name, and the draw.io page name `emit` writes |
| `version` | string | Carried into the model |
| `status` | string | Compared with `approved_statuses` by the composition's approval gate |
| `model.diagram` | path, relative to the document | The diagram this document is paired with. Used by `validate` without `--against`, `rename` without `--drawio`, `animate` without `--diagram`, and `scan` |

```yaml
---
title: Online Shop
status: Draft
model:
  diagram: components.drawio
---
```

## Environment variables

| Variable | Used by | Meaning |
|---|---|---|
| `DRAWIO_BIN` | `render`, `animate`, `drawio` | The draw.io executable, when it is not on `PATH` or in the usual install folder. `--drawio-bin` wins over it |
| `AGENT_SKILLS_PATH` | `doctor` | Extra folders to look for sibling skills in, separated as `PATH` is |
| `CLAUDE_CONFIG_DIR` | `doctor` | Where Claude Code keeps its plugins, default `~/.claude`, searched for skills installed as plugins |

## Sibling skills and inputs.toml

A skill with no runtime of its own declares what it needs from the workspace in an `inputs.toml` beside its `SKILL.md`. The workspace answers under `[suite.<skill>]`, and `python <skills>/model/bin/model.py doctor --skill <skill>` checks the answer.

```toml
[inputs]
short_description = "Bindings required to author a pattern in this repository"

[inputs.options.outputDir]
type        = "dir"
required    = true
description = "Directory new pattern folders are created in"
```

| Option key | Type | Default | Meaning |
|---|---|---|---|
| `type` | `"str"`, `"path"`, `"dir"` or `"file"` | `"str"` | A path type is resolved from the binding file and must exist; `dir` and `file` must also be that kind |
| `required` | boolean | `false` | Unset and required is an error |
| `default` | any | none | Used when the workspace sets nothing |
| `description` | string | `""` | Shown in the error when a required option is missing |
| `choices` | list | none | The only values allowed |
| `sha256` | string | none | Pins a file's digest; a binding `<name>Sha256` in `[suite.<skill>]` does the same from the workspace side |

A path value may carry a `{placeholder}`, such as `planning/{quarter}/basis.csv`; only the folder before the first placeholder is checked. A key in `[suite.<skill>]` that the contract does not declare is a warning, since a typo is otherwise indistinguishable from an unset binding.

A skill names the skills it needs in `SKILL.md` as `metadata.x-skill-requires`, comma-separated, each a Package URL and a range, `pkg:generic/dermot-obrien/diagram-model/model ^0.8.0`, or the older `model@^0.6.0`. `doctor` looks for each beside the skill, on `AGENT_SKILLS_PATH`, in every project and user skills folder an agent reads, and among Claude Code plugins, and lists what it finds as `siblings`.
