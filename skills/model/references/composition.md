<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Composing patterns

Part of the `model` skill; [SKILL.md](../SKILL.md) summarises it.

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
