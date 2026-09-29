<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Command reference

Every command of `bin/model.py`, checked against its `--help`. Run it from anywhere as `python <skills>/model/bin/model.py <command>`; it needs no installation. A `pip install ./skills/model` puts the same thing on `PATH` as `model`.

```text
model [-h] [--version] {extract,emit,validate,composition,render,sync,rename,scan,doctor,animate,stamp,drawio,layers} ...
```

`--version` prints `model <version>`. `-h` or `--help` works on every command.

## Conventions

- Results go to standard output; findings, warnings and errors to standard error. `--json`, where offered, puts one JSON document on standard output.
- Nothing prompts. Nothing is overwritten that holds work you cannot regenerate, unless you say `--force`.
- Output is bounded: at most 200 findings or changes are printed, with a count of the rest. `--json` on `validate` and `scan` reports the rest as `truncated`.
- `extract`, `emit` and `validate` work out the representation from the extension: `.md`, `.markdown` or `.mdx`; `.drawio`; `.json`; `.yaml` or `.yml`.
- `--config FILE` names the binding file on every command that reads one (all but `render`, `stamp`, `drawio` and `layers`); without it the nearest one upward from the input is used. See [configuration](configuration.md#which-file-is-used).

| Exit code | Meaning |
|---|---|
| 0 | Success, or validation found nothing at or above the fail threshold |
| 1 | Validation found something at or above the threshold; `animate` could not build the page; `drawio` found no draw.io; `stamp --check` found a missing or stale record |
| 2 | Usage error, or an input could not be read |
| 3 | An external tool was missing or failed: draw.io, or a sibling skill `doctor --skill` could not find |

## doctor

Report how the skill is bound to the workspace, and what is wrong. Run it first.

```text
model doctor [--config CONFIG] [--skill SKILL] [--near NEAR] [--doc DOC] [--json]
```

| Flag | Meaning |
|---|---|
| `--skill SKILL` | Check a sibling skill's `inputs.toml` contract against `[suite.SKILL]` instead of this skill's bindings. Exit 3 if the skill cannot be found |
| `--near NEAR` | Look for the binding file upward from here instead of the working directory |
| `--doc DOC` | Also say which of this document's boxes the `[[links]]` rules resolve, and to what |
| `--json` | The report as JSON: `bindingFile`, `bindingsVersion`, `anchor`, `resolved`, `catalogues`, `catalogueIdentifiers`, `composition`, `links`, `siblings`, `issues`, `result` |

It prints the binding file, its version, the anchor folder relative paths resolve from, each catalogue and whether it exists, the number of catalogue identifiers, the patterns root and approved statuses, the link rules, the sibling skills found, and `result : ok`, `warn` or `error`. Exit 1 on `error`.

## extract

Read a model out of any representation.

```text
model extract [--config CONFIG] [--format {json,yaml,csv,yml}] [--out OUT] input
```

| Flag | Meaning |
|---|---|
| `input` | A `.md`, `.drawio`, `.json` or `.yaml` |
| `--format` | `json` (default), `yaml` or `yml`, or `csv`. CSV is one flat table of `kind,id,label,group,source,target,scenario,step` rows |
| `--out OUT` | Write here, printing a summary line, instead of to standard output |

Reading YAML needs PyYAML; writing it needs nothing.

## emit

Write a model into another representation.

```text
model emit [--config CONFIG] --to TO --out OUT [--force] input
```

| Flag | Meaning |
|---|---|
| `--to TO` | `drawio`, `markdown` (or `md`), `json`, `yaml` or `csv`. Required |
| `--out OUT` | The file to write. Required |
| `--force` | Overwrite an existing `.drawio`, discarding its layout. Without it `emit --to drawio` refuses and exits 2; use `sync` instead |

Prints `N nodes, N edges, ... -> OUT`.

## validate

Check a model, and two representations against each other.

```text
model validate [--config CONFIG] [--against AGAINST] [--json] [--fail-on {error,warn,never}] input
```

| Flag | Meaning |
|---|---|
| `input` | Any representation, usually the document |
| `--against AGAINST` | The other representation. Default: the diagram a document declares in front matter, else none, and only the single-model rules run |
| `--json` | `input`, `against`, `summary`, `abstraction`, `result`, `counts`, `findings`, `truncated`, and `composition` for a composite pattern |
| `--fail-on` | `error` (default): exit 1 on any error. `warn`: exit 1 on any finding. `never`: always exit 0 |

Prints `<file>: <summary>; abstraction <level>`, a composition summary when the scenarios run other patterns, then each finding as `severity  where: message  [rule]` and a count.

## sync

Reconcile a diagram with its document in place, keeping the layout.

```text
model sync [--config CONFIG] [--prune] [--dry-run] [--adopt] [--json] doc drawio
```

| Flag | Meaning |
|---|---|
| `doc` | The document, which owns what exists and what connects |
| `drawio` | The diagram, which owns the layout. Must exist and be uncompressed |
| `--prune` | Delete shapes with no row, instead of marking them as orphans |
| `--dry-run` | Report without writing |
| `--adopt` | Tag unidentified shapes whose label matches a row, instead of adding new ones |
| `--json` | The changes as JSON |

Prints one line per change, `action kind id detail`, where action is `add`, `update`, `rewire`, `remove`, `orphan`, `rebuild`, `adopt` or `ambig`, then `N changed in <file>` (`would change` with `--dry-run`).

## rename

Change an identifier in a document and its diagram, typically to promote a local identifier once the catalogue has an entry.

```text
model rename [--config CONFIG] [--drawio DRAWIO] [--dry-run] doc old new
```

| Flag | Meaning |
|---|---|
| `old`, `new` | The identifier now, and what it becomes. Refused if `new` is already used |
| `--drawio DRAWIO` | The diagram. Default: the one the document declares; with neither, only the document changes |
| `--dry-run` | Report without writing. Takes no value |

Front matter is never touched. A plain-number identifier is replaced only where it leads a table cell. Promoting a local identifier drops its mapping row.

## scan

Find and validate every document in a folder that declares a diagram.

```text
model scan [--config CONFIG] [--recursive] [--json] [--fail-on {error,warn,never}] folder
```

| Flag | Meaning |
|---|---|
| `--recursive` | Look in subfolders too, skipping those whose names start with `.` or `_`, and `dist` |
| `--json` | `folder`, `result`, `models` (each with `doc`, `diagram`, `summary`, `localIds`, `deckTagged`, `views`, `result`, `counts`, `findings`) and `skipped` |
| `--fail-on` | As for `validate`, over all models |

Prints one line per model, `result doc + diagram: summary; N error(s), N warning(s), N view(s)`, with up to 20 findings each, then the number of models and of documents that declare no diagram.

## composition

Print the patterns a composite pattern's scenarios run, recursively.

```text
model composition [--config CONFIG] [--json] doc
```

| Flag | Meaning |
|---|---|
| `doc` | A Markdown document |
| `--json` | `doc`, `search`, `approvedStatuses`, `summary`, `result`, `tree`, `findings` |

Exit 1 if the composition has an error. See [references/composition.md](../skills/model/references/composition.md).

## layers

List a diagram's layers, in order, with their indexes.

```text
model layers [--json] input
```

## render

Export a diagram's layers with draw.io desktop.

```text
model render --out OUT [--format FORMAT] [--layer LAYER] [--scale SCALE] [--width WIDTH] [--transparent] [--no-regions] [--theme {light,dark,auto}] [--drawio-bin DRAWIO_BIN] [--timeout TIMEOUT] input
```

| Flag | Meaning |
|---|---|
| `--out OUT` | The image to write. Required |
| `--format FORMAT` | `svg`, `png`, `pdf` or `jpg`. Default: from the `--out` extension, else `svg` |
| `--layer LAYER` | A layer name to include; repeat for several. Omit for every layer |
| `--scale SCALE` | Scale factor, passed to draw.io |
| `--width WIDTH` | Width in pixels, passed to draw.io |
| `--transparent` | Keep a transparent background (PNG, SVG) |
| `--no-regions` | Leave out the `Participating patterns` layer, which a render of the structure layer otherwise includes when the diagram has one |
| `--theme` | SVG colour scheme: `light` (default), `dark`, or `auto` to follow the viewer as draw.io does |
| `--drawio-bin PATH` | The draw.io executable. Default: `DRAWIO_BIN`, `PATH`, then the usual install folders |
| `--timeout SECONDS` | Default 120 |

Writes the image and `<image>.render.json` beside it. The draw.io command line changes between releases, so the skill reads the installed build's `--help` and passes only flags it accepts. Success is judged by the output file existing, being non-empty and having been rewritten. Exit 3 on failure.

## stamp

Record a hand-exported view against its diagram, or check a record.

```text
model stamp [--diagram DIAGRAM] [--layer LAYER] [--check] image
```

| Flag | Meaning |
|---|---|
| `image` | The exported `.svg` or `.png` |
| `--diagram DIAGRAM` | The `.drawio` it shows. Required unless `--check` |
| `--layer LAYER` | A layer the image shows; repeat for several. Each must exist in the diagram |
| `--check` | Exit 0 if the record matches the diagram as it is now; print `current`, `stale` or `none` |

## animate

Write a standalone HTML walkthrough of a document's scenarios.

```text
model animate [--config CONFIG] [--diagram DIAGRAM] [--out OUT] [--image IMAGE] [--render {auto,always,never}] [--accent ACCENT] [--interval INTERVAL] [--force] [--drawio-bin DRAWIO_BIN] doc
```

| Flag | Meaning |
|---|---|
| `doc` | The document; its declared diagram supplies the geometry |
| `--diagram DIAGRAM` | The `.drawio`, when the document declares none |
| `--out OUT` | Default: `scenarios.html` beside an `index.md`, else `<stem>-scenarios.html` |
| `--image IMAGE` | A PNG or SVG of the structure layer to use as it is |
| `--render` | `auto` (default): a current view beside the diagram, else render one if draw.io is installed. `never`: a current view or fail. `always`: render |
| `--accent #RRGGBB` | Colour for arrows and badges. Default `#D6453D` |
| `--interval SECONDS` | Seconds per step when playing. Default 3.2 |
| `--force` | Build even if validation reports errors |
| `--drawio-bin PATH` | The draw.io executable |

Prints the page, its size and the steps per scenario. Exit 1, listing every problem, when the page cannot be built; exit 3 when draw.io was needed and failed.

## drawio

Say where draw.io desktop is.

```text
model drawio [--drawio-bin DRAWIO_BIN]
```

Prints the executable's path, or `draw.io desktop not found; views must be exported by hand and stamped` and exits 1.

## Library use

`from model import load, drawio, markdown, serial, validate` works with `skills/model/src` on the path. `load(path, cfg)` returns a `Model` of `nodes`, `edges`, `groups` and `scenarios`; `model.config.load(None, near=path)` finds and reads the binding file.
