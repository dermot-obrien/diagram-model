<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Concepts

The ideas behind the `model` skill, in the order you meet them. The [quick start](quick-start.md) shows each one in use.

## One model, several representations

A model is boxes and lines, and optionally numbered walkthroughs over them:

```text
Model
├── nodes      id, label, group, kind, attrs
├── edges      id, source, target, label, kind, attrs
├── groups     id, label
└── scenarios  key, name, start, finish, steps[ step, actor, target, action, edge, uses, binding ]
```

Markdown tables, a draw.io diagram, JSON, YAML and CSV are all projections of it. `extract` reads a model out of any of them, `emit` writes one into any of them, and `validate` checks two of them agree.

Nothing in the skill knows what the boxes mean. An architecture pattern, a network topology, a process flow and a data lineage have the same shape, so the vocabulary (which headings, which identifiers, which catalogue) lives in your workspace's binding file, never in the skill.

## Which representation owns what

| Representation | Owns | Why |
|---|---|---|
| Markdown tables | What exists, and what connects to what | The document is what people read and review |
| draw.io | Geometry: position, routing, styling | Nothing else can hold layout, and layout is human judgement |
| JSON, YAML, CSV | Nothing | Derived projections, for tooling and diffing |

Keep one source for each thing and derive the rest. You edit the document to add a box and the diagram to move one; `sync` carries the first into the second without disturbing the second.

## The document

The skill reads GitHub-flavoured Markdown tables under named headings. With no binding file it looks for:

| Heading | Columns | Becomes |
|---|---|---|
| `## Components` or `## Nodes` | `Component` (or `Node`), `Group` | Nodes |
| `## Interfaces` | `Interface`, `Provider`, `Consumer`, `Purpose` | Edges, from Provider to Consumer |
| `## Edges` | `Edge`, `From`, `To`, `Purpose` | Edges |
| `## Scenarios`, then `### S1 Name` | `Step`, `Actor`, `Action`, `Interface`, `Target`, `Uses` | One scenario per `S<n>` heading |
| `## Catalogue Mapping` | `Local ID`, `Maps To`, `Relationship` | What each local identifier stands for |

