---
name: model
description: Treat a diagram and a document as two views of one model of boxes and lines. Extract a model from Markdown tables, draw.io, JSON or YAML; emit it to any of those; validate one representation against another to catch a re-pointed arrow or an undrawn row; and render draw.io layers to SVG, PNG or PDF. Use when asked to generate a diagram from a table, check a diagram matches its document, export a diagram, list a diagram's layers, convert a model between formats, or trace which patterns a composite pattern's scenarios run.
license: CC-BY-4.0 AND Apache-2.0. Content under CC BY 4.0, code under Apache-2.0; see LICENSE and NOTICE.
compatibility: Python 3.9 or newer; Python 3.11 or newer to read a binding file. Rendering needs draw.io desktop installed (the installed build, not the portable exe). Reading YAML needs PyYAML; writing YAML needs nothing.
metadata:
  version: "0.8.0"
  homepage: https://github.com/dermot-obrien/diagram-model
  x-skill-requires: ""
  x-derived-from: "https://github.com/dermot-obrien/ai-assisted-work/tree/ac5c7ecfc3f7872737b5760906350efaa4441470/skills/model"
---

# model

One model, several representations. Markdown tables, a draw.io diagram, JSON and YAML are projections of the same boxes and lines, and this skill moves between them and checks that they agree.

Nothing here knows what the boxes mean. An architecture pattern, a network topology, a process flow and a data lineage are all the same shape. Domain vocabulary lives in the project's binding file, never in the skill.

## Which representation owns what

| Representation | Owns | Why |
|---|---|---|
| Markdown tables | What exists, and what connects to what | The document is the thing people read and review |
| draw.io | Geometry: position, routing, styling | Nothing else can hold layout, and layout is human judgement |
| JSON, YAML, CSV | Nothing | Derived projections, for tooling and for diffing |

Do not maintain two sources. Derive the others.

## Commands

Run from the skill directory. No installation is needed; `bin/model.py` puts `src` on the path itself.

```bash
python bin/model.py doctor           [--skill NAME] [--doc FILE] [--json]
python bin/model.py extract <file>   --format json|yaml|csv [--out FILE]
python bin/model.py emit    <file>   --to drawio|markdown|json|yaml|csv --out FILE [--force]
python bin/model.py validate <file>  [--against OTHER] [--json] [--fail-on error|warn|never]
python bin/model.py composition <doc> [--json]
python bin/model.py sync <doc> <drawio> [--prune] [--dry-run] [--adopt]
python bin/model.py rename  <doc> OLD NEW [--drawio FILE] [--dry-run]
python bin/model.py scan    <folder> [--recursive] [--json] [--fail-on error|warn|never]
python bin/model.py render  <drawio> --out FILE [--format svg|png|pdf] [--layer NAME ...] [--theme light|dark|auto] [--no-regions]
python bin/model.py layers  <drawio> [--json]
python bin/model.py animate <doc>    [--out FILE] [--image PNG|SVG] [--render auto|always|never] [--accent #RRGGBB] [--interval S] [--force]
python bin/model.py stamp   <image>  --diagram DRAWIO [--layer NAME ...] | --check
python bin/model.py drawio           # where draw.io desktop is; exit 1 if it is not installed
```

`extract`, `emit` and `validate` take any representation and work it out from the extension.

Exit codes: 0 success, 1 validation failed at or above the threshold, 2 usage or input error, 3 an external tool was missing or failed.

## Several models in one folder

A document declares its diagram in front matter. That declaration is what makes the two a pair, so a folder can hold several models side by side, such as a pattern and two alternative views of the same space:

```yaml
model:
  diagram: components.drawio
```

`scan <folder>` finds every document that declares one, validates each against its diagram, and lists the views a publish step renders: `<stem>.svg` for the structure layer and `<stem>-s1.svg` onward for each scenario layer, so two models never write the same file. `validate <doc>` uses the declared diagram when `--against` is not given. Documents that declare nothing are listed as skipped, not guessed at.

