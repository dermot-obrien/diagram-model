# SPDX-License-Identifier: Apache-2.0
"""Whether a document, or a template for one, has the structure the binding reads.

A repository may replace any template the framework ships, so long as the replacement
still has what the model is bound to read. This checks the construct, not the content:

    each [[markdown.tables]] section     a heading with that text, and under it a table
                                         whose header has every bound column
    [markdown.scenarios]                 its section, at least one scenario heading the
                                         heading_pattern matches, and under it a table with
                                         the Step, Actor and Action columns (Target and
                                         Interface, if bound, are warnings)
    [markdown.mapping]                   if the section is there, its bound columns
    a pattern type, with --type          the H1 leads with the type's idSeries, and a
                                         declared pattern_type is that type

Headings and tables are matched exactly as `read` matches them: a heading's text without
regard to case, a column by its header text without regard to case, comments and fenced
code ignored. A table with a header and no rows counts, since a template may have none.
"""
from __future__ import annotations

import re

from . import markdown
from .validate import Finding

SEVERITY = {"error": 0, "warn": 1}


def _headers(body: str) -> list:
    """The header row of every GFM table in a block, as lists of cell texts, rows or none."""
    out, prev = [], None
    for ln in body.split("\n"):
        if markdown.ROW_RE.match(ln):
            if markdown.SEP_RE.match(ln) and prev is not None:
                out.append(prev)
                prev = None
                continue
            prev = markdown._cells(ln)
        else:
            prev = None
    return out


def _missing(want: dict, headers: list) -> list:
    """The bound column names missing from the best-matching header, or all of them."""
    names = [str(v) for v in want.values() if v]
    if not headers:
        return names
    best = None
    for h in headers:
        low = {c.lower() for c in h}
        miss = [n for n in names if n.lower() not in low]
        if best is None or len(miss) < len(best):
            best = miss
    return best


def check(path, cfg, type_name: str = "") -> list:
    """Findings for one document or template against the binding's markdown contract."""
    out = []
    with open(path, encoding="utf-8-sig") as fh:
        meta, raw = markdown.front_matter(fh.read())
    secs = markdown.sections(markdown._clean(raw))
    titles = [(lv, t.strip().lower(), body) for lv, t, body in secs]

    def add(sev, rule, msg):
        out.append(Finding(rule, sev, msg, path))

    # Bound tables are each required. The built-in defaults are alternatives, Nodes or
    # Components, Edges or Interfaces, so one section per entity is enough.
    from .config import default_config
    defaults = cfg.tables == default_config().tables
    present = {t for _lv, t, _b in titles}
    for spec in cfg.tables:
        bodies = [b for _lv, t, b in titles if t == spec.section.strip().lower()]
        if not bodies:
            alternatives = [x.section for x in cfg.tables if x.entity == spec.entity]
            if defaults and any(x.strip().lower() in present for x in alternatives):
                continue
            add("error", "contract_section",
                f"no '{spec.section}' section, which the {spec.entity} table is read from"
                if not defaults else
                f"no {' or '.join(repr(x) for x in alternatives)} section, which the built-in "
                f"{spec.entity} table is read from; bind [[markdown.tables]] to match the template")
            if defaults:
                present.add(spec.section.strip().lower())   # report each entity once
            continue
        headers = [h for b in bodies for h in _headers(b)]
        miss = _missing(spec.columns, headers)
        if not headers:
            add("error", "contract_table", f"'{spec.section}' has no table")
        elif miss:
            add("error", "contract_columns", f"the '{spec.section}' table has no "
                f"{', '.join(repr(m) for m in miss)} column, which the binding reads")

    sc = cfg.scenarios
    start = next((i for i, (_lv, t, _b) in enumerate(titles) if t == sc.section.strip().lower()), None)
    if start is None:
        add("error", "contract_section", f"no '{sc.section}' section")
    else:
        depth, rx, found = titles[start][0], re.compile(sc.heading_pattern), []
        for lv, title, body in secs[start + 1:]:
            if lv <= depth:
                break
            if rx.match(title.strip()):
                found.append(body)
        if not found:
            add("error", "contract_scenario", f"no scenario heading under '{sc.section}' "
                f"matches {sc.heading_pattern}, such as '### S1 <name>'")
        else:
            headers = [h for b in found for h in _headers(b)]
            required = {k: sc.columns[k] for k in ("step", "actor", "action") if sc.columns.get(k)}
            optional = {k: sc.columns[k] for k in ("target", "edge") if sc.columns.get(k)}
            miss = _missing(required, headers)
            if not headers:
                add("error", "contract_table", "the scenario has no steps table")
            elif miss:
                add("error", "contract_columns", f"the steps table has no "
                    f"{', '.join(repr(m) for m in miss)} column, which the binding reads")
            elif _missing(optional, headers):
                add("warn", "contract_columns", f"the steps table has no "
                    f"{', '.join(repr(m) for m in _missing(optional, headers))} column, so "
                    f"steps cannot name their target or interface")

    mp = cfg.mapping
    bodies = [b for _lv, t, b in titles if t == mp.section.strip().lower()]
    if bodies:
        miss = _missing(mp.columns, [h for b in bodies for h in _headers(b)])
        if miss:
            add("error", "contract_columns", f"the '{mp.section}' table has no "
                f"{', '.join(repr(m) for m in miss)} column, which the binding reads")

    if type_name:
        t = cfg.pattern_types.get(type_name)
        if t is None:
            add("error", "pattern_type_unknown", f"'{type_name}' is not a bound pattern type")
        else:
            h1 = next((tt for lv, tt, _b in secs if lv == 1), "")
            if t.id_series and not h1.startswith(f"{t.id_series}-"):
                add("warn", "contract_series", f"the H1 '{h1}' does not lead with "
                    f"{t.id_series}-, the series of {t.label or type_name}")
            declared = str(meta.get("pattern_type") or "").strip()
            if declared and declared != type_name:
                add("error", "contract_type", f"pattern_type is '{declared}' in a template "
                    f"for {type_name}")
    return sorted(out, key=lambda f: SEVERITY.get(f.severity, 2))
