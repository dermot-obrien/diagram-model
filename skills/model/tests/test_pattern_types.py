# SPDX-License-Identifier: Apache-2.0
"""Pattern types: a repository's kinds of pattern, each with its own identifier series and
expectation of how physical it is, and a document's `implements`. Standard library only:

    python -m unittest discover -s tests
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from model import config, markdown, validate  # noqa: E402

BINDINGS = textwrap.dedent("""\
    bindingsVersion = "1.0"

    [model]
    local_pattern = '[0-9]{1,3}'

    [[markdown.tables]]
    section    = "Building Blocks"
    entity     = "node"
    id_pattern = '(ABB|SBB)-[0-9]{3}'
    columns    = { id = "Building Block", label = "Building Block" }

    [[catalogues]]
    path   = "abb.csv"
    column = "id"
    level  = "logical"

    [[catalogues]]
    path   = "sbb.csv"
    column = "id"
    level  = "physical"

    [suite.pattern]
    patternsRoot = "patterns"

    [suite.pattern.types.architecture-pattern]
    label    = "Architecture pattern"
    idSeries = "AP"
    physical = "none"

    [suite.pattern.types.reference-architecture]
    label    = "Reference architecture"
    idSeries = "RA"
    physical = "most"
    """)


def doc(pid, title, blocks, front="", tail=""):
    """A pattern document. A block given as (box, realised) gets a Realises column."""
    realising = any(isinstance(b, tuple) for b in blocks)
    out = ["---", "status: Draft", *([front] if front else []), "---", "",
           f"# {pid} {title}", "", "## Building Blocks", ""]
    if realising:
        out += ["| Building Block | Role | Realises |", "|---|---|---|"]
        out += [f"| {b[0]} | a role | {b[1]} |" if isinstance(b, tuple) else f"| {b} | a role | |"
                for b in blocks]
    else:
        out += ["| Building Block | Role |", "|---|---|"]
        out += [f"| {b} | a role |" for b in blocks]
    return "\n".join(out) + "\n" + (f"\n{tail}\n" if tail else "")


class TypeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.write("skill-bindings.toml", BINDINGS)
        self.write("abb.csv", "id\nABB-001\nABB-002\n")
        self.write("sbb.csv", "id\nSBB-001\nSBB-002\nSBB-003\n")
        os.makedirs(os.path.join(self.dir, ".git"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, rel, text):
        p = os.path.join(self.dir, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return p

    def pattern(self, folder, *args, **kw):
        return self.write(f"patterns/{folder}/index.md", doc(*args, **kw))

    def rules(self, path):
        c = config.load(None, near=path)
        return [(f.rule, f.severity) for f in validate.check(markdown.read(path, c), c)
                if f.rule.startswith(("pattern_type", "implements"))]

    def test_types_load(self):
        p = self.pattern("AP-001-x", "AP-001", "X", ["ABB-001 Gateway"])
        c = config.load(None, near=p)
        self.assertEqual(sorted(c.pattern_types), ["architecture-pattern", "reference-architecture"])
        self.assertEqual(c.pattern_types["reference-architecture"].id_series, "RA")

    def test_agnostic_pattern_of_abbs_passes(self):
        p = self.pattern("AP-001-x", "AP-001", "X", ["ABB-001 Gateway", "01 Client"])
        self.assertEqual(self.rules(p), [])

    def test_agnostic_pattern_with_an_sbb_warns(self):
        p = self.pattern("AP-001-x", "AP-001", "X", ["ABB-001 Gateway", "SBB-001 Kong"])
        self.assertEqual(self.rules(p), [("pattern_type_physical", "warn")])

    def test_type_is_inferred_from_the_series(self):
        p = self.pattern("RA-001-x", "RA-001", "X", ["ABB-001 Gateway", "ABB-002 Store"])
        self.assertEqual(self.rules(p), [("pattern_type_physical", "warn")])

    def test_reference_architecture_of_mainly_sbbs_passes(self):
        p = self.pattern("RA-001-x", "RA-001", "X",
                         ["SBB-001 Kong", "SBB-002 Postgres", "SBB-003 Redis", "ABB-001 Gateway", "01 Client"])
        self.assertEqual(self.rules(p), [])

    def test_declared_type_in_the_wrong_series_warns(self):
        p = self.pattern("RA-002-x", "RA-002", "X", ["ABB-001 Gateway"],
                         front="pattern_type: architecture-pattern")
        self.assertEqual(self.rules(p), [("pattern_type_series", "warn")])

    def test_unknown_type_is_an_error(self):
        p = self.pattern("AP-003-x", "AP-003", "X", ["ABB-001 Gateway"],
                         front="pattern_type: blueprint")
        self.assertEqual(self.rules(p), [("pattern_type_unknown", "error")])

    def test_other_documents_are_not_checked(self):
        p = self.pattern("UC-001-x", "UC-001", "X", ["SBB-001 Kong"])
        self.assertEqual(self.rules(p), [])

    def test_implements_finds_its_pattern(self):
        self.pattern("integration/AP-004-x", "AP-004", "X", ["ABB-001 Gateway"])
        p = self.pattern("platform/RA-005-x", "RA-005", "X",
                         [("SBB-001 Kong", "ABB-001 Gateway"), "SBB-002 Postgres"],
                         front="implements: [AP-004]")
        self.assertEqual(self.rules(p), [])

    # implements_uncovered: every catalogued box of the implemented pattern is accounted for.

    def implemented(self):
        self.pattern("AP-010-x", "AP-010", "X", ["ABB-001 Gateway", "ABB-002 Store", "01 Client"])

    def findings(self, path):
        c = config.load(None, near=path)
        return [f for f in validate.check(markdown.read(path, c), c) if f.rule == "implements_uncovered"]

    def test_a_block_nothing_realises_warns_and_is_named(self):
        self.implemented()
        p = self.pattern("RA-011-x", "RA-011", "X",
                         [("SBB-001 Kong", "ABB-001 Gateway"), "SBB-002 Postgres"],
                         front="implements: [AP-010]")
        got = self.findings(p)
        self.assertEqual([(f.rule, f.severity) for f in got], [("implements_uncovered", "warn")])
        self.assertIn("ABB-002 Store", got[0].message)
        self.assertNotIn("ABB-001", got[0].message)
        self.assertNotIn("01 Client", got[0].message)   # a local role is not counted

    def test_one_box_may_realise_two_blocks(self):
        self.implemented()
        p = self.pattern("RA-012-x", "RA-012", "X",
                         [("SBB-001 Kong", "ABB-001 Gateway, ABB-002 Store")],
                         front="implements: [AP-010]")
        self.assertEqual(self.findings(p), [])

    def test_a_block_drawn_as_itself_is_accounted_for(self):
        self.implemented()
        p = self.pattern("RA-013-x", "RA-013", "X",
                         [("SBB-001 Kong", "ABB-001 Gateway"), "SBB-002 Postgres", "SBB-003 Redis",
                          "ABB-002 Store"],
                         front="implements: [AP-010]")
        self.assertEqual(self.findings(p), [])

    def test_a_gap_named_under_risks_is_accounted_for(self):
        self.implemented()
        tail = ("## Decisions\n\nABB-001 Gateway is mentioned here.\n\n"
                "## Risks and Trade-offs\n\n| Risk/Trade-off | Mitigation |\n|---|---|\n"
                "| ABB-002 Store has no product yet | Chosen in RA-020 |")
        p = self.pattern("RA-014-x", "RA-014", "X", ["SBB-001 Kong"],
                         front="implements: [AP-010]", tail=tail)
        got = self.findings(p)
        self.assertEqual(len(got), 1)
        self.assertIn("ABB-001 Gateway", got[0].message)   # a mention outside Risks does not count
        self.assertNotIn("ABB-002", got[0].message)

    def test_a_gap_in_a_comment_does_not_count(self):
        self.implemented()
        tail = "## Risks and Trade-offs\n\n<!-- ABB-001 and ABB-002 are gaps -->\n"
        p = self.pattern("RA-015-x", "RA-015", "X", ["SBB-001 Kong"],
                         front="implements: [AP-010]", tail=tail)
        self.assertEqual(len(self.findings(p)), 1)

    def test_a_local_box_mapped_to_the_block_accounts_for_it(self):
        self.implemented()
        tail = ("## Catalogue Mapping\n\n| Local ID | Maps To | Relationship |\n|---|---|---|\n"
                "| 07 | ABB-002 Store | realises |")
        p = self.pattern("RA-016-x", "RA-016", "X",
                         [("SBB-001 Kong", "ABB-001 Gateway"), "07 Store, no product yet"],
                         front="implements: [AP-010]", tail=tail)
        self.assertEqual(self.findings(p), [])

    def test_a_local_role_mapped_in_the_pattern_must_be_accounted_for(self):
        tail = ("## Catalogue Mapping\n\n| Local ID | Maps To | Relationship |\n|---|---|---|\n"
                "| 01 | ABB-002 Store | realises |")
        self.pattern("AP-017-x", "AP-017", "X", ["ABB-001 Gateway", "01 Store role"], tail=tail)
        p = self.pattern("RA-018-x", "RA-018", "X", [("SBB-001 Kong", "ABB-001 Gateway")],
                         front="implements: [AP-017]")
        got = self.findings(p)
        self.assertEqual(len(got), 1)
        self.assertIn("ABB-002", got[0].message)

    def test_each_implemented_pattern_is_checked(self):
        self.implemented()
        self.pattern("AP-019-x", "AP-019", "X", ["ABB-002 Store"])
        p = self.pattern("RA-020-x", "RA-020", "X",
                         [("SBB-001 Kong", "ABB-001 Gateway"), ("SBB-002 Postgres", "ABB-002 Store")],
                         front="implements: [AP-010, AP-019]")
        self.assertEqual(self.findings(p), [])

    def test_the_rule_can_be_turned_off(self):
        self.implemented()
        self.write("skill-bindings.toml", BINDINGS + '\n[rules]\nimplements_uncovered = "off"\n')
        p = self.pattern("RA-021-x", "RA-021", "X", ["SBB-001 Kong"], front="implements: [AP-010]")
        self.assertEqual(self.findings(p), [])

    def test_implements_a_missing_pattern_warns(self):
        p = self.pattern("RA-006-x", "RA-006", "X", ["SBB-001 Kong"],
                         front="implements: [AP-404, AP-405]")
        self.assertEqual(self.rules(p), [("implements_missing", "warn")] * 2)

    def test_a_bad_physical_value_is_refused(self):
        self.write("skill-bindings.toml", BINDINGS.replace('physical = "most"', 'physical = "lots"'))
        p = self.pattern("RA-001-x", "RA-001", "X", ["SBB-001 Kong"])
        with self.assertRaises(SystemExit):
            config.load(None, near=p)

    def test_no_types_bound_checks_nothing(self):
        self.write("skill-bindings.toml", BINDINGS.split("\n[suite.pattern.types")[0])
        p = self.pattern("AP-001-x", "AP-001", "X", ["SBB-001 Kong"])
        self.assertEqual(self.rules(p), [])


if __name__ == "__main__":
    unittest.main()