## Local and catalogued identifiers

A model can mix identifiers the catalogue knows with local ones for boxes it does not know yet. The binding says what a local id looks like: `local_pattern = '[0-9]{1,3}'` makes them plain numbers, `01 Gateway`, which is the usual choice; `local_prefix = "LOC-"` reserves a prefix instead. A local id must lead its table cell, so a number inside a name, as in `Office Suite 365`, is never read as one.

| Identifier | Checked for | draw.io attribute |
|---|---|---|
| Local, `01` | Unique within the document; a row in the mapping table when mappings are kept | `local_attr`, default `local_id`. Its cell id is `local-01`, because draw.io's own cells `0` and `1` would otherwise collide with local nodes `0` and `1` |
| Catalogued, `ABB-901` | Present in the declared catalogue | The `node_id_attrs` entry named for its prefix, so `SBB-911.1` goes in `sbb_id` |
| Neither | Reported as `id_unmatched`, never dropped | none |

Local ids are scoped to their document; `scan` reports them as `doc.md#01`. Each local node needs a row in a `## Catalogue Mapping` table saying what it realises, partly covers, or leaves as a gap:

| Local ID | Maps To | Relationship |
|---|---|---|
| 01 | ABB-909 RAG Pipeline | partial |
| 02 | gap | gap |

The relationship is one of `realises`, `partial` or `gap`. A gap names no target, anything else names a catalogued one, and a local node that realises a block drawn beside it is flagged, because that is one concept drawn twice.

When the catalogue gains the entry, `rename <doc> 01 ABB-910` promotes it: the identifier in the document, the attribute on the shape, the cell id and every reference to it, overlay assertions and labels. Front matter is never touched, and a plain-number id is replaced only where it leads a table cell, so the same number in prose or a date is left alone. The mapping row goes, because a catalogued node is its own mapping. It refuses to rename onto an id already in use.

## Abstraction, derived rather than declared

How abstract a model is follows from its boxes, so `validate` reports it rather than asking anyone to maintain it: `index.md: 12 nodes, 12 edges, 2 scenarios; abstraction conceptual`, and `"abstraction"` in `--json`.

| A box counts as | When |
|---|---|
| Conceptual | Its id is local, or its kind is `local` or `conceptual` |
| Logical | It comes from a catalogue declared with `level = "logical"`, or its kind is `logical` |
| Physical | It comes from a catalogue declared with `level = "physical"`, or its kind is `product` or `physical` |
| Nothing | Its kind is `external` or `context`: outside the model's scope, shown for context |
| Unknown | None of the above, for example a catalogue declared without a level |

The model is then conceptual if every counted box is conceptual, logical if the boxes are logical with or without conceptual ones, physical if every box is physical, and mixed otherwise, including when any box is unknown. A kind comes from a table's `kind` column, when the binding maps one, and wins over the identifier. The levels are generic: they say nothing about what the model is for, which is why one model of boxes, lines and walkthroughs can serve as an architecture pattern at any scope, from one problem to a whole domain, with any mix of boxes in either.

## Bringing a hand-drawn diagram into a model

`sync --adopt` tags shapes that carry no identifier but whose label names a row, instead of adding new shapes beside them. A match is exact after normalising case, whitespace and markup, against the whole label, its first line, or its leading bold run, so `<b>Q&A agent</b><br/>retrieve and synthesise` matches a row labelled `Q&A agent`. A connector between two identified shapes takes the id of the one row joining them, in either direction, and is then rewired to the document's direction. Two candidates for one row are reported as `ambig` and neither is tagged. Geometry, captions and formatting are kept: a label whose name line already matches its row is never rewritten.

Run it with `--dry-run` first and read the adopt lines. Rows with no matching shape are added below the drawing as usual.

## The conventions that make it work

Identifiers go on the `<object>` wrapper, never on the mxCell id. draw.io regenerates mxCell ids on copy, paste, duplicate and id collision, while custom attributes are part of the cell's user object and are cloned with it. That is what lets a shape be matched to a table row across edits. It also means a copy-pasted shape keeps its identifier, so duplicate detection is mandatory rather than optional.

