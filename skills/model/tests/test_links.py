# SPDX-License-Identifier: Apache-2.0
"""Links from declared identifiers to their pages: the [[links]] rules, their placeholders
and targets, the walkthrough's hotspots and name links, draw.io's link attribute, and
doctor. Standard library only:

    python -m unittest discover -s tests
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from model import animate, cli, config, drawio, links, markdown, sync, validate  # noqa: E402

RULES = textwrap.dedent("""\
    [[links]]
    match  = 'ABB-[0-9]{3}'
    locate = "building-blocks/abbs/*/{id}-*"
    href   = "{site}/building-blocks/abbs/{located}/"

    [[links]]
    match  = 'ABB-9[0-9]{2}'
    href   = "{site}/never/{id}/"

    [[links]]
    match  = 'SBB-[0-9]{3}(\\.[0-9]+){0,2}'
    locate = "building-blocks/sbbs/{id}.md"
    href   = "{site}/sbbs/{located}"

    [[links]]
    match  = 'PAT-[0-9]{3}'
    locate = "patterns/*/{id}-*/index.md"
    href   = "{rel}"
    target = "same"

    [[links]]
    match  = 'CP-[0-9]{2}'
    href   = "{site}/capabilities/{id}/"
    """)

BINDINGS = textwrap.dedent("""\
    bindingsVersion = "1.0"

    [model]
    node_id_attrs = ["abb_id", "sbb_id", "cap_id"]
    edge_id_attr  = "iface_id"
    local_pattern = '[0-9]{1,3}'
    link_site     = "http://localhost:3000/site/"
    {extra}

    [[markdown.tables]]
    section    = "Building Blocks"
    entity     = "node"
    id_pattern = 'ABB-[0-9]{3}|SBB-[0-9]{3}(\\.[0-9]+){0,2}|CP-[0-9]{2}'
    columns    = { id = "Building Block", label = "Building Block" }

    [[markdown.tables]]
    section    = "Interfaces"
    entity     = "edge"
    id_pattern = 'IF-[0-9]{2}|ABB-[0-9]{3}|SBB-[0-9]{3}(\\.[0-9]+){0,2}|CP-[0-9]{2}'
    columns    = { id = "Interface", source = "Provider", target = "Consumer", label = "Purpose" }

    [markdown.scenarios]
    section         = "Scenarios"
    heading_pattern = '^(S[0-9]+)\\b[\\s:.-]*(.*)$'
    columns         = { step = "Step", actor = "Actor", action = "Action", edge = "Interface", target = "Target" }

    """)

DOC = textwrap.dedent("""\
    ---
    title: "PAT-900 Linked"
    status: Draft
    model:
      diagram: components.drawio
    ---

    # PAT-900 Linked

    ## Building Blocks

    | Building Block | Role |
    |---|---|
    | 01 Client | the caller |
    | ABB-901 Gateway | the front door |
    | SBB-911.1 Cache | a product |
    | CP-01 Capability | a capability |

    ## Interfaces

    | Interface | Provider | Consumer | Purpose |
    |---|---|---|---|
    | IF-01 | ABB-901 Gateway | 01 Client | answers |
    | IF-02 | SBB-911.1 Cache | ABB-901 Gateway | cached answers |

    ## Catalogue Mapping

    | Local ID | Maps To | Relationship |
    |---|---|---|
    | 01 | gap | gap |

    ## Scenarios

    ### S1 Ask

    | Step | Actor | Target | Action | Interface | Uses |
    |---:|---|---|---|---|---|
    | 1 | 01 Client | ABB-901 Gateway | ask | IF-01 | |
    | 2 | ABB-901 Gateway | SBB-911.1 Cache | look up | IF-02 | |
    | 3 | ABB-901 Gateway | ABB-901 Gateway | check the policy | | PAT-905 S1 |
    """)

PARTICIPANT = textwrap.dedent("""\
    ---
    status: Approved
    ---

    # PAT-905 Policy check

    ## Building Blocks

    | Building Block | Role |
    |---|---|
    | ABB-901 Gateway | asks |
    | CP-01 Capability | decides |

    ## Scenarios

    ### S1 Check

    | Step | Actor | Target | Action | Interface |
    |---:|---|---|---|---|
    | 1 | ABB-901 Gateway | CP-01 Capability | ask for a decision | |
    | 2 | CP-01 Capability | ABB-901 Gateway | decide | |
    """)


def png(w, h):
    ihdr = struct.pack(">II", w, h) + b"\x08\x06\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr + b"\x00\x00\x00\x00"


class Base(unittest.TestCase):
    extra = ""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.bind(self.extra)
        self.write("building-blocks/abbs/edge/ABB-901-gateway/index.md", "# ABB-901 Gateway\n")
        self.write("building-blocks/sbbs/SBB-911.1.md", "# SBB-911.1 Cache\n")
        self.doc = self.write("patterns/area/PAT-900-linked/index.md", DOC)
        self.part = self.write("patterns/area/PAT-905-policy/index.md", PARTICIPANT)
        os.makedirs(os.path.join(self.dir, ".git"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def bind(self, extra="", rules=RULES):
        self.write("skill-bindings.toml", BINDINGS.replace("{extra}", extra) + rules)

    def write(self, rel, text):
        p = os.path.join(self.dir, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return p

    def cfg(self):
        return config.load(None, near=self.doc)

    def resolve(self, ident, page_dir=None):
        return links.resolve(self.cfg(), ident, page_dir)

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(args))
        return code, out.getvalue(), err.getvalue()


class RuleTests(Base):
    def test_first_matching_rule_wins(self):
        # ABB-901 fits the first two rules; the first is used.
        self.assertEqual(self.resolve("ABB-901").href,
                         "http://localhost:3000/site/building-blocks/abbs/edge/ABB-901-gateway/")

    def test_located_for_a_folder_match(self):
        self.assertEqual(self.resolve("ABB-901").located, "edge/ABB-901-gateway")

    def test_located_drops_a_matched_index(self):
        self.bind(rules=RULES.replace('locate = "building-blocks/abbs/*/{id}-*"',
                                      'locate = "building-blocks/abbs/*/{id}-*/index.md"'))
        self.assertEqual(self.resolve("ABB-901").located, "edge/ABB-901-gateway")

    def test_located_for_a_file_match_and_dotted_ids(self):
        self.assertEqual(self.resolve("SBB-911.1").href,
                         "http://localhost:3000/site/sbbs/SBB-911.1.md")

    def test_rel_is_relative_to_the_page(self):
        page = os.path.dirname(self.doc)
        self.assertEqual(self.resolve("PAT-905", page).href, "../PAT-905-policy/index.md")

    def test_site_without_locate(self):
        self.assertEqual(self.resolve("CP-01").href, "http://localhost:3000/site/capabilities/CP-01/")

    def test_site_unset_is_empty(self):
        self.write("skill-bindings.toml", BINDINGS.replace('link_site     = "http://localhost:3000/site/"', "")
                   .replace("{extra}", "") + RULES)
        self.assertEqual(self.resolve("CP-01").href, "/capabilities/CP-01/")

    def test_unresolved_is_no_link_and_a_warning(self):
        link = self.resolve("ABB-902")
        self.assertIsNone(link.href)
        self.assertIn("building-blocks/abbs/*/ABB-902-*", link.problem)
        self.write("patterns/area/PAT-900-linked/index.md",
                   DOC.replace("| CP-01 Capability | a capability |",
                               "| CP-01 Capability | a capability |\n| ABB-902 Store | unfiled |"))
        c = self.cfg()
        fs = [f for f in validate.check(markdown.read(self.doc, c), c) if f.rule == "link_unresolved"]
        self.assertEqual([(f.severity, f.where) for f in fs], [("warn", "ABB-902")])
        self.assertIn("building-blocks/abbs/*/ABB-902-*", fs[0].message)

    def test_local_ids_are_never_linked(self):
        self.bind(rules='[[links]]\nmatch = \'.*\'\nhref = "{site}/{id}"\n')
        self.assertIsNone(self.resolve("01"))
        self.assertEqual(self.resolve("ABB-901").href, "http://localhost:3000/site/ABB-901")

    def test_no_rule_no_link(self):
        self.assertIsNone(self.resolve("IF-01"))


class TargetTests(Base):
    def test_default_is_a_new_page(self):
        self.assertEqual(self.resolve("ABB-901").target, "new")

    def test_model_setting(self):
        self.bind('link_target = "same"')
        self.assertEqual(self.resolve("ABB-901").target, "same")

    def test_rule_overrides_model_setting(self):
        self.assertEqual(self.resolve("PAT-905", os.path.dirname(self.doc)).target, "same")
        self.bind('link_target = "same"', RULES.replace('target = "same"', 'target = "new"'))
        self.assertEqual(self.resolve("PAT-905", os.path.dirname(self.doc)).target, "new")
        self.assertEqual(self.resolve("ABB-901").target, "same")

    def test_invalid_values_are_config_errors(self):
        self.bind('link_target = "tab"')
        code, _out, err = self.cli("validate", self.doc)
        self.assertEqual(code, 2)
        self.assertIn("link_target is 'tab'", err)
        self.bind(rules=RULES.replace('target = "same"', 'target = "popup"'))
        code, _out, err = self.cli("doctor", "--near", self.dir)
        self.assertEqual(code, 2)
        self.assertIn("target is 'popup'", err)


class DrawioLinkTests(Base):
    def emit(self):
        c = self.cfg()
        out = os.path.join(os.path.dirname(self.doc), "components.drawio")
        drawio.write(markdown.read(self.doc, c), out, c)
        return out, c

    def obj(self, path, ident):
        for o in ET.parse(path).getroot().iter("object"):
            if ident in (o.get("abb_id"), o.get("sbb_id"), o.get("local_id"), o.get("cap_id")):
                return o

    def test_emit_sets_draws_link(self):
        out, _c = self.emit()
        o = self.obj(out, "ABB-901")
        self.assertEqual(o.get("link"), "http://localhost:3000/site/building-blocks/abbs/edge/ABB-901-gateway/")
        self.assertEqual(o.get("linkTarget"), "_blank")
        self.assertIsNone(self.obj(out, "01").get("link"))

    def test_sync_keeps_links_current(self):
        out, c = self.emit()
        shutil.rmtree(os.path.join(self.dir, "building-blocks", "abbs", "edge"))
        changes = sync.sync(markdown.read(self.doc, c), out, c)
        self.assertIn("link removed", " ".join(x.detail for x in changes))
        self.assertIsNone(self.obj(out, "ABB-901").get("link"))
        self.write("building-blocks/abbs/core/ABB-901-gateway/index.md", "# ABB-901\n")
        sync.sync(markdown.read(self.doc, c), out, c)
        self.assertTrue(self.obj(out, "ABB-901").get("link").endswith("/abbs/core/ABB-901-gateway/"))
        # A second sync changes nothing.
        self.assertFalse([x for x in sync.sync(markdown.read(self.doc, c), out, c, dry_run=True)
                          if "link" in x.detail])

    def test_sync_follows_the_target(self):
        out, c = self.emit()
        self.bind('link_target = "same"')
        c = self.cfg()
        sync.sync(markdown.read(self.doc, c), out, c)
        self.assertEqual(self.obj(out, "ABB-901").get("linkTarget"), "_self")

    def test_an_authors_link_on_an_unmatched_box_is_kept(self):
        out, c = self.emit()
        tree = ET.parse(out)
        for o in tree.getroot().iter("object"):
            if o.get("local_id") == "01":
                o.set("link", "https://example.org/client")
        tree.write(out, encoding="utf-8")
        sync.sync(markdown.read(self.doc, c), out, c)
        self.assertEqual(self.obj(out, "01").get("link"), "https://example.org/client")

    def test_link_is_not_read_as_data(self):
        out, c = self.emit()
        n = drawio.read(out, c).node("ABB-901")
        self.assertNotIn("link", n.attrs)


class WalkthroughTests(DrawioLinkTests):
    def page(self):
        out, c = self.emit()
        _, boxes, _, _ = animate.geometry(out)
        x0, y0, x1, y1 = animate.bounds(boxes)
        img = os.path.join(self.dir, "structure.png")
        with open(img, "wb") as fh:
            fh.write(png(int((x1 - x0) * 2), int((y1 - y0) * 2)))
        data = animate.build(self.doc, c, image=img, force=True)
        page = animate.default_out(self.doc)
        r = animate.write(data, page)
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        return r, json.loads(re.search(r"const D=(\{.*?\}), W=", html, re.S).group(1)), html

    def test_hotspots_for_every_linked_box(self):
        _r, d, _html = self.page()
        hot = {h["id"]: h for h in d["hot"]}
        self.assertEqual(sorted(hot), ["ABB-901", "CP-01", "SBB-911.1"])
        self.assertEqual(hot["ABB-901"]["name"], "Gateway")
        self.assertEqual(hot["ABB-901"]["target"], "new")
        self.assertEqual(len(hot["ABB-901"]["box"]), 4)

    def test_step_ends_carry_their_links(self):
        _r, d, _html = self.page()
        self.assertTrue(d["nodes"]["ABB-901"]["href"].endswith("/abbs/edge/ABB-901-gateway/"))
        self.assertNotIn("href", d["nodes"]["01"])

    def test_participating_pattern_links_beside_the_drill_in(self):
        _r, d, _html = self.page()
        u = d["scenarios"][0]["steps"][2]["uses"]
        self.assertEqual(u["page"], {"href": "../PAT-905-policy/index.md", "target": "same",
                                     "id": "PAT-905"})
        self.assertEqual(u["href"], "../PAT-905-policy/scenarios.html")

    def test_markup(self):
        _r, _d, html = self.page()
        self.assertIn('<g id="hot"></g><g id="done"></g><g id="cur"></g>', html)
        self.assertIn('function hotspots(){', html)
        self.assertIn('a.setAttribute("target","_blank");a.setAttribute("rel","noopener")', html)
        self.assertIn('if(t.target!=="same")', html)
        self.assertIn('w.className="who"', html)
        self.assertIn('a.className="page-link"', html)

    def test_page_stays_standalone_and_embed_safe(self):
        _r, d, html = self.page()
        self.assertNotRegex(html, r"fetch\(|XMLHttpRequest|<script[^>]+src=|<link[^>]+href=")
        # The only URLs are the SVG namespace and the configured links, which are data.
        url = r"https?://[^\s\"')]+"
        self.assertEqual(set(re.findall(url, html)) - set(re.findall(url, json.dumps(d))),
                         {"http://www.w3.org/2000/svg"})
        self.assertNotRegex(html, r"(?i)\b(?:src|href|poster)\s*=\s*[\"']?[A-Za-z_$][\w$]*[\"']?(?=[\s;,)>+}]|$)")
        urls = [u for _q, u in re.findall(r"(?i)url\(\s*([\"']?)([^\"')]+)\1\s*\)", html)]
        self.assertTrue(all(u.startswith("#") for u in urls), urls)

    def test_unresolved_is_noted_by_animate(self):
        self.write("patterns/area/PAT-900-linked/index.md",
                   DOC.replace("| CP-01 Capability | a capability |",
                               "| CP-01 Capability | a capability |\n| ABB-902 Store | unfiled |"))
        r, _d, _html = self.page()
        self.assertTrue(any("[link_unresolved]" in n and "ABB-902" in n for n in r["notes"]))

    def test_no_rules_no_links(self):
        self.bind(rules="")
        _r, d, _html = self.page()
        self.assertEqual(d["hot"], [])
        self.assertNotIn("href", d["nodes"]["ABB-901"])


class DoctorTests(Base):
    def test_rules_and_the_documents_links(self):
        code, out, _err = self.cli("doctor", "--doc", self.doc, "--json")
        d = json.loads(out)["links"]
        self.assertEqual([r["match"] for r in d["rules"]][:2], ["ABB-[0-9]{3}", "ABB-9[0-9]{2}"])
        self.assertEqual(d["site"], "http://localhost:3000/site/")
        self.assertEqual(d["rules"][3]["target"], "same")
        self.assertEqual(sorted(d["resolved"]), ["ABB-901", "CP-01", "SBB-911.1"])
        self.assertEqual(d["resolved"]["ABB-901"]["located"], "edge/ABB-901-gateway")

    def test_text(self):
        code, out, _err = self.cli("doctor", "--doc", self.doc)
        self.assertIn("link rule    : ABB-[0-9]{3} -> {site}/building-blocks/abbs/{located}/", out)
        self.assertIn("link         : CP-01 -> http://localhost:3000/site/capabilities/CP-01/", out)


if __name__ == "__main__":
    unittest.main()