The binding file renames any of these ([configuration](configuration.md#markdowntables)). A few rules make reading predictable:

- An identifier is the first word of its cell, or the first match of the table's `id_pattern` when one is bound. `WEB Storefront` is node `WEB` labelled Storefront.
- A cell that holds text no identifier rule matches is reported as `id_unmatched` rather than dropped, so a wrong prefix never produces a silently empty model.
- Headings and column names match without regard to case.
- Columns the contract does not name are kept as attributes, so a `Protocol` column rides along to the diagram and the walkthrough.
- HTML comments are ignored, so template guidance and example rows in comments never become part of the model. Headings inside code fences are ignored too.

Front matter is read for `title` (the model's name, and the draw.io page name), `version`, `status` (for [composing patterns](#composing-patterns)) and the `model:` block below.

## The diagram

`emit --to drawio` writes an uncompressed `.drawio` whose conventions are what make checking possible:

- The identifier goes on the `<object>` wrapper as a custom attribute (by default `node_id`, `edge_id`), never only on the mxCell id. draw.io regenerates mxCell ids on copy, paste and duplicate, while custom attributes are cloned with the shape. That is how a shape is matched to its row across edits, and why a copy-pasted shape is caught as `node_duplicate_id`.
- The first layer is the structure: the boxes and lines. A shape without an identifier on it, such as a band, a legend or a caption, is left alone.
- Each scenario is a layer, not a page, named after its key (`S1 Checkout`) and hidden by default. Duplicating a page would regenerate every id and clone every identifier.
- Scenario arrows connect the real structure shapes and carry `scenario`, `step`, the edge id and the asserted `from` and `to`. So an arrow re-pointed in draw.io without its data following is caught as `step_endpoint_mismatch`.

Generated layout is a plain grid: every box and arrow is present and identified, but you arrange it. From then on `sync` keeps your arrangement, and `emit` refuses to overwrite an existing diagram unless you pass `--force`.

## Pairing a document with its diagram

A document names its diagram in front matter:

```yaml
---
title: Online Shop
model:
  diagram: components.drawio
---
```

The declaration is what makes a pair. With it, `validate doc.md` and `rename` find the diagram themselves, `animate` finds its geometry, and `scan <folder>` finds every pair in a folder and validates each. A folder can hold several models side by side; nothing is inferred from file names, and documents that declare nothing are listed as skipped.

`scan` also names the views a publish step renders for each diagram: `<stem>.svg` for the structure layer, and `<stem>-s1.svg` onward for each scenario layer over it, so two models in one folder never write the same file.

## The binding file

One file binds a workspace's layout to every skill in the suite: `.agents/skill-bindings.toml`. It is found by searching upward from the input file (or from the working directory for `doctor`), trying at each folder `.agents/skill-bindings.toml`, `skill-bindings.toml`, `model.toml` and `.model.toml`. `--config` names one directly.

- Relative paths in it anchor to the folder holding the file, never to the working directory, so a binding means the same wherever a command runs. For `.agents/skill-bindings.toml` that folder is `.agents/`, so a catalogue at the workspace root is `../catalogue.csv`.
- `bindingsVersion` guards the format. A major version this skill does not know is refused, because a silently misread binding is worse than a stopped run.
- Anything under `[suite.<skill>]` belongs to another skill and is carried untouched.
- With no file at all the defaults above apply, and `doctor` warns.

`doctor` resolves every path the binding names, checks the ones that must exist, and exits 1 if one does not. Run it before anything else. The [configuration reference](configuration.md) has every key.

## Findings, rules and severities

`validate` and `scan` report findings. Each names a rule, a severity and where it was found:

```text
  error  IF3: IF3 is CART->STOCK in the document but CART->PAY on the diagram  [step_endpoint_mismatch]
```

Every rule has a severity of `error`, `warn` or `off`, set in `[rules]`. A rule right for a new diagram is often wrong as a hard failure across an existing estate, so turn an unhelpful rule down to `warn` rather than abandoning the tool. `--fail-on error` (the default) exits 1 on any error, `--fail-on warn` on any finding, and `--fail-on never` always exits 0.

The rules that earn their keep are the agreement ones: a row nobody drew (`doc_not_in_diagram`), a shape nobody wrote down (`diagram_not_in_doc`), an edge wired differently in the two (`step_endpoint_mismatch`), and a copy-pasted identifier (`node_duplicate_id`). Anyone can see an unlabelled box; nobody can see, by looking, that an arrow now points somewhere else. [Troubleshooting](troubleshooting.md#rules) lists every rule and what to do about it.

## Sync, adopt and prune

`sync <doc> <drawio>` reconciles a diagram with its document in place: new rows become shapes placed below the drawing, changed labels and groups are updated, edges are rewired to the document's direction, scenario layers are rebuilt, and shapes whose row has gone are marked as orphans, outlined in heavy dashed red, rather than deleted. `--prune` deletes them instead, and `--dry-run` reports without writing.

`--adopt` brings a hand-drawn diagram into a model. It tags shapes that carry no identifier but whose label names a row, instead of adding new shapes beside them, and tags a connector between two tagged shapes with the one row joining them. Two candidates for one row are reported as `ambig` and neither is tagged. Run it with `--dry-run` first and read the `adopt` lines.

`sync` needs an uncompressed `.drawio`. draw.io desktop saves compressed files when Compressed is ticked in its preferences.

## Views and render records

`render` asks draw.io desktop to export chosen layers, by name, to SVG, PNG, PDF or JPG. Layers are named rather than numbered because numbers shift when someone reorders them. An SVG is pinned to the light colour scheme on a white background by default, so it does not turn dark inside a light page on a dark-mode machine; `--theme` changes that.

Every render writes `<image>.render.json` beside the image: the diagram it came from, a SHA-256 of the diagram with line endings normalised, and the layers. Anything can then tell when the image is stale: `stamp --check`, `animate`, and markdown-deck, which warns on a stale image and fails under CI. Commit the record with the image.

draw.io desktop is the only external tool, and it is optional. Without it, export the view by hand from draw.io desktop or online, and `stamp` writes the same record for it.

## The walkthrough

`animate <doc>` writes one HTML page that opens from disk with nothing fetched: `scenarios.html` beside an `index.md`, else `<stem>-scenarios.html`. It steps through each scenario on the structure view, with the step's number on the acting box, an arrow to the target, everything else dimmed, and the action text with the interface's purpose and any spare columns. Arrow keys step, space plays, and `#S1-3` in the address opens a scenario at a step.

The document supplies the words and the diagram the geometry, so after moving boxes you re-run it. It uses a current view beside the diagram (`<stem>.svg`, else `<stem>.png`, whose render record matches) and only renders one when there is none. It validates first and stops, naming every problem, rather than guess.

## Local and catalogued identifiers

A workspace may keep a catalogue of the things its boxes stand for, a CSV with an identifier column, bound under `[[catalogues]]`. Every identifier is then checked against it (`not_in_catalogue`).

Boxes the catalogue does not know yet can use local identifiers, which the binding defines: `local_pattern = '[0-9]{1,3}'` makes them plain numbers, as in `01 Gateway`. A local identifier must lead its cell, so `Office Suite 365` is a name, not identifier 365. Each local node says what it stands for in a `## Catalogue Mapping` table:

| Local ID | Maps To | Relationship |
|---|---|---|
| 01 | CAT-909 Search | partial |
| 02 | gap | gap |

The relationship is `realises`, `partial` or `gap`. When the catalogue gains the entry, `rename <doc> 01 CAT-910` promotes it everywhere: the document's tables, the shape's attribute and cell id, every arrow and label, and the mapping row goes. Local nodes get cell ids like `local-01`, because draw.io's own cells are `0` and `1`.

## Abstraction

`validate` reports how abstract a model is, derived from its boxes rather than declared: `abstraction conceptual`, `logical`, `physical` or `mixed`.

| A box counts as | When |
|---|---|
| Conceptual | Its id is local, or its kind is `local` or `conceptual` |
| Logical | It comes from a catalogue bound with `level = "logical"`, or its kind is `logical` |
| Physical | It comes from a catalogue bound with `level = "physical"`, or its kind is `product` or `physical` |
| Nothing | Its kind is `external` or `context`: shown for context only |
| Unknown | None of the above |

The model is conceptual if every counted box is conceptual, logical if the boxes are logical with or without conceptual ones, physical if every box is physical, and mixed otherwise, including when any box is unknown. That is why the quick start's unclassified boxes report `mixed`. A kind comes from a table's `kind` column when the binding maps one.

## Composing patterns

A scenario step can run a scenario of another document through a `Uses` cell: `PAT-905 S1`, optionally with a role binding, `PAT-905 S1 (01=CAT-901)`, or `TBD <name>` for one not yet written. The document holding such steps is a composite pattern, and each participation step stands for the participating pattern's whole flow. A scenario may declare `Start:` and `Finish:` boxes. `validate` resolves the composition, `composition <doc>` prints its tree, the diagram gains a `Participating patterns` layer of dashed regions, and the walkthrough drills into each participating pattern's own. The constructs are BPMN 2.0.2's call activity and UML 2.5.1's collaboration use.

[references/composition.md](../skills/model/references/composition.md) has the syntax, where participating patterns are found, and every rule.

## Links from boxes to their pages

A box whose identifier the workspace declares can link to that item's page. `[[links]]` rules in the binding match identifiers and build an address, optionally from a file found on disk. The walkthrough gets a clickable hotspot on each linked box, and `emit` and `sync` set draw.io's own link on the shape. [references/links.md](../skills/model/references/links.md) has the detail.

## Other skills in the suite

Skills without a runtime of their own borrow this one's resolver. Such a skill declares what it needs in an `inputs.toml` beside its `SKILL.md`, the workspace answers under `[suite.<name>]` in the binding file, and `doctor --skill <name>` checks the one against the other. `doctor` also finds the skills a skill declares in `metadata.x-skill-requires`, wherever each agent installed them. See [configuration](configuration.md#sibling-skills-and-inputstoml).

## Known limitations

Generated layout is a mechanical grid, one column per group. Every box and arrow is present and correctly identified, but routing overlaps and edge labels collide where several interfaces meet one box. Arranging the diagram is the author's job; `sync` preserves that work, and `emit --to drawio` refuses to overwrite it.

A scenario is a numbered walkthrough overlaid on the structure: a UML communication diagram, which C4 calls a dynamic diagram. It cannot express branching, loops or concurrency, so a flow with real alternatives belongs in a sequence diagram.

Round-tripping is not lossless in both directions. A diagram legitimately holds bands, annotations and a legend that the model has no place for; those are read as not a node and left alone. Only the first page of a `.drawio` is read.

`sync` and `rename` need an uncompressed `.drawio`.