Scenarios are layers, not pages. Duplicating a page regenerates every mxCell id, so overlay arrows stop referencing the real shapes, and it clones every identifier so a reader sees each node once per page.

Overlay arrows point at the real structure shapes. That makes the overlay part of the graph rather than a picture laid on top of it, and it is what lets validation catch an arrow that was re-pointed without its metadata following.

## Procedure

### Generating a diagram from a document

1. Check the document has the tables the config declares. Run `extract` first and read the summary; if the node or edge count is zero, the section headings or column names do not match the config.
2. `emit --to drawio`. It refuses to overwrite an existing diagram, because doing so would discard the author's layout. Use `--force` only when you mean to start again.
3. Open the result and arrange it. Generated layout is a mechanical grid: every box and arrow is present and correctly identified, but the routing will overlap and the labels will collide. Arranging it is the author's job.
4. Re-run `validate <doc> --against <drawio>` after any edit to either side.

### Checking a diagram against its document

```bash
python bin/model.py validate doc.md --against components.drawio
```

Report what it finds. The findings that matter most are the ones nobody can see by looking: an edge wired differently in the two representations, an overlay step whose asserted endpoints disagree with its real ones, and an identifier that appears twice.

### Rendering

```bash
python bin/model.py layers components.drawio
python bin/model.py render components.drawio --out scenario-1.svg --layer Structure --layer "S1 Happy path"
```

Layers are addressed by name, not index, because indexes shift when someone reorders them. Prefer SVG. The draw.io CLI changes flags between releases, so the skill probes the installed build and passes only what it accepts; if rendering fails, check the draw.io version before suspecting anything else.

An SVG is pinned to the light colour scheme on a white background by default. draw.io on its own writes colours that follow the viewer's system setting on a transparent background, so a diagram embedded in a document or a slide turns dark on a dark-mode machine while the page around it stays light. `--theme dark` pins the dark scheme, `--theme auto` keeps draw.io's behaviour, and `--transparent` keeps the background transparent.

Every render also writes `<image>.render.json` beside the image: the source diagram relative to the image, a SHA-256 of it with line endings normalised, and the layers. A consumer, such as markdown-deck, compares the fingerprint with the diagram as it is now and reports the image as stale when they differ, naming the command that re-renders it. Commit the record with the image.

### Animating the scenarios

```bash
python bin/model.py animate index.md
```

Writes `scenarios.html` beside an `index.md`, or `<stem>-scenarios.html` beside any other document: one self-contained page that opens from disk in any browser, with no server. It steps through each scenario on the structure view: the step's number on the acting shape, an arrow drawn to the target, everything else dimmed, a zoom onto the two shapes, and the narrative with the interface's purpose and spare columns. Arrow keys step, space plays.

The document supplies names, narratives and interface details; the diagram supplies geometry and each step's endpoints. The page draws its own arrows between the shapes' current positions, so after moving shapes, re-run it; there is nothing else to update. Positions inside groups and containers are resolved.

The structure view it draws on is the one thing draw.io is needed for, and draw.io is optional. With `--render auto`, the default, it uses a current view beside the diagram, `<stem>.svg` or else `<stem>.png`, whose render record matches the diagram; only when there is none does it ask draw.io desktop to render one, and if draw.io is not installed it stops and says which file to export and stamp. `--render never` never calls draw.io, for a build machine without it; `--render always` renders regardless. Drawing on a committed view also makes the page identical from run to run, where a fresh render can differ by a pixel.

It validates first and stops rather than guesses. A step with no narrative, an endpoint with no shape on the structure layer, a scenario in the document but not on the diagram or the reverse, or a rendered view whose proportions differ from the shapes' extent is an error that names every case. The last usually means an edge label or waypoint lies outside the shapes; a background rectangle enclosing the structure layer, used as a frame, fixes it.

