<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Linking boxes to their pages

Part of the `model` skill; [SKILL.md](../SKILL.md) summarises it.

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
