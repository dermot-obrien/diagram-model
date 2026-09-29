# SPDX-License-Identifier: Apache-2.0
"""Composing patterns: a participation step, whose Uses cell runs another pattern's scenario.

Parsing, resolution, each validation rule, the composition report, the approval gate, draw.io
and the walkthrough's drill-in and back links. Standard library only:

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

from model import animate, composition, cli, config, drawio, markdown, sync, validate  # noqa: E402
from model.schema import Model  # noqa: E402

BINDINGS = textwrap.dedent("""\
    bindingsVersion = "1.0"

    [model]
    node_id_attrs = ["abb_id"]
    edge_id_attr  = "iface_id"
    local_pattern = '[0-9]{1,3}'
    {extra}

    [[markdown.tables]]
    section    = "Building Blocks"
    entity     = "node"
    id_pattern = 'ABB-[0-9]{3}'
    columns    = { id = "Building Block", label = "Building Block" }

    [[markdown.tables]]
    section    = "Interfaces"
    entity     = "edge"
    id_pattern = 'IF-[0-9]{2,3}|ABB-[0-9]{3}'
    columns    = { id = "Interface", source = "Provider", target = "Consumer", label = "Purpose" }

    [markdown.scenarios]
    section         = "Scenarios"
    heading_pattern = '^(S[0-9]+)\\b[\\s:.-]*(.*)$'
    columns         = { step = "Step", actor = "Actor", action = "Action", edge = "Interface", target = "Target" }
    {suite}
    """)


def doc(pid, title, status, blocks, mapping, scenarios, interfaces=None):
    """A pattern document. `scenarios` is {key: [(actor, target, action, iface, uses)]}."""
    out = ["---", f'title: "{pid} {title}"', f"status: {status}", "---", "",
           f"# {pid} {title}", "", "## Building Blocks", "",
           "| Building Block | Role |", "|---|---|"]
    out += [f"| {b} | a role |" for b in blocks]
    out += ["", "## Interfaces", "", "| Interface | Provider | Consumer | Purpose |",
            "|---|---|---|---|"]
    out += [f"| {i} | {p} | {c} | {u} |" for i, p, c, u in (interfaces or [])]
    if mapping:
        out += ["", "## Catalogue Mapping", "", "| Local ID | Maps To | Relationship |",
                "|---|---|---|"]
        out += [f"| {l} | {t or 'gap'} | {r} |" for l, t, r in mapping]
    out += ["", "## Scenarios", ""]
    for key, steps in scenarios.items():
        out += [f"### {key} Flow {key}", "",
                "| Step | Actor | Target | Action | Interface | Uses |",
                "|---:|---|---|---|---|---|"]
        out += [f"| {n} | {a} | {t} | {act} | {i} | {u} |"
                for n, (a, t, act, i, u) in enumerate(steps, 1)]
        out.append("")
    return "\n".join(out) + "\n"


COMPOSITE = dict(
    pid="PAT-900", title="Order intake", status="Draft",
    blocks=["01 Storefront", "ABB-901 Order service"],
    mapping=[("01", "", "gap")],
    interfaces=[("IF-01", "01 Storefront", "ABB-901 Order service", "orders")],
    scenarios={"S1": [
        ("01 Storefront", "ABB-901 Order service", "submit the order", "IF-01", ""),
        ("ABB-901 Order service", "ABB-901 Order service", "take payment", "", "PAT-905 S1 payment capture"),
        ("ABB-901 Order service", "01 Storefront", "confirm", "IF-01", ""),
    ]})

PARTICIPANT = dict(
    pid="PAT-905", title="Payment capture", status="Approved",
    blocks=["ABB-901 Order service", "01 Card processor"],
    mapping=[("01", "", "gap")],
    interfaces=[("IF-01", "ABB-901 Order service", "01 Card processor", "charges")],
    scenarios={"S1": [
        ("ABB-901 Order service", "01 Card processor", "charge the card", "IF-01", ""),
        ("01 Card processor", "ABB-901 Order service", "return the result", "IF-01", ""),
    ]})


def png(w, h):
    ihdr = struct.pack(">II", w, h) + b"\x08\x06\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr + b"\x00\x00\x00\x00"


class Base(unittest.TestCase):
    extra = ""
    suite = ""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.write("skill-bindings.toml", BINDINGS.replace("{extra}", self.extra)
                   .replace("{suite}", self.suite))
        self.composite = self.pattern("PAT-900-order-intake", **COMPOSITE)
        self.participant = self.pattern("PAT-905-payment-capture", **PARTICIPANT)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, rel, text):
        p = os.path.join(self.dir, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return p

    def pattern(self, folder, where="patterns", **kw):
        return self.write(f"{where}/{folder}/index.md", doc(**kw))

    def edit(self, path, old, new):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(old, text)
        self.write(os.path.relpath(path, self.dir).replace(os.sep, "/"), text.replace(old, new))

    def cfg(self, path=None):
        return config.load(None, near=path or self.composite)

    def findings(self, path=None):
        path = path or self.composite
        c = self.cfg(path)
        return validate.check(markdown.read(path, c), c)

    def rules(self, path=None):
        return [(f.rule, f.severity) for f in self.findings(path)]

    def composition_rules(self, path=None):
        return [r for r in self.rules(path)
                if r[0].startswith(("uses_", "participant_", "composition_"))]

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(args))
        return code, out.getvalue(), err.getvalue()


# ----------------------------------------------------------------------------- parsing

class ParseTests(Base):
    def test_ref_with_trailing_text(self):
        v = markdown.parse_uses("PAT-905 S1 payment capture", self.cfg())
        self.assertEqual(v, ("PAT-905 S1", "ref", "PAT-905", "S1", ""))

    def test_ref_with_punctuation(self):
        self.assertEqual(markdown.parse_uses("PAT-905: S2, then more", self.cfg())[:4],
                         ("PAT-905 S2", "ref", "PAT-905", "S2"))

    def test_tbd(self):
        self.assertEqual(markdown.parse_uses("TBD fraud scoring", self.cfg()),
                         ("TBD fraud scoring", "tbd", "", "", "fraud scoring"))
        self.assertEqual(markdown.parse_uses("tbd", self.cfg())[:2], ("TBD", "tbd"))

    def test_empty_and_dash(self):
        for v in ("", "  ", "-"):
            self.assertEqual(markdown.parse_uses(v, self.cfg())[1], "")

    def test_invalid(self):
        self.assertEqual(markdown.parse_uses("payment capture", self.cfg())[1], "invalid")
        self.assertEqual(markdown.parse_uses("PAT-905", self.cfg())[1], "invalid")

    def test_step_reads_uses_and_link_text(self):
        self.edit(self.composite, "| PAT-905 S1 payment capture |",
                  "| [PAT-905 S1](../PAT-905-payment-capture/index.md) |")
        m = markdown.read(self.composite, self.cfg())
        steps = m.scenario("S1").steps
        self.assertEqual([s.uses for s in steps], ["", "PAT-905 S1", ""])

    def test_document_without_the_column_is_unchanged(self):
        text = doc(**PARTICIPANT).replace(" Uses |", "").replace("|---|---|---|---|---|---|",
                                                           "|---|---|---|---|---|")
        text = text.replace("| IF-01 |  |", "| IF-01 |")
        self.assertNotIn("Uses", text)
        p = self.write("other/index.md", text)
        m = markdown.read(p, self.cfg(p))
        self.assertTrue(all(s.uses == "" for s in m.scenario("S1").steps))
        self.assertNotIn("uses", json.dumps(m.to_dict()))
        self.assertEqual(composition.findings(m, self.cfg(p)), [])

    def test_uses_is_serialised_when_set_and_round_trips(self):
        m = markdown.read(self.composite, self.cfg())
        d = m.to_dict()
        steps = d["scenarios"][0]["steps"]
        self.assertEqual(steps[1]["uses"], "PAT-905 S1")
        self.assertNotIn("uses", steps[0])
        self.assertEqual(Model.from_dict(d).scenario("S1").steps[1].uses, "PAT-905 S1")

    def test_header_is_configurable(self):
        self.write("skill-bindings.toml", BINDINGS.replace("{extra}", "").replace("{suite}", "")
                   .replace('target = "Target" }', 'target = "Target", uses = "Runs" }'))
        self.edit(self.composite, "| Interface | Uses |", "| Interface | Runs |")
        m = markdown.read(self.composite, self.cfg())
        self.assertEqual(m.scenario("S1").steps[1].uses, "PAT-905 S1")

    def test_pattern_id_is_configurable(self):
        self.write("skill-bindings.toml", BINDINGS.replace("{extra}", "pattern_id = 'X[0-9]+'")
                   .replace("{suite}", ""))
        self.assertEqual(markdown.parse_uses("X12 S3", self.cfg())[:3], ("X12 S3", "ref", "X12"))
        self.assertEqual(markdown.parse_uses("PAT-905 S1", self.cfg())[1], "invalid")

    def test_markdown_writer_keeps_the_call(self):
        c = self.cfg()
        out = os.path.join(self.dir, "round.md")
        markdown.write(markdown.read(self.composite, c), out, c)
        self.assertEqual(markdown.read(out, c).scenario("S1").steps[1].uses, "PAT-905 S1")


# ------------------------------------------------------------------------- validation

class ValidateTests(Base):
    def test_a_resolved_composition_is_clean(self):
        self.assertEqual(self.composition_rules(), [])

    def test_participant_missing(self):
        self.edit(self.composite, "PAT-905 S1 payment capture", "PAT-977 S1")
        self.assertIn(("participant_missing", "error"), self.rules())

    def test_scenario_missing(self):
        self.edit(self.composite, "PAT-905 S1 payment capture", "PAT-905 S4")
        fs = [f for f in self.findings() if f.rule == "participant_scenario_missing"]
        self.assertEqual(len(fs), 1)
        self.assertEqual(fs[0].severity, "error")
        self.assertIn("it has S1", fs[0].message)

    def test_invalid_uses(self):
        self.edit(self.composite, "PAT-905 S1 payment capture", "the payment pattern")
        self.assertIn(("uses_invalid", "error"), self.rules())

    def test_uses_step_needs_actor_and_target(self):
        self.edit(self.composite, "| ABB-901 Order service | ABB-901 Order service | take payment",
                  "| ABB-901 Order service |  | take payment")
        self.assertIn(("uses_step_endpoints", "error"), self.rules())

    def test_interface_is_optional_on_a_uses_step(self):
        self.assertFalse([r for r in self.rules() if r[1] == "error"])

    def test_direct_cycle(self):
        self.edit(self.composite, "PAT-905 S1 payment capture", "PAT-900 S1")
        self.assertIn(("composition_cycle", "error"), self.rules())

    def test_transitive_cycle(self):
        self.edit(self.participant, "| return the result | IF-01 |  |", "| return the result | IF-01 | PAT-900 S1 |")
        fs = [f for f in self.findings() if f.rule == "composition_cycle"]
        self.assertEqual(len(fs), 1)
        self.assertIn("PAT-900 S1 step 2 -> PAT-905 S1 step 2 -> PAT-900 S1", fs[0].message)

    def test_tbd_is_an_open_warning(self):
        self.edit(self.composite, "PAT-905 S1 payment capture", "TBD fraud scoring")
        self.assertEqual(self.composition_rules(), [("participant_open", "warn")])

    def test_join_warns_naming_both_boxes(self):
        # The participating pattern is entered at its local 01, which maps to nothing.
        self.edit(self.participant, "| 1 | ABB-901 Order service | 01 Card processor |",
                  "| 1 | 01 Card processor | ABB-901 Order service |")
        fs = [f for f in self.findings() if f.rule == "participant_join"]
        self.assertEqual(len(fs), 1)
        self.assertEqual(fs[0].severity, "warn")
        self.assertIn("enters at 01 Card processor there", fs[0].message)
        self.assertIn("ABB-901 Order service here", fs[0].message)
        self.assertIn("Catalogue Mapping", fs[0].message)

    def test_join_through_catalogue_mapping(self):
        # The composite enters at local 01, mapped to ABB-901, which the participant uses directly.
        self.edit(self.composite, "| 2 | ABB-901 Order service |", "| 2 | 01 Storefront |")
        self.assertIn(("participant_join", "warn"), self.composition_rules())
        self.edit(self.composite, "| 01 | gap | gap |", "| 01 | ABB-901 Order service | partial |")
        self.assertEqual([r for r in self.composition_rules() if r[0] == "participant_join"], [])

    def test_local_ids_never_match_across_documents(self):
        # Both sides have a local 01, meaning different things: not a join.
        self.edit(self.composite, "| 2 | ABB-901 Order service |", "| 2 | 01 Storefront |")
        self.edit(self.participant, "| 1 | ABB-901 Order service | 01 Card processor |",
                  "| 1 | 01 Card processor | 01 Card processor |")
        self.assertIn(("participant_join", "warn"), self.composition_rules())

    def test_exit_matches_the_last_steps_actor(self):
        # The flow ends with the exit box making a final call to a helper: it leaves at
        # the facade, the last step's actor, not at the helper it called.
        self.edit(self.participant, "| 2 | 01 Card processor | ABB-901 Order service | return the result |",
                  "| 2 | ABB-901 Order service | 01 Card processor | authorise |")
        self.assertEqual([r for r in self.composition_rules() if r[0] == "participant_join"], [])

    def test_exit_warning_names_both_candidates(self):
        self.edit(self.composite, "| ABB-901 Order service | ABB-901 Order service | take payment",
                  "| ABB-901 Order service | 01 Storefront | take payment")
        fs = [f for f in self.findings() if f.rule == "participant_join"]
        self.assertEqual(len(fs), 1)
        self.assertIn("leaves at 01 Card processor or ABB-901 Order service there", fs[0].message)
        self.assertIn("01 Storefront here", fs[0].message)

    def test_ambiguous_participant_warns(self):
        self.pattern("PAT-905-a-copy", where="patterns/elsewhere", **PARTICIPANT)
        self.assertIn(("participant_ambiguous", "warn"), self.composition_rules())

    def test_a_folder_match_wins_over_h1_matches(self):
        # A pattern folder's other documents repeat its id in their H1; not ambiguous.
        self.write("patterns/PAT-905-payment-capture/controls.md", "# PAT-905 Controls\n")
        self.write("patterns/elsewhere/notes.md", "# PAT-905 Notes\n")
        self.assertEqual(self.composition_rules(), [])

    def test_participant_found_by_h1(self):
        shutil.rmtree(os.path.dirname(self.participant))
        self.write("patterns/misc/payments.md", doc(**PARTICIPANT))
        self.assertEqual(self.composition_rules(), [])


class GateTests(Base):
    def approve(self, path, status="Approved"):
        self.edit(path, "status: Draft", f"status: {status}")

    def test_approved_composite_over_approved_participant_passes(self):
        self.approve(self.composite)
        self.assertEqual(self.composition_rules(), [])

    def test_approved_composite_over_draft_participant_fails(self):
        self.approve(self.composite)
        self.edit(self.participant, "status: Approved", "status: Draft")
        fs = [f for f in self.findings() if f.rule == "participant_unapproved"]
        self.assertEqual(len(fs), 1)
        self.assertEqual(fs[0].severity, "error")
        self.assertIn("rests on the participating pattern PAT-905, which is Draft", fs[0].message)

    def test_draft_composite_is_not_gated(self):
        self.edit(self.participant, "status: Approved", "status: Draft")
        self.assertEqual(self.composition_rules(), [])

    def test_gate_is_recursive(self):
        self.approve(self.composite)
        self.pattern("PAT-907-card-vault", **dict(PARTICIPANT, pid="PAT-907", status="Draft"))
        self.edit(self.participant, "| return the result | IF-01 |  |",
                  "| return the result | IF-01 | PAT-907 S1 |")
        fs = [f for f in self.findings() if f.rule == "participant_unapproved"]
        self.assertEqual(len(fs), 1)
        self.assertIn("PAT-907", fs[0].message)
        self.assertIn("through PAT-905", fs[0].message)

    def test_approved_composite_with_tbd_fails(self):
        self.approve(self.composite)
        self.edit(self.composite, "PAT-905 S1 payment capture", "TBD fraud scoring")
        self.assertIn(("participant_unapproved", "error"), self.composition_rules())

    def test_approved_statuses_are_configurable(self):
        self.write("skill-bindings.toml", BINDINGS.replace(
            "{extra}", 'approved_statuses = ["Endorsed"]').replace("{suite}", ""))
        self.approve(self.composite, "Endorsed")
        self.assertIn(("participant_unapproved", "error"), self.composition_rules())
        self.edit(self.participant, "status: Approved", "status: Endorsed")
        self.assertEqual(self.composition_rules(), [])


# ---------------------------------------------------- where participating patterns live

class RootTests(Base):
    def setUp(self):
        super().setUp()
        # Move the participating pattern where the ancestor search cannot reach it.
        target = os.path.join(self.dir, "library", "deep", "er", "PAT-905-payment-capture")
        os.makedirs(os.path.dirname(target))
        shutil.move(os.path.dirname(self.participant), target)
        self.participant = os.path.join(target, "index.md")
        os.makedirs(os.path.join(self.dir, ".git"))

    def bind(self, extra="", suite=""):
        self.write("skill-bindings.toml", BINDINGS.replace("{extra}", extra)
                   .replace("{suite}", suite))

    def test_unbound_ancestors_do_not_reach_it(self):
        self.assertIn(("participant_missing", "error"), self.rules())

    def test_model_patterns_root(self):
        self.bind(extra='patterns_root = "library"')
        self.assertEqual(self.composition_rules(), [])

    def test_suite_pattern_patterns_root(self):
        self.bind(suite='[suite.pattern]\npatternsRoot = "library"\n')
        self.assertEqual(self.composition_rules(), [])
        self.assertEqual(self.cfg().patterns_root_from, "suite.pattern.patternsRoot")

    def test_suite_pattern_output_dir_is_the_fallback(self):
        self.bind(suite='[suite.pattern]\noutputDir = "library"\n')
        self.assertEqual(self.composition_rules(), [])

    def test_doctor_reports_the_root(self):
        self.bind(extra='patterns_root = "library"')
        code, out, _err = self.cli("doctor", "--near", self.dir, "--json")
        ch = json.loads(out)["composition"]
        self.assertEqual(ch["patternsRoot"], os.path.join(self.dir, "library"))
        self.assertEqual(ch["from"], "model.patterns_root")
        self.assertEqual(ch["approvedStatuses"], ["Final", "Approved", "Active", "Published"])

    def test_doctor_fails_on_a_missing_root(self):
        self.bind(extra='patterns_root = "nowhere"')
        code, out, _err = self.cli("doctor", "--near", self.dir, "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["result"], "error")


# ------------------------------------------------------------------ composition report

class ReportTests(Base):
    def test_composition_json(self):
        self.pattern("PAT-907-card-vault", **dict(PARTICIPANT, pid="PAT-907", status="Draft"))
        self.edit(self.participant, "| return the result | IF-01 |  |",
                  "| return the result | IF-01 | PAT-907 S1 |")
        self.edit(self.participant, "| charge the card | IF-01 |  |",
                  "| charge the card | IF-01 | TBD tokenise |")
        code, out, _err = self.cli("composition", self.composite, "--json")
        self.assertEqual(code, 0)
        d = json.loads(out)
        t = d["tree"]
        self.assertEqual((t["id"], t["status"]), ("PAT-900", "Draft"))
        c = t["participations"][0]
        self.assertEqual((c["scenario"], c["step"], c["id"], c["key"]), ("S1", 2, "PAT-905", "S1"))
        self.assertTrue(c["found"] and c["scenarioFound"])
        self.assertEqual(c["participant"]["status"], "Approved")
        kinds = [(x["kind"], x.get("id")) for x in c["participant"]["participations"]]
        self.assertEqual(kinds, [("tbd", None), ("ref", "PAT-907")])
        self.assertEqual(c["participant"]["participations"][1]["participant"]["status"], "Draft")
        self.assertEqual(d["summary"], {"participations": 1, "patterns": 2, "open": 1, "cycles": 0,
                                        "missing": 0, "depth": 2})

    def test_composition_marks_cycles(self):
        self.edit(self.participant, "| return the result | IF-01 |  |",
                  "| return the result | IF-01 | PAT-900 S1 |")
        code, out, _err = self.cli("composition", self.composite, "--json")
        self.assertEqual(code, 1)
        back = json.loads(out)["tree"]["participations"][0]["participant"]["participations"][0]
        self.assertTrue(back["cycle"])
        self.assertEqual(back["participant"]["id"], "PAT-900")

    def test_composition_text(self):
        self.edit(self.composite, "| confirm | IF-01 |  |", "| confirm | IF-01 | TBD notify |")
        code, out, _err = self.cli("composition", self.composite)
        self.assertEqual(code, 0)
        self.assertIn("PAT-900 Order intake [Draft]", out)
        self.assertIn("S1 step 2 runs S1 of PAT-905 Payment capture [Approved]", out)
        self.assertIn("S1 step 3 runs TBD notify  (open participating pattern)", out)

    def test_validate_summarises_the_composition(self):
        code, out, _err = self.cli("validate", self.composite)
        self.assertEqual(code, 0)
        self.assertIn("composition: 1 participation step(s) running 1 participating pattern(s), depth 1", out)
        code, out, _err = self.cli("validate", self.composite, "--json")
        self.assertEqual(json.loads(out)["composition"]["participations"], 1)

    def test_validate_without_uses_has_no_composition(self):
        code, out, _err = self.cli("validate", self.participant, "--json")
        self.assertNotIn("composition", json.loads(out))


# ------------------------------------------------------------------------------ draw.io

class DrawioTests(Base):
    def emit(self):
        c = self.cfg()
        out = os.path.join(os.path.dirname(self.composite), "components.drawio")
        drawio.write(markdown.read(self.composite, c), out, c)
        return out, c

    def flow(self, path, step):
        for o in ET.parse(path).getroot().iter("object"):
            if o.get("scenario") == "S1" and o.get("step") == str(step) and o.find("mxCell").get("edge"):
                return o

    def test_emit_marks_the_call(self):
        out, c = self.emit()
        o = self.flow(out, 2)
        self.assertEqual(o.get("uses"), "PAT-905 S1")
        self.assertEqual(o.get("label"), "2: PAT-905 S1")
        self.assertIn("dashPattern=", o.find("mxCell").get("style"))
        self.assertIsNone(self.flow(out, 1).get("uses"))
        self.assertNotIn("dashPattern=", self.flow(out, 1).find("mxCell").get("style"))
        self.assertEqual(drawio.read(out, c).scenario("S1").steps[1].uses, "PAT-905 S1")

    def test_validate_and_sync_accept_it(self):
        out, c = self.emit()
        d = markdown.read(self.composite, c)
        self.assertEqual([f for f in validate.check(d, c, drawio.read(out, c))
                          if f.severity == "error"], [])
        sync.sync(d, out, c)
        self.assertEqual(self.flow(out, 2).get("uses"), "PAT-905 S1")

    def test_a_changed_call_is_reported_until_synced(self):
        out, c = self.emit()
        self.edit(self.composite, "PAT-905 S1 payment capture", "TBD fraud scoring")
        d = markdown.read(self.composite, c)
        fs = [f for f in validate.check(d, c, drawio.read(out, c)) if f.rule == "step_uses_mismatch"]
        self.assertEqual(len(fs), 1)
        sync.sync(d, out, c)
        self.assertEqual(self.flow(out, 2).get("uses"), "TBD fraud scoring")
        self.assertEqual([f for f in validate.check(d, c, drawio.read(out, c))
                          if f.rule == "step_uses_mismatch"], [])


# ----------------------------------------------------------------------- the walkthrough

class AnimateTests(Base):
    def setUp(self):
        super().setUp()
        self.page = self.prepare(self.composite)
        self.prepare(self.participant)

    def prepare(self, path):
        """Emit the diagram and a structure image the right shape for it."""
        c = self.cfg(path)
        dia = os.path.join(os.path.dirname(path), "components.drawio")
        drawio.write(markdown.read(path, c), dia, c)
        self.edit(path, "---\n\n#", "model:\n  diagram: components.drawio\n---\n\n#")
        _, boxes, _, _ = animate.geometry(dia)
        x0, y0, x1, y1 = animate.bounds(boxes)
        img = os.path.join(os.path.dirname(path), "structure.png")
        with open(img, "wb") as fh:
            fh.write(png(int((x1 - x0) * 2), int((y1 - y0) * 2)))
        return os.path.join(os.path.dirname(path), "scenarios.html")

    def animate(self, path):
        c = self.cfg(path)
        img = os.path.join(os.path.dirname(path), "structure.png")
        data = animate.build(path, c, image=img, force=True)
        out = animate.default_out(path)
        r = animate.write(data, out)
        with open(out, encoding="utf-8") as fh:
            html = fh.read()
        return r, json.loads(re.search(r"const D=(\{.*?\}), W=", html, re.S).group(1)), html

    def test_drill_in_link_is_relative(self):
        self.animate(self.participant)
        r, d, html = self.animate(self.composite)
        u = d["scenarios"][0]["steps"][1]["uses"]
        self.assertEqual(u["ref"], "PAT-905 S1")
        self.assertEqual(u["href"], "../PAT-905-payment-capture/scenarios.html")
        self.assertEqual(u["back"], "../PAT-900-order-intake/scenarios.html")
        self.assertEqual(u["key"], "S1")
        self.assertNotIn("_target", json.dumps(d))
        self.assertEqual(r["notes"], [])
        self.assertNotIn("uses", d["scenarios"][0]["steps"][0])

    def test_the_page_builds_the_hash_and_back_query(self):
        _r, _d, html = self.animate(self.composite)
        self.assertIn('u.href+"?back="+encodeURIComponent(back)+"#"+encodeURIComponent(u.key)', html)
        self.assertIn('"#"+encodeURIComponent(S.key+"-"+s.n)', html)
        self.assertIn("function fromHash()", html)
        self.assertIn('id="back"', html)

    def test_page_stays_standalone(self):
        _r, _d, html = self.animate(self.composite)
        self.assertNotRegex(html, r"fetch\(|XMLHttpRequest|<script[^>]+src=|<link[^>]+href=")
        self.assertEqual(set(re.findall(r"https?://[^\s\"')]+", html)), {"http://www.w3.org/2000/svg"})

    def test_page_embeds_in_a_deck_without_false_assets(self):
        # A deck that embeds the page scans it for local resources: src, poster and
        # href attributes, and CSS url(...), case-insensitively. The script must hold
        # nothing those scans would read as a file, such as src="'+s+'" or drillUrl(s).
        for page in (self.composite, self.participant):
            _r, _d, html = self.animate(page)
            self.assertNotRegex(html, r"(?i)\b(?:src|href|poster)\s*=\s*[\"']?[A-Za-z_$][\w$]*[\"']?(?=[\s;,)>+}]|$)")
            urls = [u for _q, u in re.findall(r"(?i)url\(\s*([\"']?)([^\"')]+)\1\s*\)", html)]
            self.assertTrue(all(u.startswith("#") for u in urls), urls)
            attrs = re.findall(r"(?i)\s(?:src|poster)\s*=\s*([\"'])([^\"']*)\1", html)
            self.assertTrue(all(v.startswith("data:") for _q, v in attrs), attrs)

    def test_back_link_rejects_anything_but_a_relative_url(self):
        _r, _d, html = self.animate(self.participant)
        guard = re.search(r"const BACK=.*?;\n", html).group(0)
        self.assertIn("[a-z][a-z0-9+.-]*:", guard)

    def test_unbuilt_participant_is_noted(self):
        r, _d, _html = self.animate(self.composite)
        self.assertEqual(len(r["notes"]), 1)
        self.assertIn("not built yet", r["notes"][0])

    def test_tbd_has_no_link(self):
        self.edit(self.composite, "PAT-905 S1 payment capture", "TBD fraud scoring")
        c = self.cfg()
        drawio.write(markdown.read(self.composite, c), os.path.join(os.path.dirname(self.composite),
                                                                  "components.drawio"), c)
        _r, d, _html = self.animate(self.composite)
        u = d["scenarios"][0]["steps"][1]["uses"]
        self.assertEqual(u, {"ref": "TBD fraud scoring", "kind": "tbd"})

    def test_page_without_calls_is_unchanged_in_behaviour(self):
        _r, d, _html = self.animate(self.participant)
        self.assertTrue(all("uses" not in s for sc in d["scenarios"] for s in sc["steps"]))


if __name__ == "__main__":
    unittest.main()
