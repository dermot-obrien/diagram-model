# SPDX-License-Identifier: Apache-2.0
"""Pattern chaining: a scenario step that calls a scenario of another pattern.

A step whose Uses cell reads `PAT-905 S1` stands for the whole of that child flow. Its
Actor and Target are the boxes where the child flow enters and leaves the parent, so the
parent stays one readable walkthrough while each child is solved, reviewed and approved
as its own pattern. `TBD <name>` marks a child flow not yet written: a high-level pattern
can be sketched first and its children filled in later.

What is checked, and why each is what it is:

    child not found, scenario not found, a cycle    errors: the chain does not resolve
    entry or exit box that cannot be matched        a warning: a conceptual sketch may
                                                    use different local roles
    TBD                                             a warning: open, listed, not wrong
    approved parent over an unapproved child        an error: an approved pattern cannot
                                                    rest on unapproved or unwritten work

Where children are found. A bound root, `[model] patterns_root`, else `[suite.pattern]
patternsRoot`, else `[suite.pattern] outputDir`, is searched to any depth. With none,
each folder from the parent document's own upward is searched two levels deep, and the
first that holds the id wins; the search stops at the repository root (a folder holding
`.git` or the binding file) and after eight levels. A child is a folder whose name
starts with `<ID>-` and holds index.md, or, when no folder is named for the id, a
document whose first H1 starts with it.

Nothing here runs for a document without a Uses column, so existing documents are
untouched by it.
"""
from __future__ import annotations

import os
import re

from . import config as config_mod
from . import markdown
from .validate import Finding

MD_EXT = (".md", ".markdown", ".mdx")
SKIP_DIRS = {"node_modules", "dist", "build"}
ANCESTOR_DEPTH = 2          # levels below each ancestor searched when no root is bound
ANCESTOR_LIMIT = 8          # ancestors tried before giving up
MAX_DEPTH = 25              # chain depth at which the tree stops expanding
H1_RE = re.compile(r"^#\s+(.+?)\s*#*\s*$")


def _key(path) -> str:
    return os.path.normcase(os.path.abspath(path))


def calls(m, cfg) -> list:
    """(scenario, step, parsed) for every step of a model that has a Uses value."""
    out = []
    for sc in m.scenarios:
        for st in sc.steps:
            if st.uses:
                out.append((sc, st, markdown.parse_uses(st.uses, cfg)))
    return out


class Doc:
    __slots__ = ("path", "model", "cfg", "id", "title", "status")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def _h1(path, limit=65536) -> str:
    """The text of a document's first H1, outside front matter and code fences."""
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read(limit)
    except (OSError, UnicodeDecodeError):
        return ""
    _meta, body = markdown.front_matter(raw)
    fenced = False
    for ln in markdown._clean(body).split("\n"):
        if markdown.FENCE_RE.match(ln):
            fenced = not fenced
            continue
        if not fenced:
            m = H1_RE.match(ln)
            if m:
                return m.group(1).strip()
    return ""