### Composing patterns

A composite pattern is one whose scenario steps run other patterns' flows, its participating patterns. The constructs are borrowed rather than invented: a participation step is BPMN 2.0.2's call activity, a scenario's declared start and finish are its start and end events (UML 2.5.1 ports on the pattern's boundary), a role binding is UML 2.5.1's collaboration use with its role bindings, and each participating pattern's region on the diagram is that collaboration use drawn as a dashed outline. In a sequence diagram the same step is an InteractionUse, a `ref` fragment.

Add a `Uses` column to the step table and, on a participation step, name the participating pattern's id and scenario key, `PAT-905 S1`, or write `TBD <name>` for an open participating pattern, not yet written. Trailing text after the key is prose and ignored, except a parenthesised group of `id=id` pairs directly after the key, which is the role binding: participating pattern's box on the left, this pattern's box on the right.

| Step | Actor | Target | Action | Interface | Uses |
|---:|---|---|---|---|---|
| 2 | ABB-901 Order service | ABB-901 Order service | take payment | | PAT-905 S1 (01=ABB-901) |

A participation step needs an Actor and a Target, the boxes where the participating pattern's flow enters and leaves; its Interface is optional. An open participating pattern cannot carry a binding. Steps without Uses, and documents without the column, behave as before. The header comes from the scenario column contract (`uses = "Uses"`), and a participating pattern's id must match `pattern_id`, by default `[A-Z]{2,5}-[0-9]{3}`.

A scenario may declare where its flow starts and finishes, on their own lines under its heading and before its steps table, each a box's id optionally followed by its name. Narrative may come before or between them; a blank line between the two keeps them on separate lines on the page:

```markdown
### S1 Payment capture

Start: ABB-901 Order service

Finish: 01 Card processor
```

The Start is the first step's actor, the Finish the last step's actor or target. A composite pattern that runs the scenario joins to them: the declared box is then the only candidate, where without one the entry is the first step's actor and the exit the last step's actor or target.

`validate` resolves each participation step and says, by rule:

