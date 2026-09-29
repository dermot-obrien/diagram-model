<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Semantic versions, with the contract defined as: MAJOR for a changed skill `name`, a removed command, a changed CLI interface or a changed model schema; MINOR for new commands, adapters or rules; PATCH for wording and fixes.

## [0.8.0] - 2026-09-30

### Added

- Composing patterns. A scenario step's optional `Uses` cell runs a scenario of another pattern, `PAT-905 S1`, or marks an open participating pattern, not yet written, `TBD <name>`. The pattern holding such steps is a composite pattern, and each participation step stands for the participating pattern's whole flow: its Actor and Target, both required, are where that flow enters and leaves, and its Interface is optional. `Step.uses` carries it, serialised when set. Steps without Uses and documents without the column are unchanged.
- The header is the scenario column contract's `uses`, default `Uses`. `[model]` gains `patterns_root`, `pattern_id` (default `[A-Z]{2,5}-[0-9]{3}`) and `approved_statuses` (default Final, Approved, Active, Published); `[suite.pattern] patternsRoot`, `approvedStatuses` and then `outputDir` are read when `[model]` sets none.
- A participating pattern is a folder named `<ID>-<slug>` holding `index.md`, or, when no folder is named for the id, a document whose first H1 starts with it, found under the bound root or, unbound, in the folders above the composite pattern.
- Rules `uses_invalid`, `uses_step_endpoints`, `participant_missing`, `participant_scenario_missing`, `composition_cycle` and `participant_unapproved` (errors), and `participant_join`, `participant_open`, `participant_ambiguous` and `step_uses_mismatch` (warnings). The join check matches the participating scenario's first actor to the step's Actor, and its last step's actor or target to the step's Target, by catalogue id directly or through either document's Catalogue Mapping. The approval gate fails an approved composite pattern that rests, at any depth, on an unapproved participating pattern or a `TBD`.
- `model composition <doc> [--json]` prints the composition tree: each participation step, the participating pattern's id, scenario and status, open participating patterns, recursively, with cycles marked. `validate` prints a one-line summary and adds `composition` to `--json`. `doctor` reports the patterns root in use and the approved statuses, and fails on a bound root that does not exist.
- draw.io: the overlay arrow of a participation step carries `uses`, is labelled with what it runs and is drawn heavier and dash-dotted, overridable as `style.flow_uses`. `emit`, `sync` and `validate` handle it.
- The walkthrough draws a participation step as one dash-dotted arrow with a drill-in badge. The badge, a link beside the steps and the D key open the participating pattern's walkthrough at that scenario, by a relative link carrying the way back as `?back=`; that page links back to the composite pattern, and B returns to the step. Any walkthrough opens at `#S1` or `#S1-3`. An open participating pattern has a badge and no link. Still one file that opens from disk, and its script holds nothing a deck's asset scan reads as a file, so a markdown-deck `deck:html` slide embeds it without warnings.
- Grounding: a participation step is BPMN 2.0.2's call activity, and UML InteractionUse (a `ref` fragment) in a sequence diagram; a scenario's declared start and finish are BPMN start and end events, UML 2.5.1 ports; a role binding and a participating pattern's region are UML 2.5.1's collaboration use.
- A scenario may declare `Start: <box>` and `Finish: <box>` on their own lines under its heading, before its steps table, blank lines and narrative allowed. `Scenario.start` and `finish` carry them, serialised when set. Rule `scenario_start_finish` (error): the Start is the first step's actor, the Finish the last step's actor or target, and both are boxes of the pattern. A composite pattern joins to a participating scenario's declared start and finish when it has them, and the composition tree and its JSON (`join`) say which ends were declared.
- Role binding: a parenthesised group of `id=id` pairs directly after the scenario key, `PAT-005 S1 (02=ABB-011, 04=ABB-024)`, maps the participating pattern's boxes to the composite pattern's. `Step.binding` carries it, serialised when set, and the composition JSON includes it. Rule `participant_binding` (error): each left box is in the participating pattern, each right box in the composite, and each box at most once on a side. The join matches through the binding first, which makes local ids joinable across patterns. A TBD with a binding, or a group holding `=` that is not all `id=id` pairs, is `uses_invalid`.
- Participating patterns' regions. `emit` and `sync` keep a `Participating patterns` layer: one dashed, rounded, unfilled region per distinct participating pattern and per open one, labelled with its id and name or `Open: <name>`, carrying `participant`, and enclosing the boxes bound to it with padding that grows per region. Not containers; `sync` recomputes them from the boxes' absolute positions and removes one no step runs. `style.region` overrides the style. `validate` reports a missing or extra region as `step_uses_mismatch`.
- `render` of the structure layer includes the regions layer by default when there is one, and records it; `--no-regions` leaves it out. `animate` accepts a view with or without the regions and measures positions from whichever extent the view shows.
- Links from declared identifiers to their pages. `[model] link_site` and `link_target` (`new`, the default, or `same`), and `[[links]]` rules of `match` (a full-match regex on the id), optional `locate` (a glob relative to the binding file, `{id}` substituted, first match wins), `href` (a template of `{id}`, `{site}`, `{located}` and `{rel}`) and optional `target`, tried in order. Local ids are never linked. Rule `link_unresolved` (warn) when a rule matches but `locate` finds nothing its href needs; an invalid target is a configuration error. The walkthrough draws a hotspot over each linked box, links Actor and Target names in the steps list and the pop-up, and links a participating pattern's id beside its drill-in, all built with `setAttribute` so the page stays embed-safe. `emit` and `sync` set draw.io's `link` and `linkTarget` on a resolved box and remove it when its rule no longer resolves. `doctor` lists the rules, and `--doc` says which of a document's boxes resolve. New module `links.py`.
- BPMN's call-activity marker: the overlay arrow is labelled `[+] 2: PAT-905 S1` (ASCII, since a boxed-plus glyph falls back to an empty box in draw.io's export), and the walkthrough's drill-in badge, the steps list and the link beside them draw a small boxed plus in SVG and CSS, greyed and without a link for an open participating pattern. The overlay arrow's label has a white background.
- `bundle.json`, the bundle manifest DD-11 of AI-Assisted Work defines: the `model` skill, its purl, its requirements (none), and `python bin/model.py doctor` as its post-install check, which already meets the contract (exit 0 when the bindings resolve, 1 with one line per problem). The marketplace is its `claude-plugin` adapter.
- CI validates `bundle.json` with `scripts/validate-bundle.mjs`, and runs the check in an empty workspace as an installer would. The validator and the schema are copies from AI-Assisted Work, in `scripts/` and `scripts/vendor/`, so CI needs no network.

