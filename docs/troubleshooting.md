<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Troubleshooting

Keyed to what the tools actually print. Search this page for the start of the message you see. Messages that stop a command begin with `!`; findings end with a rule id in brackets, listed under [Rules](#rules).

Run `model doctor` first when anything is unexpected: most problems are a binding file that was not found, or one that points somewhere that does not exist.

## Setup and binding file

### `warn  bindings: no binding file found; built-in defaults are in use`

No `.agents/skill-bindings.toml`, `skill-bindings.toml`, `model.toml` or `.model.toml` in the input's folder or any folder above it. The built-in headings still work. Create `.agents/skill-bindings.toml` at the workspace root, or pass `--config`. For `doctor`, the search starts at the working directory; use `--near <folder>` to start elsewhere.

### `! reading a config file needs Python 3.11 or newer (tomllib)`

A binding file was found but this Python cannot read TOML. Use Python 3.11 or newer, or work without a binding file.

### `! <file> is not valid TOML: ... A regex belongs in a single-quoted TOML literal string`

Usually a regular expression in a double-quoted string, where `\b` or `\d` is an invalid escape. Write `id_pattern = '(SVC|EXT)-[0-9]{2}'` with single quotes.

### `! <file>: bindingsVersion 2.0 but this skill understands 1.x.`

The binding file was written for a newer format. Upgrade the skill, or set `bindingsVersion = "1.0"` if the file really is in the 1.x format. `bindingsVersion '<x>' is not a version` means the value is not a number like `1.0`.

### `! <file>: local_pattern is not a valid regex` or `pattern_id is not a valid regex`

Fix the expression in `[model]`. Test it in Python with `re.compile`.

### `! rule '<name>' has severity '<value>'; expected one of ('error', 'warn', 'off')`

A `[rules]` value is misspelled or not a string.

### `! catalogue <path> has level '<value>'; expected one of ('conceptual', 'logical', 'physical')`

Fix `level` under `[[catalogues]]`, or remove it.

### `! <file>: [model] link_target is '<value>'; expected one of new, same`

Also `[[links]] entry N target is ...`, `entry N needs match and href`, and `entry N match is not a valid regex`. Each `[[links]]` entry needs a `match` and an `href`, and `target` is `new` or `same`.

### `'<name>' points at <path>, which does not exist`

From `doctor`: a path binding resolves to nothing. Remember relative paths resolve from the folder holding the binding file, which for `.agents/skill-bindings.toml` is `.agents/`, so a workspace-root folder is `../folder`. The resolved path is printed so you can see where it looked. Related messages: `is not a directory`, `is not a file`, and `is a template and the part before its first placeholder, <path>, does not exist`.

### `'<name>' is required and not set.`

A sibling skill's `inputs.toml` requires a binding under `[suite.<skill>]` that the workspace does not set. The message ends with the option's description.

### `'<name>' is not a binding this skill declares`

A key under `[suite.<skill>]` that skill's `inputs.toml` does not list. Usually a typo.

### `'<name>' is an absolute path. It will not survive a clone on another machine`

A warning. Make the path relative to the binding file.

### `'<name>' has digest ... but the binding pins ...; the vendored copy has drifted`

A pinned file changed. Review the change, then update `<name>Sha256`.

### `! no skill '<name>' installed beside this one, on AGENT_SKILLS_PATH or in any agent skills directory.`

`doctor --skill <name>` could not find that skill (exit 3). Install it into any project or user skills folder (see the [README](../README.md#install)), or add its parent folder to `AGENT_SKILLS_PATH`.

### `catalogue not found: <path>`, `has no column '<c>'; it has ...`, `holds no values`, `could not be read`

A declared catalogue cannot be used, reported by `doctor` and as `catalogue_unreadable` by `validate`. Fix `path` (relative to the binding file) or `column` (the exact CSV header). This is an error rather than an absence on purpose: skipping it would make `not_in_catalogue` pass everything.

### `the patterns root <path> does not exist`

`[model] patterns_root`, or the `[suite.pattern]` key it fell back to, names a missing folder. `doctor` prints which key supplied it.

## Reading inputs

### The model is empty

`extract` prints no `node` rows, or `validate` reports `0 nodes`. The headings or columns do not match the contract. Check that the table sits under a heading whose text is the bound `section` (default `Components`, `Nodes`, `Interfaces`, `Edges`), that its header row has the bound column names, and that a table is a real GFM table with a `|---|` separator row. If you bound `[[markdown.tables]]`, the default tables no longer apply. An `id_unmatched` finding means the cells were found but the `id_pattern` matched nothing.

### Front matter is ignored

`validate` does not use the declared diagram, or `scan` lists the document as skipped. The front matter must be the first thing in the file, between `---` lines, with `diagram:` indented under `model:`. Skill versions before 0.8.1 did not read front matter after a UTF-8 byte order mark, which Windows PowerShell 5.1 writes with `Set-Content -Encoding utf8` and `Out-File`; write files with `[IO.File]::WriteAllText` or an editor, or upgrade.

### `! <file>: not found`

The input, or the diagram a document declares, does not exist. `validate` on a document whose declared diagram has not been emitted yet fails this way: `emit` it first, or pass `--against`.

### `! cannot read a model from '<ext>'; expected .md, .drawio, .json, .yaml or .yml`

The extension decides the representation. Rename the file, or pass a supported one.

### `! reading YAML needs PyYAML: pip install pyyaml`

Only reading YAML needs it; writing YAML does not.

### `xml.etree.ElementTree.ParseError: duplicate attribute`

A diagram emitted by version 0.8.0 or earlier with no binding file, where `node_id_attrs` defaulted to `id`, which draw.io already uses. Add `[model] node_id_attrs = ["node_id"]` to the binding file and emit again with `--force`, or upgrade to 0.8.1 or later. Any other `ParseError` means the `.drawio` is not valid XML.

## Writing and syncing

### `! <file> exists. Emitting would discard its layout.`

`emit --to drawio` will not overwrite a diagram. Use `sync <doc> <drawio>` to bring it up to date, or `--force` to start again from a grid.

### `! <file>: not found. Use emit --to drawio to create it first.`

`sync` needs an existing diagram.

### `! <file> is compressed, so it cannot be edited in place.`

draw.io desktop saved it compressed. Untick Compressed in draw.io's preferences and save again, or normalise it with the command the message prints: `drawio -x -f xml -u -o <file> <file>`. `rename` says `is compressed or empty; save it uncompressed` for the same cause.

### `! <file> has no pages`

The `.drawio` has no `<diagram>` element. It is empty or not a draw.io file.

### `ambig` lines from `sync --adopt`

Two shapes, or two connectors, match one row, so neither was tagged. Rename one shape's label, or add the identifier attribute by hand in draw.io (Edit Data), then run again.

### `orphan` lines from `sync`

Shapes whose row is gone from the document. They are outlined in dashed red rather than deleted. Delete them in draw.io, restore the row, or run `sync --prune`.

### `! <new> is already an identifier in <doc>; refusing to merge two identifiers into one`

`rename` will not merge two things into one. Pick an unused identifier, or remove the other first.

### `no diagram declared or given; only the document was changed`

`rename` found no diagram. Pass `--drawio`, or declare `model: diagram:` in the document.

## Rendering and views

### `! draw.io desktop not found.`

Install draw.io desktop, or set `DRAWIO_BIN` or `--drawio-bin` to its executable. On Windows use the installed build; the portable executable ignores command-line arguments. Without draw.io, export views by hand and `stamp` them. `model drawio` prints `draw.io desktop not found; views must be exported by hand and stamped` and exits 1 in the same situation.

### `! no such layer: <name>`

Layer names are exact and case-sensitive. The message lists the layers that exist; `model layers <drawio>` does too.

### `! export produced nothing (exit N)`

draw.io ran but wrote no file. Check the draw.io version first: its command line changes between releases. The last line draw.io printed is appended.

### `! export did not rewrite <file>; is draw.io already open on this file?`

Close the file in draw.io desktop and render again.

### `stale   <image> <- <drawio>` or `none   <image>: no render record`

From `stamp --check` (exit 1). The diagram changed since the image was made, or the image has no record. Render again, or re-export by hand and `stamp` it.

### `! <drawio> has no layer [...]; it has [...]`

`stamp --layer` named a layer the diagram lacks.

### `! --diagram is required to stamp; --check verifies an existing record`

Pass `--diagram <drawio>` to record, or `--check` to verify.

## The walkthrough

### `! <doc> declares no diagram; add model: diagram: to its front matter or pass --diagram`

`animate` needs the diagram's geometry.

### `! cannot animate:`

Followed by every problem found, one per line. `animate` validates first and stops rather than guess.

| Line | Fix |
|---|---|
| `validate: error ...` | Fix the finding, or pass `--force` to build anyway |
| `S1: in the document but has no overlay layer on the diagram` | `sync` the diagram |
| `S1: has an overlay layer but no steps table in the document` | Add the table, or delete the layer |
| `S1 step 3: on the diagram but not in the document's table` | Add the step, or `sync` |
| `S1 step 3: in the document but has no arrow on the diagram` | The step needs an Actor and a Target; then `sync` |
| `S1 step 3: no action text in the document` | Fill in the step's Action cell |
| `the document's actor is X but the diagram's arrow starts at Y` | Re-point the arrow, or `sync` |
| `endpoint X has no shape on the structure layer` | The shape is missing or not on the first layer |
| `endpoint X has no row in the document` / `interface X has no row in the document` | Add the row |
| `no scenarios to animate` | The document has no `## Scenarios` with `### S<n>` headings and tables |

### `! no current view of the 'Structure' layer`

There is no image of the structure layer beside the diagram with a matching render record, and draw.io cannot render one (`--render never`, or draw.io is not installed). The reasons are listed: `no components.svg or .png beside the diagram`, `has no render record; record it with model stamp`, `shows layers [...], not only 'Structure'`, `is older than the diagram; re-export it and stamp it`. Without draw.io, the message ends with the exact `model stamp` command to run after exporting.

### `! the rendered view is WxH but the shapes span WxH, so positions would not line up.`

The image's proportions differ from the shapes' extent, usually because an edge label or waypoint lies outside the boxes. Add a plain rectangle on the structure layer that encloses everything, as a frame, and render again. In 0.8.0 and earlier a freshly emitted diagram with all its boxes in one row could fail this by the width of draw.io's border alone; 0.8.1 allows for it.

### `! the structure image is neither a PNG nor an SVG`, `does not parse`, `states no viewBox or pixel size`

`--image`, or the view beside the diagram, is not a usable image. Export it again as SVG or PNG.

### `! --accent must be a #RRGGBB colour`

Pass six hex digits, quoted in PowerShell: `--accent '#1F6FEB'`.

### `note: S1 step 2: PAT-905 S1 links to ../PAT-905-x/scenarios.html, not built yet; run animate there`

A composite pattern's drill-in link points at a walkthrough that does not exist yet. Run `animate` on the participating pattern. `is on another drive; no link` means the two pages are on different Windows drives and cannot be linked relatively.

## Rules

Every finding ends with its rule id. Change a rule's severity in `[rules]` ([configuration](configuration.md#rules)); `off` silences it.

| Rule | Default | Means | Fix |
|---|---|---|---|
| `node_missing_id` | error | A node with no identifier, as a JSON or YAML model can hold. A draw.io shape without one is read as decoration and skipped | Give the node an id |
| `node_duplicate_id` | error | One identifier on two shapes, usually a copy-paste | Delete the copy or give it its own row and identifier |
| `node_id_mismatch` | warn | A shape's cell id differs from its identifier | Harmless for reading; `emit` writes them equal. Set to `off` for hand-drawn estates |
| `edge_missing_id` | warn | A connector with no identifier | Add the edge id attribute, or give the row an id |
| `edge_unlabelled` | warn | A connector that does not say what flows | Fill in the label column |
| `edge_dangling` | error | A connector with a free end | Attach both ends in draw.io |
| `edge_unknown_endpoint` | error | An end that is not an identified node | Add the node row, or fix the Provider or Consumer cell |
| `step_missing_fields` | error | A step with no number or no actor, or a scenario with no key | Fill in the cells |
| `step_not_contiguous` | error | Step numbers with a gap or a duplicate | Number from 1 without gaps |
| `step_endpoint_mismatch` | error | An edge or step arrow points elsewhere than the document says | Decide which is right, then fix the document or `sync` the diagram |
| `catalogue_unreadable` | error | A declared catalogue is missing, lacks the column, or is empty | See [Setup and binding file](#setup-and-binding-file) |
| `not_in_catalogue` | error | An identifier the catalogue does not hold | Add it to the catalogue, fix the typo, or use a local identifier |
| `doc_not_in_diagram` | warn | A row nobody drew | `sync` |
| `diagram_not_in_doc` | warn | A shape nobody wrote down | Add the row, or delete the shape |
| `id_unmatched` | error | A cell whose text no identifier rule matches, so the row was not read | Fix the cell or the `id_pattern`; a local id leads its cell |
| `id_attr_mismatch` | error | A local id in a catalogue attribute, or the reverse | `sync`, or move the attribute in draw.io |
| `mapping_missing` | warn | A local node with no Catalogue Mapping row | Add the row |
| `mapping_unknown_local` | error | A mapping row for a local id that is not a node | Remove the row, or add the node |
| `mapping_invalid` | error | A mapping row that is not a local id, a relationship other than realises, partial or gap, a gap with a target, a target missing, or a target that is another local id | Fix the row |
| `mapping_not_in_catalogue` | error | A mapping target the catalogue does not hold | Fix the target |
| `mapping_duplicates_node` | warn | A local node realises a block also drawn here: one concept, two boxes | Remove one |
| `uses_invalid` | error | A Uses cell that is neither `<ID> <KEY>` nor `TBD <name>`, or a malformed binding | See [composition](../skills/model/references/composition.md) |
| `uses_step_endpoints` | error | A participation step without an Actor or a Target | Fill in both |
| `participant_missing` | error | No document for the participating pattern | Create it, or bind `patterns_root` |
| `participant_scenario_missing` | error | The participating pattern has no such scenario | Fix the key |
| `participant_ambiguous` | warn | Two documents claim one id; the first is used | Rename one |
| `composition_cycle` | error | A pattern that reaches itself through Uses | Break the loop |
| `participant_join` | warn | The participating flow's entry or exit cannot be matched to the step's Actor or Target | Add a role binding, or map the local box |
| `participant_open` | warn | A `TBD` participating pattern | Write it and replace TBD |
| `participant_unapproved` | error | An approved composite pattern rests on an unapproved or open one | Approve the participating pattern, or lower this one's status |
| `participant_binding` | error | A binding names a box that is not there, or one box twice | Fix the binding |
| `scenario_start_finish` | error | A declared Start or Finish the steps do not bear out | Fix the declaration or the steps |
| `step_uses_mismatch` | warn | The diagram's Uses or regions differ from the document's | `sync` |
| `link_unresolved` | warn | A `[[links]]` rule matches an id but its `locate` glob finds nothing | Fix the glob, or create the page |
