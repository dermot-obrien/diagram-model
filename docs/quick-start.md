<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Quick start

From nothing to a document, a generated draw.io diagram, a check that the two agree, a rendered view and an animated walkthrough, in about ten minutes.

You run the skill's command line yourself here, so you can see what it does. Once it is installed, your agent runs the same commands for you when you ask it to generate a diagram from a table or check a diagram against its document.

Commands are given for PowerShell (Windows) and bash (Git Bash on Windows, macOS, Linux). Where only one block is shown, it is the same in both.

## 1. Check the prerequisites

You need Python 3.11 or newer, because this guide uses a binding file (3.9 and 3.10 run the skill without one), and Git. draw.io desktop is optional: it is needed only to render images, and step 7 says what to do without it.

```
python --version
git --version
```

You should see `Python 3.11` or later and any recent Git. On macOS and Linux the command may be `python3`; use it wherever this guide says `python`.

## 2. Make a workspace and install the skill

The skill is one folder, `skills/model`, copied into a folder your agent reads skills from. `.agents/skills/` in the project is read by VS Code with GitHub Copilot, Cursor, Codex, Gemini CLI and others; the [README](../README.md#install) lists the folders for every agent, and the installers.

PowerShell:

```powershell
mkdir model-quickstart
cd model-quickstart
git clone --depth 1 https://github.com/dermot-obrien/diagram-model.git .diagram-model
New-Item -ItemType Directory -Force .agents\skills | Out-Null
Copy-Item -Recurse .diagram-model\skills\model .agents\skills\model
Remove-Item -Recurse -Force .diagram-model
```

bash:

```bash
mkdir model-quickstart && cd model-quickstart
git clone --depth 1 https://github.com/dermot-obrien/diagram-model.git .diagram-model
mkdir -p .agents/skills
cp -r .diagram-model/skills/model .agents/skills/model
rm -rf .diagram-model
```

Git prints `Cloning into '.diagram-model'...`. To pin a release instead of the latest, add `--branch model--v0.8.0` (any `model--v<version>` tag) to the clone.

The skill needs no installation of its own: `bin/model.py` runs from the copied folder with the standard library. Give it a short name for this session, run from the workspace root.

PowerShell:

```powershell
function model { python .agents\skills\model\bin\model.py @args }
model --version
```

bash:

```bash
model() { python .agents/skills/model/bin/model.py "$@"; }
model --version
```

You should see `model 0.8.0` or later.

## 3. Bind the skill to the workspace

Run `doctor` first, always. It says which binding file is in use and whether everything it names exists.

```
model doctor
```

With no binding file yet you see a warning and `result : warn`:

```text
  warn  bindings: no binding file found; built-in defaults are in use. Add .agents/skill-bindings.toml to bind this repository's layout
  binding file : (none; built-in defaults in use)
  ...
  result       : warn
```

Create the binding file. This one only names the draw.io attribute that carries each box's identifier; the table headings used below are the built-in defaults, so they need no binding.

PowerShell:

```powershell
$bindings = @'
bindingsVersion = "1.0"

[model]
node_id_attrs = ["node_id"]
'@
[IO.File]::WriteAllText("$PWD\.agents\skill-bindings.toml", $bindings)
```

bash:

```bash
cat > .agents/skill-bindings.toml <<'EOF'
bindingsVersion = "1.0"

[model]
node_id_attrs = ["node_id"]
EOF
```

`[IO.File]::WriteAllText` writes UTF-8 without a byte order mark, which every tool reads. Run `model doctor` again and it ends with `result : ok`, naming `.agents\skill-bindings.toml` as the binding file. The [configuration reference](configuration.md) has every key.

## 4. Write a document

The document is the source of truth for what exists and what connects to what. Tables under `## Components` and `## Interfaces` are nodes and edges; each `### S1 ...` under `## Scenarios` is a numbered walkthrough over them. The front matter names the diagram that goes with it.

PowerShell:

```powershell
$doc = @'
---
title: Online Shop
model:
  diagram: components.drawio
---

# Online Shop

## Components

| Component | Group |
|---|---|
| WEB Storefront | edge |
| CART Basket service | core |
| STOCK Inventory | core |
| PAY Payment provider | external |

## Interfaces

| Interface | Provider | Consumer | Purpose |
|---|---|---|---|
| IF1 | WEB | CART | add an item |
| IF2 | CART | STOCK | reserve stock |
| IF3 | CART | PAY | take payment |

## Scenarios

### S1 Checkout

| Step | Actor | Target | Action | Interface |
|---|---|---|---|---|
| 1 | WEB | CART | The shopper adds an item to the basket | IF1 |
| 2 | CART | STOCK | The basket reserves the item | IF2 |
| 3 | CART | PAY | The basket takes payment | IF3 |
'@
[IO.File]::WriteAllText("$PWD\shop.md", $doc)
```

bash:

```bash
cat > shop.md <<'EOF'
---
title: Online Shop
model:
  diagram: components.drawio
---

# Online Shop

## Components

| Component | Group |
|---|---|
| WEB Storefront | edge |
| CART Basket service | core |
| STOCK Inventory | core |
| PAY Payment provider | external |

## Interfaces

| Interface | Provider | Consumer | Purpose |
|---|---|---|---|
| IF1 | WEB | CART | add an item |
| IF2 | CART | STOCK | reserve stock |
| IF3 | CART | PAY | take payment |

## Scenarios

### S1 Checkout

| Step | Actor | Target | Action | Interface |
|---|---|---|---|---|
| 1 | WEB | CART | The shopper adds an item to the basket | IF1 |
| 2 | CART | STOCK | The basket reserves the item | IF2 |
| 3 | CART | PAY | The basket takes payment | IF3 |
EOF
```

The first word of a Component cell is its identifier and the rest its label: `WEB Storefront` is node `WEB`, labelled Storefront.

## 5. See what the skill reads

```
model extract shop.md --format csv
```

```text
kind,id,label,group,source,target,scenario,step
node,WEB,Storefront,edge,,,,
node,CART,Basket service,core,,,,
node,STOCK,Inventory,core,,,,
node,PAY,Payment provider,external,,,,
edge,IF1,add an item,,WEB,CART,,
edge,IF2,reserve stock,,CART,STOCK,,
edge,IF3,take payment,,CART,PAY,,
step,IF1,The shopper adds an item to the basket,,WEB,CART,S1,1
step,IF2,The basket reserves the item,,CART,STOCK,S1,2
step,IF3,The basket takes payment,,CART,PAY,S1,3
```

If you see no `node` rows, the headings or column names do not match what the skill expects; [troubleshooting](troubleshooting.md#the-model-is-empty) says how to fix it.

## 6. Generate the diagram and check it

```
model emit shop.md --to drawio --out components.drawio
model validate shop.md
model layers components.drawio
```

```text
  4 nodes, 3 edges, 3 groups, 1 scenario (3 steps) -> components.drawio
  shop.md: 4 nodes, 3 edges, 3 groups, 1 scenario (3 steps); abstraction mixed
  0  Structure
  1  S1 Checkout
```

`validate` found the diagram through the front matter and reported no findings, so the two agree. The diagram has a `Structure` layer with the boxes and lines, and one hidden layer per scenario with numbered badges and arrows. Open `components.drawio` in draw.io to see it: the layout is a plain grid, which you arrange by hand; the skill keeps your layout from then on. "abstraction mixed" only means the boxes are not classified; [concepts](concepts.md#abstraction) explains it.

## 7. Render a view

```
model drawio
model render components.drawio --out components.svg --layer Structure
```

```text
  C:\Program Files\draw.io\draw.io.exe
  components.svg (75 KB, svg)
  components.svg.render.json (render record; commit it with the image)
```

`model drawio` prints where draw.io desktop is, or exits 1 when it is not installed. The render record beside the image fingerprints the diagram, so anything that reads it can tell when the image is stale.

Without draw.io desktop, export the view by hand instead: open `components.drawio` in draw.io online (app.diagrams.net), hide every layer except Structure, export as SVG to `components.svg` beside the diagram, then record it:

```
model stamp components.svg --diagram components.drawio --layer Structure
```

## 8. Animate the scenario

```
model animate shop.md
```

```text
  shop-scenarios.html (119 KB; S1 3 steps). Opens from disk.
```

Open it in a browser (PowerShell `Start-Process shop-scenarios.html`; Git Bash `start shop-scenarios.html`; macOS `open`; Linux `xdg-open`). It steps through S1 on the structure view: the step's number on the acting box, an arrow to the target, everything else dimmed. Arrow keys step and space plays. The page is one self-contained file with nothing fetched.

## 9. Catch a disagreement

The check that matters is the one nobody can do by looking. Re-point interface IF3 in the document, from PAY to STOCK, without touching the diagram.

PowerShell:

```powershell
[IO.File]::WriteAllText("$PWD\shop.md", [IO.File]::ReadAllText("$PWD\shop.md").Replace("| IF3 | CART | PAY |", "| IF3 | CART | STOCK |"))
model validate shop.md
```

bash (on macOS use `sed -i ''`):

```bash
sed -i 's/| IF3 | CART | PAY |/| IF3 | CART | STOCK |/' shop.md
model validate shop.md
```

```text
  shop.md: 4 nodes, 3 edges, 3 groups, 1 scenario (3 steps); abstraction mixed
  error  IF3: IF3 is CART->STOCK in the document but CART->PAY on the diagram  [step_endpoint_mismatch]
  1 error(s), 0 warning(s)
```

The summary line goes to standard output and the findings to standard error. The exit code is 1, so a build fails on it. Put it back:

PowerShell:

```powershell
[IO.File]::WriteAllText("$PWD\shop.md", [IO.File]::ReadAllText("$PWD\shop.md").Replace("| IF3 | CART | STOCK |", "| IF3 | CART | PAY |"))
```

bash:

```bash
sed -i 's/| IF3 | CART | STOCK |/| IF3 | CART | PAY |/' shop.md
```

## 10. Change the document and sync the diagram

Add an email service, the interface to it and a fourth step. Open `shop.md` and add these three rows at the ends of the Components, Interfaces and S1 tables:

```markdown
| MAIL Email service | external |
| IF4 | CART | MAIL | send the receipt |
| 4 | CART | MAIL | The basket emails the receipt | IF4 |
```

Or run this, which makes the same edit.

PowerShell:

```powershell
$t = [IO.File]::ReadAllText("$PWD\shop.md")
$t = $t.Replace("| PAY Payment provider | external |", "| PAY Payment provider | external |`n| MAIL Email service | external |")
$t = $t.Replace("| IF3 | CART | PAY | take payment |", "| IF3 | CART | PAY | take payment |`n| IF4 | CART | MAIL | send the receipt |")
$t = $t.Replace("| The basket takes payment | IF3 |", "| The basket takes payment | IF3 |`n| 4 | CART | MAIL | The basket emails the receipt | IF4 |")
[IO.File]::WriteAllText("$PWD\shop.md", $t)
```

bash:

```bash
cat > edit.py <<'EOF'
t = open("shop.md", encoding="utf-8").read()
t = t.replace("| PAY Payment provider | external |\n", "| PAY Payment provider | external |\n| MAIL Email service | external |\n")
t = t.replace("| IF3 | CART | PAY | take payment |\n", "| IF3 | CART | PAY | take payment |\n| IF4 | CART | MAIL | send the receipt |\n")
t = t.replace("| The basket takes payment | IF3 |\n", "| The basket takes payment | IF3 |\n| 4 | CART | MAIL | The basket emails the receipt | IF4 |\n")
open("shop.md", "w", encoding="utf-8", newline="\n").write(t)
EOF
python edit.py && rm edit.py
```

Now the document says more than the diagram:

```
model validate shop.md
```

```text
  shop.md: 5 nodes, 4 edges, 3 groups, 1 scenario (4 steps); abstraction mixed
  warn  MAIL: MAIL is in the document but not on the diagram  [doc_not_in_diagram]
  warn  IF4: IF4 is in the document but no connector carries it  [doc_not_in_diagram]
  0 error(s), 2 warning(s)
```

Warnings exit 0; add `--fail-on warn` to make them fail. Bring the diagram up to date without losing its layout, dry run first:

```
model sync shop.md components.drawio --dry-run
model sync shop.md components.drawio
```

```text
  add      node  MAIL  placed below the existing shapes
  add      edge  IF4  CART -> MAIL
  rebuild  scen  S1  4 step(s)
  3 changed in components.drawio
```

`emit` would refuse here, because `components.drawio` exists and overwriting it would discard your arrangement; `sync` edits it in place.

## 11. Keep the views current

The image rendered in step 7 now shows an old diagram, and the render record knows:

```
model stamp --check components.svg
```

```text
  stale   components.svg <- components.drawio ['Structure']
```

Re-render, re-animate and check the whole folder:

```
model render components.drawio --out components.svg --layer Structure
model animate shop.md
model scan .
```

```text
  components.svg (94 KB, svg)
  components.svg.render.json (render record; commit it with the image)
  shop-scenarios.html (144 KB; S1 4 steps). Opens from disk.
  ok    shop.md + components.drawio: 5 nodes, 4 edges, 3 groups, 1 scenario (4 steps); 0 error(s), 0 warning(s), 2 view(s)
  1 model(s); 0 document(s) declare no diagram
```

## What you have

```text
model-quickstart/
├── .agents/
│   ├── skill-bindings.toml      how this workspace binds the skill
│   └── skills/model/            the skill
├── shop.md                      the document: what exists and what connects
├── components.drawio            the diagram: the layout
├── components.svg               a rendered view of the Structure layer
├── components.svg.render.json   its fingerprint
└── shop-scenarios.html          the walkthrough
```

## Next

- Ask your agent: "check components.drawio matches shop.md", or "generate a diagram from the tables in this document". It reads `SKILL.md` and runs these commands.
- Bind your own table headings, identifier patterns and catalogues: [configuration](configuration.md).
- Learn the ideas behind the commands: [concepts](concepts.md).
- Every command and flag: [commands](commands.md).
- A larger worked example: [examples](examples.md).