## [0.7.0] - 2026-09-29

### Added

- Sibling discovery reads requirements as Package URLs with a range, `pkg:generic/<owner>/<bundle>/<skill> ^0.7.0`, as DD-11 of AI-Assisted Work sets out, as well as the older `name@range`. `requirement_name` is importable. Tests cover both forms.

### Changed

- The skill's identifier is `pkg:generic/dermot-obrien/diagram-model/model`, and releases are tagged `model--v<version>`, named after the skill rather than the repository.
- The marketplace defines one package per skill: install it as `model@diagram-model`, not `diagram-model@diagram-model`. CI checks each skill's versions agree.

## [0.6.0] - 2026-09-29

Extracted from AI-Assisted Work, where it was `skills/model`, into its own repository, https://github.com/dermot-obrien/diagram-model, so it can be installed and used without that framework. The `pattern` skill, in https://github.com/dermot-obrien/architecture-pattern, and the skills of AI-Assisted Architecture depend on it. NOTICE records the source commit, and the history before this entry is the history of that path in AI-Assisted Work.

### Changed

- Sibling discovery, which `doctor` reports and the `pattern` skill relies on, now looks beyond the directory this skill is installed in, because agents disagree about where skills go: each directory on `AGENT_SKILLS_PATH`, and then, for a skill some sibling declares in `metadata.x-skill-requires` but that is not there, every directory an agent reads skills from. That is the project's `.agents/skills`, `.github/skills`, `.cursor/skills`, `.claude/skills` and `.codex/skills`, the user's `~/.agents/skills`, `~/.copilot/skills`, `~/.cursor/skills`, `~/.claude/skills`, `~/.gemini/skills` and `~/.codex/skills`, and the skills of installed Claude Code plugins. A dependency installed by a different tool, such as `markdown-deck` in `.github/skills` beside a `pattern` in `.agents/skills`, was not found before.
- Licensed as AI-Assisted Work licenses its skills: content under CC BY 4.0 and code under Apache-2.0, declared per file in `REUSE.toml`. The skill directory carries `LICENSE`, both licence texts and `NOTICE`.
- `find_skill`, and `doctor --skill NAME` through it, find the named skill in all of those places too, so `doctor --skill pattern` works when `pattern` was installed by a different tool from `model`. It looked only beside `model`.
- The repository is a Claude Code plugin and a one-plugin marketplace, `diagram-model@diagram-model`, so other plugins can depend on it by version range. The plugin is named for the repository; the skill is still `model`, so every skill and repository that calls `model` keeps working.
- `metadata.homepage` names this repository, and `metadata.x-derived-from` names the source commit in AI-Assisted Work.

### Removed

- `scripts/pack-repo.py`. It assembled a standalone repository from the framework's copy; this repository is now the master.