| Rule | Severity | When |
|---|---|---|
| `uses_invalid` | error | The cell is neither `<ID> <KEY>` nor `TBD <name>`; a binding that is not all `id=id` pairs; a TBD with a binding |
| `uses_step_endpoints` | error | A participation step without an Actor or a Target |
| `participant_missing`, `participant_scenario_missing` | error | No document for the id, or no scenario with the key |
| `participant_binding` | error | A binding whose left box is not in the participating pattern or right box not in this one, or a box twice on one side |
| `composition_cycle` | error | A pattern running itself through Uses, directly or transitively |
| `participant_join` | warn | The participating scenario's start (declared, else its first actor) is not the step's Actor, or its finish (declared, else its last step's actor or target) is not the step's Target. Boxes match through the step's binding first, then when they share a catalogue id, directly or through either document's Catalogue Mapping; local ids match across documents only through a binding |
| `participant_open` | warn | An open participating pattern, `TBD`, listed until it is written |
| `participant_unapproved` | error | The composite pattern's front matter `status` is approved but a participating pattern, at any depth, is not, or a `TBD` remains |
| `participant_ambiguous` | warn | Two documents claim one id; the first is used |
| `scenario_start_finish` | error | A declared Start that is not the first step's actor, a Finish that is not the last step's actor or target, or either not a box of the pattern |
| `step_uses_mismatch` | warn | The diagram's overlay arrow carries a different Uses, or its regions do not match the participating patterns; run `sync` |

A participating pattern is a folder whose name starts with `<ID>-` holding `index.md`, or, when no folder is named for the id, a document whose first H1 starts with it. It is looked for under `[model] patterns_root`, else `[suite.pattern] patternsRoot`, else `[suite.pattern] outputDir`, to any depth. With none bound, each folder from the composite pattern's upward is searched two levels deep, stopping at the repository root. `approved_statuses` in `[model]`, or `approvedStatuses` in `[suite.pattern]`, sets which statuses the gate counts as approved, by default Final, Approved, Active and Published. `doctor` prints the root in use.

`composition <doc>` prints the composition tree: each participation step, the participating pattern's id, scenario and status, its binding, whether the join used a declared start or finish, open participating patterns, recursively, with cycles marked. `--json` gives the same as data (`binding`, and `join` as `declared` or `derived` per end). `validate` adds a one-line summary.

On the diagram, the overlay arrow of a participation step carries `uses="PAT-905 S1"`, is labelled `[+] 2: PAT-905 S1`, BPMN's call-activity marker in ASCII because a boxed-plus glyph falls back to an empty box in draw.io's export, and is drawn heavier and dash-dotted (`style.flow_uses` overrides it). `emit` and `sync` keep a layer named `Participating patterns` just above the structure: one dashed, rounded, unfilled region per distinct participating pattern, and per distinct open one, labelled with its id and name (`Open: <name>` for a TBD) and carrying `participant` (the id, or `TBD <name>`). A region encloses the boxes bound to it, the Actor and Target of every step that runs it and the right-hand side of any binding, with padding that grows with the region's index so overlapping outlines stay apart. Regions are not containers; `sync` recomputes them from the boxes' current positions and removes one that no step runs; `style.region` overrides the style.

`render` of the structure layer includes the `Participating patterns` layer by default when the diagram has one, and records it in the render record; `--no-regions` leaves it out. A view exported by hand is stamped with the layers it shows: `--layer Structure --layer "Participating patterns"` when it shows the regions.

In the walkthrough a participation step is one step with a drill-in badge, drawn with a boxed plus. Clicking the badge, the link beside the steps, or pressing D opens the participating pattern's walkthrough at that scenario, relative to this page, with the way back in the query; that page shows a link back to the composite pattern, and B goes back to the step it came from. A `#S1` or `#S1-3` hash opens any walkthrough at that scenario or step. An open participating pattern shows the marker greyed, without a link. Build each participating pattern's walkthrough too; `animate` notes a link to one not built yet. The page's script holds no `url(...)` or attribute text a deck's asset scan would read as a file, so embedding it in a markdown-deck slide raises no warning.

### Linking boxes to their pages

A box whose id is declared, a building block, a product, a pattern, a capability, anything the workspace catalogues, can link to that item's page. The workspace declares how, in the binding file; nothing in the skill knows a site's layout:

```toml
[model]
link_site   = "http://localhost:3000/docs"            # {site}; optional
link_target = "new"                                   # "new" (default) or "same"

[[links]]
match  = 'ABB-[0-9]{3}'                               # full match on the id
locate = "../building-blocks/abbs/*/{id}-*"           # optional glob, relative to the binding file
href   = "{site}/building-blocks/abbs/{located}/"
target = "same"                                       # optional; wins over link_target
```

| Placeholder | Is |
|---|---|
| `{id}` | The identifier |
| `{site}` | `[model] link_site`, empty when unset, without a trailing slash |
| `{located}` | The first path `locate` matched, relative to the glob's fixed prefix (the folders before its first wildcard), with forward slashes and no trailing slash; a matched `index.md` is dropped, so its folder is named |
| `{rel}` | The relative path from the generated page to the matched path, for a workspace that links files on disk |

Rules are tried in order and the first whose `match` fits the whole id wins, so one rule per prefix is normal: building blocks, dotted product ids, patterns, capabilities. Ids are matched after the usual leading-id extraction. Local ids are never linked. A rule whose href needs `{located}` or `{rel}` when `locate` found nothing gives no link and a `link_unresolved` warning, from `validate` and `animate`, naming the id and the glob. An invalid `link_target` or `target` is a configuration error.

In the walkthrough, each linked box has a hotspot over its shape on the view, with its name as the tooltip, and the Actor and Target names in the steps list and the step's pop-up link the same way. A participation step's participating pattern links to its page too when a rule covers its id, beside the drill-in, which stays the main action and keeps opening in the same page with a Back link. `new` opens a link in a new tab (`target="_blank"`, `rel="noopener"`); `same` opens it in place. Hotspots sit below the step badges and the drill-in badge, and stepping, zoom and the keys are unchanged.

`emit` and `sync` set draw.io's own `link` on a box a rule resolves, with `linkTarget` `_blank` for `new` or `_self` for `same`, so the box is clickable in draw.io and its exports; `sync` updates it, and removes it when the box's rule no longer resolves. A box no rule matches keeps any link its author gave it. The link is part of the diagram, so a view rendered before it changed is reported stale by its render record like any other edit.

`doctor` lists the rules; `doctor --doc <file>` also says which of that document's boxes resolve, and to what.

### Working without draw.io desktop

Rendering needs draw.io desktop; nothing else does. Where it is not installed, the views are exported by hand, from draw.io desktop or from draw.io online, and committed beside their diagrams:

1. Open the `.drawio`, show only the structure layer (the first, usually named Structure), and export it as SVG to `<stem>.svg` beside the diagram, the name `render` would give it.
2. Record what it shows, so it is checked like a rendered view from then on:

   ```bash
   python bin/model.py stamp components.svg --diagram components.drawio --layer Structure
   ```

3. Commit the diagram, the SVG and its `.render.json` together.

`stamp --check <image>` exits 0 when the record still matches the diagram, so a build can refuse a view that was not re-exported after the diagram changed. markdown-deck reads the same record, warning on a stale image and failing under `CI`.

## Configuration

`.agents/skill-bindings.toml`, found by searching upward from the input file, or passed with `--config`. `model.toml` is still recognised as an alias. One file binds the whole skill suite to the host repository's layout.

Run `doctor` before anything else. It resolves every binding to an absolute path, verifies the ones that must exist, and exits non-zero if any do not. `--skill NAME` checks a sibling skill's `inputs.toml` contract instead of this skill's own, so a prose skill can declare what it needs without shipping a runtime.

A path binding may carry a `{placeholder}`, such as `planning/{quarter}/basis.csv`, when one binding covers many runs. Only the skill that owns the placeholder can fill it, so `doctor` checks the directory in front of the first placeholder and leaves the rest to that skill.

Relative paths anchor to the directory holding the binding file, never to the working directory, so a binding means the same thing wherever it is run from. `bindingsVersion` is refused if its major is one this skill does not understand: a silently misread binding is worse than a stopped run.

It declares the draw.io attribute names, the Markdown table contract as section and column names, optional catalogue files to check identifiers against, each with an optional `level` of `conceptual`, `logical` or `physical` for the derived abstraction, and a severity for each rule. `examples/model.toml` is a complete worked example. With no config at all, conventional headings such as `## Components` and `## Interfaces` work out of the box.

A declared catalogue that cannot be read is an error, not an absence. Skipping it silently would turn `not_in_catalogue` into a no-op exactly when the binding is wrong, which is the moment it most needs to speak up.

Composing patterns adds `patterns_root`, `pattern_id` and `approved_statuses` to `[model]`, the `uses` scenario column, and the rules listed under composing above.

The rules added for local identifiers are `id_unmatched`, `id_attr_mismatch`, `mapping_missing` (warn by default), `mapping_unknown_local`, `mapping_invalid`, `mapping_not_in_catalogue` and `mapping_duplicates_node` (warn).

Every rule has a severity of `error`, `warn` or `off`. Set an unhelpful rule to `warn` rather than abandoning the tool: a rule that is right for a new diagram is often wrong as a hard failure across an existing estate.

## Reporting back

Give the counts from the summary line, name the findings by rule, and say which file each side of a disagreement favours. Never report a render as successful without checking the output file exists and is non-empty; some draw.io releases print an error on success and a success on failure.

## Library use

`from model import load, drawio, markdown, serial, validate` works if `src` is on the path. `load(path, cfg)` returns a `Model` of `nodes`, `edges`, `groups` and `scenarios`.
