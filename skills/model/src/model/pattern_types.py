# SPDX-License-Identifier: Apache-2.0
"""Pattern types: what a repository calls its kinds of pattern, and what each may hold.

Every architecture model is a pattern. A repository may name kinds of it, each with its
own label, identifier series and expectation of how physical it is, in its binding file:

    [suite.pattern.types.architecture-pattern]
    label    = "Architecture pattern"
    idSeries = "AP"
    physical = "none"          # technology-agnostic: ABBs and local roles only

    [suite.pattern.types.reference-architecture]
    label    = "Reference architecture"
    idSeries = "RA"
    physical = "most"          # technology-specific: mainly SBBs and products

A document's type is its front matter `pattern_type`, or else the type whose idSeries its
identifier carries. A physical box is one whose abstraction is physical: an SBB or product
from a catalogue whose level is physical, or a box whose kind says so (see validate.py).
`physical` is none, some (at least one), most (more than half of the boxes that have a
level) or all. Unset, any mix is allowed.

A document may name what it implements, `implements: [AP-004]`, as a reference
architecture names the architecture pattern it makes concrete. Each is looked up as a
participating pattern is, and each catalogued box of the implemented pattern must be
accounted for here (`implements_uncovered`): drawn as a box, named in a box's Realises
column, mapped to by a local box, or named under a Risks heading as a gap. A local role of
the implemented pattern has no identifier outside it, so it is not counted. A reference
architecture's mapping of functions onto elements need not be one to one, so one box may
realise several blocks, and a block may be realised by several boxes.

Nothing here runs for a repository with no types bound, or for a document that is not of
a bound type, so a use case or any other document is never checked against them.
"""
from __future__ import annotations

import re

from . import markdown

# The Building Blocks column a reference architecture names the realised block in. Spare
# table columns reach the model as attributes keyed by their header, lower-cased.
REALISES_ATTR = "realises"
# A section whose heading starts with this records accepted gaps, among other risks.
RISKS_HEADING = "risk"

PHYSICAL = ("none", "some", "most", "all")


def doc_id(path, cfg) -> str:
    """The identifier leading the document's first H1, or ""."""
    from .composition import _h1
    from . import config as config_mod
    m = re.match(cfg.pattern_id or config_mod.DEFAULT_PATTERN_ID, _h1(path) or "")
    return m.group(0) if m else ""


def type_of(meta, pid, cfg) -> tuple:
    """(type name, how it was known) for a document, or ("", "")."""
    declared = str(meta.get("pattern_type") or "").strip()
    if declared:
        return declared, "declared"
    for name, t in cfg.pattern_types.items():
        if t.id_series and pid.startswith(f"{t.id_series}-"):
            return name, "series"
    return "", ""


def _ids(value) -> list:
    if isinstance(value, str):
        # The front matter reader returns a flow list, [AP-004, AP-007], as its text.
        return [v.strip().strip("'\"") for v in value.strip().strip("[]").split(",")
                if v.strip().strip("'\"")]
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _mentions(text: str, ident: str) -> bool:
    return bool(re.search(r"(?<![A-Za-z0-9-])" + re.escape(ident) + r"(?![A-Za-z0-9-])", text))


def _risks_text(path) -> str:
    with open(path, encoding="utf-8-sig") as fh:
        _meta, raw = markdown.front_matter(fh.read())
    return "\n".join(body for _lv, title, body in markdown.sections(markdown._clean(raw))
                     if title.strip().lower().startswith(RISKS_HEADING))


def _uncovered(m, cfg, path, pid, target, implemented) -> list:
    """The catalogued boxes of an implemented pattern that this document does not account for."""
    from .composition import _canon, _named
    tm, tcfg = implemented.model, implemented.cfg
    needed = []
    for n in tm.nodes:
        for ident in sorted(_canon(tm, tcfg, n.id)):
            if ident not in needed:
                needed.append(ident)
    if not needed:
        return []
    drawn = set()
    for n in m.nodes:
        drawn |= _canon(m, cfg, n.id)
    realises = "\n".join(str(n.attrs.get(REALISES_ATTR, "")) for n in m.nodes)
    risks = None
    missing = []
    for ident in needed:
        if ident in drawn or _mentions(realises, ident):
            continue
        if risks is None:
            risks = _risks_text(path)
        if _mentions(risks, ident):
            continue
        missing.append(_named(tm, ident))
    if not missing:
        return []
    from .validate import _add
    out = []
    shown = ", ".join(missing[:5]) + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
    _add(out, cfg, "implements_uncovered",
         f"{pid or 'this document'} implements {target}, but nothing here accounts for "
         f"{shown}: name it in a box's Realises column, draw it, or record it as a gap "
         f"under Risks and Trade-offs", pid or path)
    return out


def findings(m, cfg, resolver=None) -> list:
    from .validate import _add, node_level, catalogue_levels
    out = []
    path = getattr(m, "source", "") or ""
    if not path.endswith((".md", ".markdown", ".mdx")):
        return out
    meta = markdown.read_meta(path)
    pid = doc_id(path, cfg)
    where = pid or path

    implements = _ids(meta.get("implements"))
    if implements:
        from .composition import Resolver
        r = resolver or Resolver(cfg)
        for target in implements:
            if target == pid:
                _add(out, cfg, "implements_missing", f"{pid} implements itself", where)
                continue
            found, searched = r.find(target, path)
            if not found:
                _add(out, cfg, "implements_missing",
                     f"{pid or 'this document'} implements {target}, but there is no document "
                     f"for {target} under {searched}", where)
            elif len(found) == 1:
                out += _uncovered(m, cfg, path, pid, target, r.load(found[0]))

    if not cfg.pattern_types:
        return out
    name, how = type_of(meta, pid, cfg)
    if not name:
        return out
    t = cfg.pattern_types.get(name)
    if t is None:
        _add(out, cfg, "pattern_type_unknown",
             f"pattern_type '{name}' is not a bound type; expected one of "
             f"{', '.join(sorted(cfg.pattern_types))}", where)
        return out
    label = t.label or name
    if how == "declared" and t.id_series and pid and not pid.startswith(f"{t.id_series}-"):
        _add(out, cfg, "pattern_type_series",
             f"{pid} is a {label}, whose identifiers are {t.id_series}-NNN", where)

    if t.physical:
        levels = catalogue_levels(cfg)
        boxes = [(n.id, node_level(n, cfg, levels)) for n in m.nodes]
        boxes = [(i, lv) for i, lv in boxes if lv is not None]
        physical = [i for i, lv in boxes if lv == "physical"]
        known = [i for i, lv in boxes if lv]
        if boxes:
            ok = {"none": not physical,
                  "some": bool(physical),
                  "most": bool(known) and len(physical) * 2 > len(known),
                  "all": bool(known) and len(physical) == len(known) == len(boxes)}[t.physical]
            if not ok:
                expect = {"none": "no physical boxes (SBBs or products)",
                          "some": "at least one physical box (an SBB or product)",
                          "most": "mainly physical boxes (SBBs or products)",
                          "all": "only physical boxes (SBBs or products)"}[t.physical]
                got = (f"{len(physical)} of its {len(known)} boxes with a level are physical"
                       + (f": {', '.join(physical[:5])}" + (" ..." if len(physical) > 5 else "")
                          if physical and t.physical == "none" else ""))
                _add(out, cfg, "pattern_type_physical",
                     f"{pid or 'this document'} is a {label}, which has {expect}, but {got}",
                     where)
    return out