### Added

- `tests/test_discovery.py`, covering a dependency in the same directory, installed by a different tool, on `AGENT_SKILLS_PATH` and as a Claude Code plugin.
- `scripts/validate-skills.mjs`, CI running it with the tests on Linux and Windows, a REUSE compliance check, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` and `SECURITY.md`.

## [Unreleased]

## [0.5.0] - 2026-09-26

### Added

- draw.io desktop is optional. `animate --render auto` (the default) draws on a current view beside the diagram, `<stem>.svg` or `<stem>.png` with a render record matching the diagram, and asks draw.io to render only when there is none; without draw.io it stops and names the file to export and stamp. `--render never` never calls draw.io; `--render always` always does. `--image` accepts an SVG as well as a PNG, and an SVG is embedded as SVG.
- `stamp <image> --diagram DRAWIO [--layer NAME]` writes the render record for a view exported by hand, from draw.io desktop or online, so it is checked for staleness like a rendered one. `stamp --check <image>` exits 0 when it is current.
- `drawio` prints where draw.io desktop is, and exits 1 when it is not installed, so a caller can choose between rendering and requiring committed views.
- `render.available()`, the non-raising form of `find_binary`.

## [0.4.1] - 2026-09-26

### Fixed

- `animate` wrote a different page on every run from the same document and diagram, because it iterated a set of node identifiers and Python randomises string hashing per process. Anything embedding the page, such as a deck slide, changed with it. Nodes are now written in sorted order, and a test runs `animate` under three hash seeds and requires identical bytes.

## [0.4.0] - 2026-09-26

### Added

- Derived abstraction. `validate` reports whether a model is conceptual, logical, physical or mixed, in its summary line and as `abstraction` in `--json`, computed from the kinds of box and never declared. A catalogue binding may carry `level = "logical"` or `"physical"`; a local id counts as conceptual; a table's optional `kind` column can mark a box `product`, `external`, `context`, `local` or a level outright, and external boxes are ignored. `validate.abstraction`, `validate.node_level` and `validate.catalogue_levels` expose it to library callers. An unknown `level` in the binding is refused.

## [0.3.0] - 2026-09-25

### Added

- `animate <doc>`: a step-through animation of a document's scenarios as one standalone HTML file that opens from disk with no server. Each step puts its number on the acting shape, draws an arrow to the target, dims the rest, zooms to the step and shows the narrative with the interface's purpose and spare columns. Names, narratives and interface details come from the document; geometry and each step's endpoints come from the diagram, with positions inside groups and containers made absolute. The structure layer is rendered by draw.io unless `--image` supplies it. It validates first and fails rather than guesses: a step without narrative, an endpoint without a shape, a scenario on one side only, or a rendered view whose proportions differ from the shapes' extent is an error. `--accent`, `--interval` and `--force` adjust it.
- `render --theme light|dark|auto`, for SVG. `light` is the default.

### Fixed

- An SVG from `render` no longer changes with the viewer's colour scheme. draw.io writes light-dark() colours on a transparent background, so an embedded diagram went dark on a dark-mode machine while the page around it stayed light. `render` now passes `--svg-theme` where the installed draw.io accepts it and pins the root element's `color-scheme` afterwards either way, so older builds get the same result, and gives a light SVG a white background unless `--transparent` is set. `render.pin_svg_theme` applies the same fix to an SVG already on disk.
- `doctor` no longer reports a templated path binding as missing. A binding carrying a `{placeholder}`, such as `planning/{quarter}/basis.csv`, names a different location per run, so the directory in front of the first placeholder is checked and the rest is left to the skill that fills it.

## [0.2.0] - 2026-09-25

Local ids may be plain numbers: `local_pattern = '[0-9]{1,3}'` reads `01 Gateway` as local id `01`. A local id must lead its cell, so a number inside a name is never one, and its draw.io cell id is `local-01`, since draw.io's own cells `0` and `1` would collide with local nodes `0` and `1`. `rename` never touches front matter, checks clashes against the model's identifiers rather than raw text, and replaces a plain-number id only where it leads a table cell. `local_prefix` still works.


Several models in one folder, and local identifiers beside catalogued ones.

### Added

- A render record. `render` writes `<image>.render.json` beside each image: the source diagram, a SHA-256 of it with CRLF normalised to LF so a Windows checkout and a Linux runner agree, and the layers. `render.check_record` says whether an image is still current. The record is a file convention, so a consumer needs no dependency on this skill.
- `model:` front matter, naming a document's diagram. A folder can now hold several models, each a document plus the diagram it declares. `validate` uses the declared diagram when `--against` is absent.
- `scan <folder>`, which finds every declared model, validates each against its diagram, qualifies local ids by document, and lists the views to render as `<stem>.svg` and `<stem>-sN.svg`.
- `local_prefix` and `local_attr` bindings. Identifiers carrying the reserved prefix are local to their document: exempt from the catalogue check, written to their own draw.io attribute, and mapped onto the catalogue in a `Catalogue Mapping` table.
- Mapping rules: `mapping_missing`, `mapping_unknown_local`, `mapping_invalid`, `mapping_not_in_catalogue`, `mapping_duplicates_node`.
- `id_attr_mismatch`, so a local id can never pass for a catalogue one on the diagram, nor the reverse.
- `rename <doc> OLD NEW`, which promotes or corrects an identifier across the document and the diagram, following every cell reference.
- `sync --adopt`, which tags unidentified shapes and connectors whose label names a row, keeping geometry and formatting. It is how a hand-drawn diagram joins a model.
- A standard-library test suite under `tests/`.

### Changed

- A table cell that no identifier rule matches is reported as `id_unmatched`. It was silently dropped, so a table written with the wrong prefix produced an empty model and no finding.
- The draw.io attribute for a catalogued id is chosen by its prefix, so an SBB id is written to `sbb_id` rather than always to the first declared attribute.
- `sync` resolves identifiers to cell ids before wiring edges and overlays, so a copy-pasted or adopted shape whose cell id differs from its identifier is still connected correctly.
- `sync` no longer rewrites a label whose first line or leading bold run already names the row.
- `validate --against` also runs the duplicate, attribute and endpoint rules over the diagram, not only over the document.

### Fixed

- `render` crashed printing its result when the output was on a different Windows drive from the working directory. The file had been written; only the report failed.

## [0.1.0] - 2026-09-25

First release. Commands: `extract`, `emit`, `validate`, `sync`, `render`, `layers`, `doctor`.

### Added

- A generic canonical model of nodes, edges, groups and scenarios, with no domain vocabulary. Anything expressible as boxes and lines fits it.
- Markdown adapter, reading and writing GFM tables against a contract declared in config rather than hardcoded. HTML comments are stripped first, so template guidance never becomes model content.
- draw.io adapter, reading and writing. Handles compressed and uncompressed pages and both `object` and `UserObject` wrappers. Identifiers live on the object wrapper because mxCell ids do not survive copy and paste.
- Scenario overlays generated from a steps table, as draw.io layers. Contiguity and endpoint agreement hold by construction.
- JSON, YAML and CSV serialisation. YAML is written with a small stdlib writer; only reading YAML needs PyYAML.
- Thirteen validation rules, each with a configurable severity, covering the model alone, the catalogue, and the agreement between two representations.
- `catalogue_unreadable`, which fails loudly when a declared catalogue is missing, has the wrong column or is empty. Without it the catalogue check failed open: a wrong path was read as an absence, so `not_in_catalogue` set to `error` quietly passed everything. That is the failure mode of installing the skill into a repository with a different layout, which is the case it most needs to catch.
- `sync`, which reconciles a diagram with its document while preserving geometry. The document owns what exists and what connects; the diagram owns where things sit. Shapes without a recognised identifier, such as bands, legends and annotations, are never touched. Scenario overlays are derived, so they are rebuilt rather than reconciled.
- `render`, which probes the installed draw.io build via its own `--help` and passes only the flags it accepts. Version 29.7 dropped `--disable-update` and `--timeout`, which older documentation still lists, and an unknown flag breaks argument parsing with an error that blames the input file.

- `doctor`, which resolves every binding to an absolute path and says what does not resolve. `--skill NAME` checks a sibling's `inputs.toml` contract instead, so a skill with no runtime of its own borrows this resolver rather than asking the agent to read a config file. Agents skip preconditions often enough to measure, and a broken path reference inside a SKILL.md raises nothing at all.
- `.agents/skill-bindings.toml` as the preferred config name, with `model.toml` kept as an alias. One file binds the whole suite; `[suite.<name>]` sections belong to the other skills.
- `bindingsVersion`, refused when its major is unknown. There is no version-skew defence anywhere in the skills ecosystem, so this is ours.
- Path bindings may be pinned with a sibling `<name>Sha256`, so a shared artefact vendored once into the repository is held to the version that was reviewed. An absolute path in a committed binding is warned about, because it will not survive a clone on another machine.

### Known limitations

- Generated layout is a mechanical grid. Every box and arrow is present and correctly identified, but routing overlaps and edge labels collide where several interfaces converge on one component. Arranging the diagram is the author's job; `sync` preserves that work.
- `emit --to drawio` refuses to overwrite an existing diagram, because that would discard the layout. Use `sync`.
- `sync` needs an uncompressed .drawio and says so with the command to normalise one.
