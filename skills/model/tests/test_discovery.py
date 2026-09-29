# SPDX-License-Identifier: Apache-2.0
"""Finding other skills wherever an agent installed them, not only beside this one.

    python -m unittest discover -s tests
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from model import bindings  # noqa: E402


def skill(root, *parts, requires=None):
    d = os.path.join(root, *parts)
    os.makedirs(d, exist_ok=True)
    meta = f'  x-skill-requires: "{requires}"\n' if requires is not None else ""
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(f"---\nname: {parts[-1]}\ndescription: test\nmetadata:\n{meta}---\n")
    return d


class Discovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        self.home = os.path.join(self.root, "home")
        os.makedirs(self.home)
        env = {"HOME": self.home, "USERPROFILE": self.home,
               "CLAUDE_CONFIG_DIR": os.path.join(self.home, ".claude")}
        self.patches = [mock.patch.dict(os.environ, env),
                        mock.patch.object(os.path, "expanduser",
                                          lambda p: p.replace("~", self.home, 1)),
                        mock.patch.object(os, "getcwd", lambda: os.path.join(self.root, "project"))]
        for p in self.patches:
            p.start()
        os.environ.pop(bindings.SKILLS_PATH_ENV, None)
        self.project = os.path.join(self.root, "project")
        self.pattern = skill(self.project, ".agents", "skills", "pattern",
                             requires="model@^0.6.0, markdown-deck@^0.6.0")

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_siblings_in_one_directory(self):
        model = skill(self.project, ".agents", "skills", "model", requires="")
        self.assertEqual(bindings.sibling_skills(self.pattern)["model"], model)

    def test_declared_dependency_installed_by_another_tool(self):
        deck = skill(self.project, ".github", "skills", "markdown-deck", requires="")
        model = skill(self.home, ".cursor", "skills", "model", requires="")
        found = bindings.sibling_skills(self.pattern)
        self.assertEqual(found["markdown-deck"], deck)
        self.assertEqual(found["model"], model)

    def test_undeclared_skills_elsewhere_are_not_reported(self):
        skill(self.home, ".copilot", "skills", "unrelated", requires="")
        self.assertNotIn("unrelated", bindings.sibling_skills(self.pattern))

    def test_agent_skills_path(self):
        other = os.path.join(self.root, "elsewhere")
        deck = skill(other, "markdown-deck", requires="")
        os.environ[bindings.SKILLS_PATH_ENV] = other
        self.assertEqual(bindings.sibling_skills(self.pattern)["markdown-deck"], deck)

    def test_claude_code_plugin_newest_version(self):
        cache = os.path.join(self.home, ".claude", "plugins", "cache", "markdown-deck", "markdown-deck")
        skill(cache, "0.6.0", "skills", "markdown-deck", requires="")
        newest = skill(cache, "0.10.0", "skills", "markdown-deck", requires="")
        self.assertEqual(bindings.sibling_skills(self.pattern)["markdown-deck"], newest)

    def test_purl_requirements_name_their_skills(self):
        pattern = skill(self.project, ".agents", "skills", "pattern2",
                        requires="pkg:generic/owner/diagram-model/model ^0.7.0, "
                                 "pkg:generic/owner/markdown-deck/markdown-deck ^0.6.0")
        deck = skill(self.project, ".github", "skills", "markdown-deck", requires="")
        model = skill(self.home, ".cursor", "skills", "model", requires="")
        found = bindings.sibling_skills(pattern)
        self.assertEqual(found["markdown-deck"], deck)
        self.assertEqual(found["model"], model)

    def test_requirement_name_in_both_forms(self):
        name = bindings.requirement_name
        self.assertEqual(name("pkg:generic/owner/diagram-model/model ^0.7.0"), "model")
        self.assertEqual(name("pkg:generic/owner/diagram-model/model@0.7.0"), "model")
        self.assertEqual(name("  pkg:generic/owner/bundle/some-skill >=1.2.0 <2.0.0 "), "some-skill")
        self.assertEqual(name("model@^0.6.0"), "model")
        self.assertEqual(name("markdown-deck"), "markdown-deck")
        self.assertEqual(name(""), "")

    def test_find_skill_by_name_from_model(self):
        model = skill(self.home, ".agents", "skills", "model", requires="")
        self.assertEqual(bindings.find_skill("pattern", model), self.pattern)
        self.assertIsNone(bindings.find_skill("absent", model))


if __name__ == "__main__":
    unittest.main()
