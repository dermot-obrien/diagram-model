# SPDX-License-Identifier: Apache-2.0
"""model contract: whether a document or a template has the structure the binding reads,
so a repository can replace a shipped template with its own. Standard library only:

    python -m unittest discover -s tests
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from model import cli, config, contract  # noqa: E402

BINDINGS = textwrap.dedent("""\
    bindingsVersion = "1.0"

    [model]
    local_pattern = '[0-9]{1,3}'

    [[markdown.tables]]
    section    = "Building Blocks"
    entity     = "node"
    id_pattern = 'SBB-[0-9]{3}'
    columns    = { id = "Building Block", label = "Building Block", group = "Realises" }

    [[markdown.tables]]
    section    = "Interfaces"
    entity     = "edge"
    id_pattern = 'IF-[0-9]{2}'
    columns    = { id = "Interface", source = "Provider", target = "Consumer" }

    [suite.pattern.types.reference-architecture]
    label    = "Reference architecture"
    idSeries = "RA"
    """)

GOOD = textwrap.dedent("""\
    ---
    status: Draft
    ---

    # RA-NNN Name

    <!-- guidance -->

    ## Building Blocks

    | Building Block | Role | Realises |
    |---|---|---|

    ## Interfaces

    | Interface | Provider | Consumer | Purpose |
    |---|---|---|---|
    | IF-01 | SBB-NNN | 01 Role | what |

    ## Scenarios

    ### S1 Scenario name

    | Step | Actor | Target | Action | Interface |
    |---:|---|---|---|---|
    """)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.write("skill-bindings.toml", BINDINGS)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, rel, text):
        p = os.path.join(self.dir, rel)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return p

    def rules(self, text, type_name=""):
        p = self.write("t.md", text)
        return [(f.rule, f.severity) for f in contract.check(p, config.load(None, near=p), type_name)]

    def test_a_template_with_empty_tables_passes(self):
        self.assertEqual(self.rules(GOOD), [])

    def test_a_missing_section(self):
        self.assertEqual(self.rules(GOOD.replace("## Interfaces", "## Connections")),
                         [("contract_section", "error")])

    def test_a_missing_bound_column(self):
        self.assertEqual(self.rules(GOOD.replace("| Realises |", "| Source |")),
                         [("contract_columns", "error")])

    def test_columns_match_without_case(self):
        self.assertEqual(self.rules(GOOD.replace("| Realises |", "| realises |")), [])

    def test_a_section_without_a_table(self):
        text = GOOD.replace("| Interface | Provider | Consumer | Purpose |\n|---|---|---|---|\n"
                            "| IF-01 | SBB-NNN | 01 Role | what |\n", "")
        self.assertEqual(self.rules(text), [("contract_table", "error")])

    def test_no_scenario_heading(self):
        self.assertEqual(self.rules(GOOD.replace("### S1 Scenario name", "### First scenario")),
                         [("contract_scenario", "error")])

    def test_a_steps_table_without_target_warns(self):
        text = GOOD.replace("| Step | Actor | Target | Action | Interface |\n|---:|---|---|---|---|",
                            "| Step | Actor | Action |\n|---:|---|---|")
        self.assertEqual(self.rules(text), [("contract_columns", "warn")])

    def test_headings_in_code_and_comments_do_not_count(self):
        text = GOOD.replace("## Interfaces", "<!--\n## Interfaces\n-->\n## Elsewhere")
        self.assertIn(("contract_section", "error"), self.rules(text))

    def test_type_checks_the_series(self):
        self.assertEqual(self.rules(GOOD, "reference-architecture"), [])
        self.assertEqual(self.rules(GOOD.replace("# RA-NNN", "# PAT-NNN"), "reference-architecture"),
                         [("contract_series", "warn")])
        self.assertEqual(self.rules(GOOD, "blueprint"), [("pattern_type_unknown", "error")])

    def test_cli_reads_the_binding_near_another_folder(self):
        elsewhere = tempfile.mkdtemp()
        try:
            p = os.path.join(elsewhere, "template.md")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(GOOD.replace("| Realises |", "| Source |"))
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = cli.main(["contract", p, "--near", self.dir, "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out.getvalue())["results"][0]["result"], "error")
        finally:
            shutil.rmtree(elsewhere, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
