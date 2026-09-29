# SPDX-License-Identifier: Apache-2.0
"""Links from a declared identifier to its page.

A workspace declares, in its binding file, how an id becomes a link: a full-match regex
on the id, an optional glob that finds the item on disk, and an href template.

    [model]
    link_site   = "http://localhost:3000/docs"    # {site}; optional
    link_target = "new"                           # "new" (default) or "same"

    [[links]]
    match  = 'ABB-[0-9]{3}'
    locate = "../building-blocks/abbs/*/{id}-*"   # optional; relative to the binding file
    href   = "{site}/building-blocks/abbs/{located}/"
    target = "same"                               # optional; wins over link_target

Placeholders in `href`:

    {id}        the identifier
    {site}      [model] link_site, "" when unset, without a trailing slash
    {located}   the first path `locate` matched, relative to the glob's fixed prefix (the
                folders before its first wildcard), with forward slashes and no trailing
                slash; a matched `index.md`, or other index document, is dropped so the
                folder that holds it is what is named
    {rel}       the relative path from the page being generated to the matched path

Rules are tried in order and the first whose `match` fits wins. Local ids are never
linked: they are scoped to their document and name nothing elsewhere. A rule whose href
needs `{located}` or `{rel}` when `locate` found nothing gives no link, and a
`link_unresolved` warning naming the id and the glob.
"""
from __future__ import annotations

import glob
import os
import re

INDEX_NAMES = ("index.md", "index.mdx", "index.markdown")
WILD = re.compile(r"[*?\[]")


class Link:
    __slots__ = ("id", "href", "target", "rule", "located", "problem")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def to_dict(self):
        return {k: getattr(self, k) for k in ("id", "href", "target", "located", "problem")
                if getattr(self, k)}


def rule_for(cfg, ident):
    """The first rule whose match fits the whole id, or None. Never one for a local id."""
    if not ident or cfg.is_local(ident):
        return None
    return next((r for r in cfg.links if r.match_re.fullmatch(ident)), None)


def _prefix(pattern: str) -> str:
    """The folders of a glob before its first wildcard."""
    parts = re.split(r"[\\/]", pattern)
    fixed = []
    for part in parts[:-1]:
        if WILD.search(part):
            break
        fixed.append(part)
    return os.sep.join(fixed) if fixed else ""


def _located(match: str, prefix: str) -> str:
    rel = os.path.relpath(match, prefix) if prefix else match
    rel = rel.replace(os.sep, "/").rstrip("/")
    head, _, tail = rel.rpartition("/")
    if tail in INDEX_NAMES:
        rel = head
    return rel


def resolve(cfg, ident, page_dir=None):
    """The Link for an id, or None when no rule matches it.

    `page_dir` is the folder of the page the link is written into, which `{rel}` is
    relative to. A Link with `href` None carries the `problem` instead.
    """
    rule = rule_for(cfg, ident)
    if rule is None:
        return None
    target = rule.target or cfg.link_target or "new"
    found, glob_shown = None, ""
    if rule.locate:
        pattern = cfg.resolve(rule.locate.replace("{id}", ident))
        glob_shown = rule.locate.replace("{id}", ident)
        hits = sorted(glob.glob(pattern))
        if hits:
            found = hits[0]
    needs_path = "{located}" in rule.href or "{rel}" in rule.href
    if needs_path and not found:
        why = (f"no path matches {glob_shown}" if rule.locate
               else "the rule has no locate glob to fill {located} or {rel}")
        return Link(id=ident, href=None, target=target, rule=rule, problem=why)
    values = {"{id}": ident, "{site}": (cfg.link_site or "").rstrip("/")}
    if found:
        prefix = _prefix(cfg.resolve(rule.locate.replace("{id}", ident)))
        values["{located}"] = _located(found, prefix)
        if page_dir is not None:
            try:
                values["{rel}"] = os.path.relpath(found, page_dir).replace(os.sep, "/")
            except ValueError:
                values["{rel}"] = found.replace(os.sep, "/")
        elif "{rel}" in rule.href:
            values["{rel}"] = found.replace(os.sep, "/")
    href = rule.href
    for k, v in values.items():
        href = href.replace(k, v)
    return Link(id=ident, href=href, target=target, rule=rule,
                located=values.get("{located}", ""), problem=None)


def findings(m, cfg, page_dir=None) -> list:
    """A `link_unresolved` warning for each box whose rule matches but whose page is
    not found."""
    from .validate import Finding
    out = []
    if not cfg.links:
        return out
    sev = cfg.severity("link_unresolved")
    if sev == "off":
        return out
    page_dir = page_dir or (os.path.dirname(os.path.abspath(m.source)) if m.source else None)
    seen = set()
    for n in m.nodes:
        if n.id in seen:
            continue
        seen.add(n.id)
        link = resolve(cfg, n.id, page_dir)
        if link is not None and link.href is None:
            out.append(Finding("link_unresolved", sev,
                               f"{n.id} matches the link rule '{link.rule.match}' but "
                               f"{link.problem}, so it is not linked", n.id))
    return out


def report(m, cfg, page_dir=None) -> dict:
    """{id: {href, target, located} or {problem}} for every box a rule matches."""
    out = {}
    page_dir = page_dir or (os.path.dirname(os.path.abspath(m.source)) if m.source else None)
    for n in m.nodes:
        link = resolve(cfg, n.id, page_dir)
        if link is not None:
            out[n.id] = link.to_dict()
    return out