class Resolver:
    """Finds child patterns by id and loads documents, each once per run."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.pid = re.compile(cfg.pattern_id or config_mod.DEFAULT_PATTERN_ID)
        self._index = {}
        self._docs = {}
        self._cfgs = {}

    # ------------------------------------------------------------------ settings

    @property
    def root(self) -> str:
        return self.cfg.resolve(self.cfg.patterns_root) if self.cfg.patterns_root else ""

    def approved(self, status) -> bool:
        s = str(status or "").strip().lower()
        return bool(s) and s in {a.strip().lower() for a in self.cfg.approved_statuses}

    def describe(self) -> dict:
        """Where children are looked for, for doctor and the chain report."""
        if self.root:
            return {"patternsRoot": self.root, "from": self.cfg.patterns_root_from,
                    "exists": os.path.isdir(self.root)}
        return {"patternsRoot": "", "from": "ancestors of each document, two levels deep",
                "exists": None}

    # ------------------------------------------------------------------ finding

    def _id_in(self, text) -> str:
        m = self.pid.match(text or "")
        if m and not re.match(r"[A-Za-z0-9]", text[m.end():m.end() + 1] or " "):
            return m.group(0)
        return ""

    def index(self, root, depth=None) -> dict:
        """{pattern id: [document paths]} under root, to `depth` levels, None for all."""
        k = (_key(root), depth)
        if k in self._index:
            return self._index[k]
        folders, headed = {}, {}

        def add(into, pid, path):
            lst = into.setdefault(pid, [])
            if all(_key(p) != _key(path) for p in lst):
                lst.append(os.path.abspath(path))

        base = os.path.abspath(root)
        if os.path.isdir(base):
            for d, dirs, files in os.walk(base):
                rel = os.path.relpath(d, base)
                level = 0 if rel == "." else rel.count(os.sep) + 1
                dirs[:] = sorted(x for x in dirs if not x.startswith((".", "_"))
                                 and x not in SKIP_DIRS)
                if depth is not None and level >= depth:
                    dirs[:] = []
                if level:
                    pid = self._id_in(os.path.basename(d))
                    if pid and "index.md" in files:
                        add(folders, pid, os.path.join(d, "index.md"))
                for f in sorted(files):
                    if f.lower().endswith(MD_EXT):
                        pid = self._id_in(_h1(os.path.join(d, f)))
                        if pid:
                            add(headed, pid, os.path.join(d, f))
        # `<ID>-slug/index.md` is the convention and wins outright. A pattern's folder often
        # holds further documents whose H1 repeats its id, so an H1 counts only for an id
        # that no folder claims.
        found = {pid: sorted(lst) for pid, lst in folders.items()}
        for pid, lst in headed.items():
            if pid not in found:
                found[pid] = sorted(lst)
        self._index[k] = found
        return found

    def _stop_at(self) -> set:
        stops = set()
        if self.cfg.path:
            d = os.path.dirname(self.cfg.path)
            stops.add(_key(os.path.dirname(d) if os.path.basename(d) == ".agents" else d))
        return stops

    def find(self, pid, near) -> tuple:
        """(paths, where searched) for a pattern id, from the document at `near`."""
        if self.root:
            return self.index(self.root).get(pid, []), self.root
        stops = self._stop_at()
        d = os.path.dirname(os.path.abspath(near))
        for _ in range(ANCESTOR_LIMIT):
            hit = self.index(d, ANCESTOR_DEPTH).get(pid, [])
            if hit:
                return hit, d
            if _key(d) in stops or os.path.exists(os.path.join(d, ".git")):
                break
            up = os.path.dirname(d)
            if up == d:
                break
            d = up
        return [], f"the folders above {os.path.basename(os.path.dirname(os.path.abspath(near)))}"

    # ------------------------------------------------------------------ loading

    def cfg_for(self, path):
        found = config_mod.find(path)
        k = _key(found) if found else ""
        if self.cfg.path and k == _key(self.cfg.path):
            return self.cfg
        if k not in self._cfgs:
            self._cfgs[k] = config_mod.load(found) if found else config_mod.default_config()
        return self._cfgs[k]

    def load(self, path, model=None) -> Doc:
        k = _key(path)
        if k in self._docs:
            return self._docs[k]
        cfg = self.cfg_for(path)
        m = model if model is not None else markdown.read(path, cfg)
        meta = markdown.read_meta(path)
        h1 = _h1(path)
        pid = self._id_in(h1) or self._id_in(os.path.basename(os.path.dirname(os.path.abspath(path))))
        title = h1[len(pid):].strip(" :-") if pid and h1.startswith(pid) else (h1 or str(meta.get("title", "")))
        status = meta.get("status", "")
        doc = Doc(path=os.path.abspath(path), model=m, cfg=cfg, id=pid, title=title,
                  status=status if isinstance(status, str) else "")
        self._docs[k] = doc
        return doc


# ---------------------------------------------------------------------- the tree

def _brief(d: Doc, r: Resolver) -> dict:
    return {"doc": d.path, "id": d.id, "title": d.title, "status": d.status,
            "approved": r.approved(d.status), "calls": []}


def tree(path, cfg=None, resolver=None, model=None) -> dict:
    """The chain below one document: its Uses steps, each child, recursively.

    Every call records what it names and what was found. A child already on the path
    from the top is marked `cycle` and not expanded again.
    """
    r = resolver or Resolver(cfg or config_mod.load(None, near=path))
    return _node(os.path.abspath(path), r, [], 0, model)


def _node(path, r, stack, depth, model=None) -> dict:
    d = r.load(path, model)
    node = _brief(d, r)
    here = stack + [_key(path)]
    for sc, st, (val, kind, pid, skey, name) in calls(d.model, d.cfg):
        call = {"scenario": sc.key, "step": st.step, "uses": val, "kind": kind,
                "actor": st.actor, "target": st.target}
        if kind == "tbd":
            call["name"] = name
        elif kind == "ref":
            call.update({"id": pid, "key": skey})
            paths, where = r.find(pid, path)
            call["found"] = bool(paths)
            if not paths:
                call["searched"] = where
            else:
                child = paths[0]
                if len(paths) > 1:
                    call["candidates"] = paths
                cd = r.load(child)
                call["scenarioFound"] = cd.model.scenario(skey) is not None
                if _key(child) in here:
                    call["cycle"] = True
                    call["child"] = _brief(cd, r)
                elif depth >= MAX_DEPTH:
                    call["truncated"] = True
                    call["child"] = _brief(cd, r)
                else:
                    call["child"] = _node(child, r, here, depth + 1)
        node["calls"].append(call)
    return node


def walk(node, trail=()):
    """(node, call, trail) for every call in the tree, depth first. `trail` is the ids
    and calls from the top down to the node holding the call."""
    for call in node.get("calls", []):
        yield node, call, trail
        child = call.get("child")
        if child and not call.get("cycle") and not call.get("truncated"):
            yield from walk(child, trail + ((node, call),))


def summary(t: dict) -> dict:
    direct = len(t.get("calls", []))
    patterns, opened, cycles, missing, depth = set(), 0, 0, 0, 0
    for _node_, call, trail in walk(t):
        depth = max(depth, len(trail) + 1)
        if call["kind"] == "tbd":
            opened += 1
        if call.get("cycle"):
            cycles += 1
        if call["kind"] == "ref" and not call.get("found"):
            missing += 1
        if call.get("child"):
            patterns.add(_key(call["child"]["doc"]))
    return {"callouts": direct, "patterns": len(patterns), "open": opened,
            "cycles": cycles, "missing": missing, "depth": depth}


def summary_line(s: dict) -> str:
    parts = [f"{s['callouts']} call-out(s) to {s['patterns']} pattern(s)",
             f"depth {s['depth']}"]
    if s["open"]:
        parts.append(f"{s['open']} open (TBD)")
    if s["missing"]:
        parts.append(f"{s['missing']} not found")
    if s["cycles"]:
        parts.append(f"{s['cycles']} cycle(s)")
    return "chain: " + ", ".join(parts)


def render(t: dict) -> list:
    """The tree as indented text lines."""
    def head(n):
        name = " ".join(x for x in (n["id"], n["title"]) if x) or os.path.basename(n["doc"])
        return f"{name} [{n['status'] or 'no status'}]"

    lines = [head(t)]

    def rec(n, pad):
        for c in n.get("calls", []):
            at = f"{c['scenario']} step {c['step']}"
            if c["kind"] == "tbd":
                lines.append(f"{pad}{at} -> {c['uses']}  (open)")
            elif c["kind"] == "invalid":
                lines.append(f"{pad}{at} -> '{c['uses']}'  (not a call)")
            elif not c.get("found"):
                lines.append(f"{pad}{at} -> {c['uses']}  (not found under {c.get('searched')})")
            else:
                ch = c["child"]
                note = ""
                if not c.get("scenarioFound"):
                    note += f"  (no scenario {c['key']})"
                if c.get("cycle"):
                    note += "  (cycle)"
                if c.get("truncated"):
                    note += "  (too deep; not expanded)"
                lines.append(f"{pad}{at} -> {c['key']} of {head(ch)}{note}")
                if not c.get("cycle") and not c.get("truncated"):
                    rec(ch, pad + "    ")

    rec(t, "  ")
    return lines


# ---------------------------------------------------------------------- findings

def _add(out, cfg, rule, message, where=""):
    sev = cfg.severity(rule)
    if sev != "off":
        out.append(Finding(rule, sev, message, where))


def _canon(model, cfg, ident) -> set:
    """What a box is, across documents. A catalogued id is itself; a local id is
    document-scoped, so it means only the catalogue ids its mapping rows name."""
    if not ident:
        return set()
    if cfg.is_local(ident):
        return {r["maps_to"] for r in model.attrs.get("mapping", [])
                if r.get("local") == ident and r.get("maps_to")}
    return {ident}


def _named(model, ident) -> str:
    n = model.node(ident)
    return f"{ident} {n.label}".strip() if n and n.label else ident


def _join(out, cfg, where, parent: Doc, box, child: Doc, cboxes, pid, skey, side):
    """Warn when none of the child's candidate boxes corresponds to the parent's box.

    Entry has one candidate, the first step's actor. Exit has two, the last step's actor
    and its target, because a flow often ends with the exit box making a final call to a
    helper: `Facade -> Policy engine: authorise` leaves at the facade."""
    cboxes = [c for i, c in enumerate(cboxes) if c and c not in cboxes[:i]]
    if not box or not cboxes:
        return
    mine = _canon(parent.model, parent.cfg, box)
    if any(mine & _canon(child.model, child.cfg, c) for c in cboxes):
        return
    verb = "enters" if side == "entry" else "leaves"
    there = " or ".join(_named(child.model, c) for c in cboxes)
    _add(out, cfg, "chain_join",
         f"{pid} {skey} {verb} at {there} there, which cannot be matched to "
         f"{_named(parent.model, box)} here. Map the local box in Catalogue Mapping to the "
         f"catalogue id it realises, or use the same catalogue id in both patterns", where)


def findings(m, cfg, resolver=None) -> list:
    """Every chain finding for one document. Empty, and nothing read, without Uses."""
    if not any(st.uses for sc in m.scenarios for st in sc.steps):
        return []
    src = m.source or ""
    if not (src.lower().endswith(MD_EXT) and os.path.isfile(src)):
        return []
    r = resolver or Resolver(cfg)
    t = tree(src, resolver=r, model=m)
    parent = r.load(src)
    out = []

    for call in t["calls"]:
        where = f"{call['scenario']} step {call['step']}"
        if call["kind"] == "invalid":
            _add(out, cfg, "chain_uses_invalid",
                 f"Uses '{call['uses']}' is neither a pattern id and scenario key, such as "
                 f"PAT-905 S1, nor TBD and a name", where)
            continue
        if not call["actor"] or not call["target"]:
            _add(out, cfg, "chain_step_endpoints",
                 f"calls {call['uses']} but has no "
                 f"{'Actor' if not call['actor'] else 'Target'}; a Uses step needs both, the "
                 f"boxes where the child flow enters and leaves this pattern", where)
        if call["kind"] == "tbd":
            _add(out, cfg, "chain_open",
                 f"open sub-flow {call['uses']}: write it as its own pattern, then replace "
                 f"TBD with its id and scenario key", where)
            continue
        pid, skey = call["id"], call["key"]
        if not call["found"]:
            _add(out, cfg, "chain_child_missing",
                 f"no document for {pid} under {call['searched']}; a child is a folder named "
                 f"{pid}-<slug> holding index.md, or a document whose H1 starts with {pid}. "
                 f"Bind patterns_root if the patterns live elsewhere", where)
            continue
        if call.get("candidates"):
            _add(out, cfg, "chain_ambiguous",
                 f"{len(call['candidates'])} documents claim {pid}; using "
                 f"{os.path.relpath(call['candidates'][0], os.path.dirname(src))}", where)
        child = r.load(call["child"]["doc"])
        csc = child.model.scenario(skey)
        if csc is None:
            have = ", ".join(s.key for s in child.model.scenarios) or "none"
            _add(out, cfg, "chain_scenario_missing",
                 f"{pid} has no scenario {skey}; it has {have}", where)
            continue
        if csc.steps:
            first, last = csc.steps[0], csc.steps[-1]
            _join(out, cfg, where, parent, call["actor"], child, [first.actor], pid, skey,
                  "entry")
            _join(out, cfg, where, parent, call["target"], child, [last.actor, last.target],
                  pid, skey, "exit")

    # Cycles anywhere below: the chain does not terminate.
    seen = set()
    for _n, call, trail in walk(t):
        if not call.get("cycle"):
            continue
        hops = [f"{n['id'] or os.path.basename(n['doc'])} {c['scenario']} step {c['step']}"
                for n, c in trail] + [f"{_n['id'] or os.path.basename(_n['doc'])} "
                                      f"{call['scenario']} step {call['step']}"]
        msg = " -> ".join(hops) + f" -> {call['uses']}"
        if msg not in seen:
            seen.add(msg)
            top = trail[0][1] if trail else call
            _add(out, cfg, "chain_cycle",
                 f"a chain cycle: {msg}, which is already on the path; a pattern cannot "
                 f"reach itself through Uses", f"{top['scenario']} step {top['step']}")

    # The approval gate: an approved pattern cannot rest on unapproved or unwritten work.
    if r.approved(parent.status):
        me = parent.id or os.path.basename(src)
        flagged = set()
        for n, call, trail in walk(t):
            top = trail[0][1] if trail else call
            where = f"{top['scenario']} step {top['step']}"
            via = f" through {n['id']}" if trail else ""
            if call["kind"] == "tbd":
                _add(out, cfg, "chain_unapproved",
                     f"{me} is {parent.status} but rests on the open sub-flow "
                     f"{call['uses']}{via}", where)
            elif call["kind"] == "ref" and not call.get("found"):
                if trail:
                    _add(out, cfg, "chain_unapproved",
                         f"{me} is {parent.status} but rests on {call['uses']}{via}, which "
                         f"cannot be found", where)
            elif call.get("child"):
                ch = call["child"]
                k = _key(ch["doc"])
                if not ch["approved"] and k not in flagged and k != _key(src):
                    flagged.add(k)
                    _add(out, cfg, "chain_unapproved",
                         f"{me} is {parent.status} but rests on {ch['id'] or ch['doc']}, "
                         f"which is {ch['status'] or 'without a status'}{via}; approved "
                         f"statuses are {', '.join(cfg.approved_statuses)}", where)
    return out
