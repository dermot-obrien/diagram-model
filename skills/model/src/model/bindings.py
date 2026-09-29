# SPDX-License-Identifier: Apache-2.0
"""Resolve and check what the host repository has told this skill.

A published skill is opinionated about WHAT it needs and must not assume WHERE any of it
lives. The consuming repository declares that in a binding file. This module turns those
declarations into resolved absolute paths, and says loudly when one does not resolve.

The loudness is the point. Measured precondition-violation rates for coding agents run
from roughly a third to over four fifths, and a broken path reference inside a SKILL.md
raises nothing at all: the agent looks, finds nothing and carries on. So the binding is
read by code rather than by the agent, and every declared path is checked at the point of
use rather than assumed.

`inputs.toml` beside each skill declares that skill's contract: which keys it needs, their
type, whether they are required, and their default. Checking a repository's bindings
against that contract is what makes a wrong install a stopped run instead of a wrong one.
"""
from __future__ import annotations

import hashlib
import os
import re

try:
    import tomllib
except ModuleNotFoundError:                      # Python < 3.11
    tomllib = None

PATH_TYPES = ("path", "dir", "file")


class Issue:
    __slots__ = ("level", "where", "message")

    def __init__(self, level, where, message):
        self.level, self.where, self.message = level, where, message

    def __str__(self):
        return f"{self.level}  {self.where}: {self.message}"

    def to_dict(self):
        return {"level": self.level, "where": self.where, "message": self.message}


def load_contract(skill_dir: str) -> dict:
    """The inputs.toml contract beside a skill, or {} when it declares none."""
    p = os.path.join(skill_dir, "inputs.toml")
    if not os.path.exists(p) or tomllib is None:
        return {}
    with open(p, "rb") as fh:
        return tomllib.load(fh)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _template_stem(raw: str):
    """The directory part of a templated path, before its first {placeholder}.

    None when the path carries no placeholder. A binding may be written once and mean a
    different location per run, `planning/{quarter}/calendar.csv` being
    the case this was added for. Checking such a path for existence is checking a name
    nothing ever has, so the stable part in front of it is checked instead.
    """
    m = re.search(r"\{[A-Za-z_][A-Za-z0-9_]*\}", raw)
    if not m:
        return None
    head = raw[:m.start()]
    cut = max(head.rfind("/"), head.rfind(os.sep))
    return head[:cut] if cut > 0 else ""


def check_section(values: dict, contract: dict, cfg, where: str) -> tuple:
    """Check one skill's bindings against its declared contract.

    Returns (resolved, issues). Unknown keys are reported rather than dropped: a typo in
    a binding name is otherwise indistinguishable from a binding that was never set.
    """
    resolved, issues = {}, []
    options = (contract.get("inputs") or {}).get("options") or {}

    for name, spec in options.items():
        required = bool(spec.get("required"))
        typ = str(spec.get("type", "str"))
        raw = values.get(name, spec.get("default"))

        if raw in (None, ""):
            if required:
                issues.append(Issue("error", where,
                                    f"'{name}' is required and not set. {spec.get('description', '')}".strip()))
            continue

        if typ in PATH_TYPES:
            full = cfg.resolve(str(raw))
            resolved[name] = full
            stem = _template_stem(str(raw))
            if stem is not None:
                # A templated path, such as one carrying {quarter}. Only the part before
                # the first placeholder is a real location, so that is what is checked. The
                # skill that owns the placeholder is the only thing that can fill it.
                anchor = cfg.resolve(stem) if stem else cfg.resolve(".")
                if not os.path.isdir(anchor):
                    issues.append(Issue("error", where,
                                        f"'{name}' is a template and the part before its "
                                        f"first placeholder, {anchor}, does not exist"))
            elif not os.path.exists(full):
                issues.append(Issue("error", where,
                                    f"'{name}' points at {full}, which does not exist"))
            elif typ == "dir" and not os.path.isdir(full):
                issues.append(Issue("error", where, f"'{name}' is not a directory: {full}"))
            elif typ == "file" and not os.path.isfile(full):
                issues.append(Issue("error", where, f"'{name}' is not a file: {full}"))
            if os.path.isabs(str(raw)):
                issues.append(Issue("warn", where,
                                    f"'{name}' is an absolute path. It will not survive a "
                                    f"clone on another machine; make it relative to the "
                                    f"binding file"))
        else:
            resolved[name] = raw

        choices = spec.get("choices")
        if choices and raw not in choices:
            issues.append(Issue("error", where,
                                f"'{name}' is '{raw}'; expected one of {', '.join(map(str, choices))}"))

        # A path binding may be pinned by a sibling `<name>Sha256` binding. This is how a
        # shared artefact, vendored once into the repository rather than fetched at run
        # time or copied into every skill, is held to the version that was reviewed.
        want = spec.get("sha256") or values.get(f"{name}Sha256")
        if want and typ in PATH_TYPES and os.path.isfile(resolved.get(name, "")):
            got = sha256(resolved[name])
            if got != want:
                issues.append(Issue("error", where,
                                    f"'{name}' has digest {got[:16]}... but the binding "
                                    f"pins {want[:16]}...; the vendored copy has drifted. "
                                    f"Review the change, then update {name}Sha256"))

    for name in values:
        if options and name not in options:
            issues.append(Issue("warn", where, f"'{name}' is not a binding this skill declares"))

    return resolved, issues


SKILLS_PATH_ENV = "AGENT_SKILLS_PATH"


def _version_key(name: str) -> tuple:
    """Sort key for a plugin cache version directory: numeric parts first, so 0.10 > 0.9."""
    return tuple(int(p) if p.isdigit() else -1 for p in name.split("-")[0].split("."))


def _plugin_skill_roots() -> list:
    """The `skills/` directories of Claude Code plugins, newest version of each first.

    A plugin is cached at `<config>/plugins/cache/<marketplace>/<plugin>/<version>/`, so
    two skills installed as two plugins do not share a parent directory the way skills
    installed into one `.agents/skills/` do.
    """
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    cache = os.path.join(config, "plugins", "cache")
    roots = []
    if not os.path.isdir(cache):
        return roots
    for market in sorted(os.listdir(cache)):
        mdir = os.path.join(cache, market)
        if not os.path.isdir(mdir):
            continue
        for plugin in sorted(os.listdir(mdir)):
            pdir = os.path.join(mdir, plugin)
            if not os.path.isdir(pdir):
                continue
            for version in sorted(os.listdir(pdir), key=_version_key, reverse=True):
                skills = os.path.join(pdir, version, "skills")
                if os.path.isdir(skills):
                    roots.append(skills)
    return roots


def sibling_skills(skill_dir: str) -> dict:
    """Other skills installed beside this one, by directory name.

    Discovery rather than assumption. A skill suite is normally installed into one
    skills directory, but nothing guarantees it, so a caller that needs a sibling asks
    here and gets an honest answer instead of a hardcoded `../name`.

    Looked for, first found wins: the directory this skill is installed in, and each
    directory in the AGENT_SKILLS_PATH environment variable (separated as PATH is).

    Agents disagree about where skills go, and one person may install with more than
    one tool, so a skill that those declare in `metadata.x-skill-requires` but that is
    not there is then looked for in every directory an agent reads skills from: the
    project's `.agents/skills`, `.github/skills`, `.cursor/skills`, `.claude/skills` and
    `.codex/skills` (the project being any folder above this skill or above the working
    directory), the user's `~/.agents/skills`, `~/.copilot/skills`, `~/.cursor/skills`,
    `~/.claude/skills`, `~/.gemini/skills` and `~/.codex/skills`, and last the skills of installed Claude Code plugins, where
    a dependency installed as its own plugin lives in a directory of its own. Only
    declared dependencies are looked for there, so unrelated skills are not reported.
    """
    parents = [os.path.dirname(os.path.abspath(skill_dir))]
    parents += [p for p in os.environ.get(SKILLS_PATH_ENV, "").split(os.pathsep) if p]
    out = {}
    for parent in parents:
        for name, d in _skills_in(parent):
            out.setdefault(name, d)
    wanted = {n for d in out.values() for n in _declared_requires(d)} - set(out)
    if wanted:
        for parent in _agent_skill_roots(skill_dir) + _plugin_skill_roots():
            for name, d in _skills_in(parent):
                if name in wanted:
                    out.setdefault(name, d)
    return dict(sorted(out.items()))


PROJECT_SKILL_DIRS = (".agents/skills", ".github/skills", ".cursor/skills", ".claude/skills",
                      ".codex/skills")
USER_SKILL_DIRS = (".agents/skills", ".copilot/skills", ".cursor/skills", ".claude/skills",
                   ".gemini/skills", ".codex/skills")


def _agent_skill_roots(skill_dir: str) -> list:
    """Every directory an agent reads skills from, project level first, then user level."""
    roots = []
    for start in (os.path.abspath(skill_dir), os.getcwd()):
        d = start
        while True:
            roots += [os.path.join(d, *rel.split("/")) for rel in PROJECT_SKILL_DIRS]
            up = os.path.dirname(d)
            if up == d:
                break
            d = up
    home = os.path.expanduser("~")
    roots += [os.path.join(home, *rel.split("/")) for rel in USER_SKILL_DIRS]
    seen, ordered = set(), []
    for r in roots:
        key = os.path.normcase(r)
        if key not in seen:
            seen.add(key)
            ordered.append(r)
    return ordered


def find_skill(name: str, skill_dir: str):
    """One named skill, looked for in the same places as a declared dependency, or None.

    For when the caller knows the name it wants: `doctor --skill pattern` run from a
    model skill that one tool installed in `.agents/skills`, while another tool put
    pattern in `.github/skills`.
    """
    roots = [os.path.dirname(os.path.abspath(skill_dir))]
    roots += [p for p in os.environ.get(SKILLS_PATH_ENV, "").split(os.pathsep) if p]
    roots += _agent_skill_roots(skill_dir) + _plugin_skill_roots()
    for root in roots:
        d = os.path.join(root, name)
        if os.path.exists(os.path.join(d, "SKILL.md")):
            return d
    return None


def _skills_in(parent: str) -> list:
    if not os.path.isdir(parent):
        return []
    return [(name, os.path.join(parent, name)) for name in sorted(os.listdir(parent))
            if os.path.exists(os.path.join(parent, name, "SKILL.md"))]


def requirement_name(part: str) -> str:
    """The skill name in one requirement, in either form a SKILL.md may use.

    A Package URL and a range, `pkg:generic/<owner>/<bundle>/<skill> ^0.7.0`, names the skill
    in its last path segment. The older form, `<skill>@^0.6.0`, names it before the `@`.
    """
    part = part.strip()
    if part.startswith("pkg:"):
        ident = part.split()[0].split("@")[0].split("?")[0].split("#")[0]
        return ident.rstrip("/").rsplit("/", 1)[-1]
    return part.split("@")[0].split()[0] if part else ""


def _declared_requires(skill_dir: str) -> list:
    """Skill names from `metadata.x-skill-requires` in SKILL.md: comma-separated
    requirements, each a Package URL and a range, or the older `name@range`."""
    try:
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read(8192)
    except OSError:
        return []
    m = re.search(r"^\s+x-skill-requires:\s*[\"']?([^\"'\n]*)", text, re.M)
    if not m:
        return []
    return [n for n in (requirement_name(p) for p in m.group(1).split(",")) if n]


def report(cfg, skill_dir: str, skill: str = "model") -> tuple:
    """Everything this skill can say about how it has been bound. (payload, issues)."""
    issues = []
    payload = {
        "skill": skill,
        "bindingFile": cfg.path or "(none; built-in defaults in use)",
        "bindingsVersion": cfg.version,
        "anchor": os.path.abspath(cfg.root),
        "resolved": {},
        "catalogues": [],
        "siblings": sibling_skills(skill_dir),
    }

    if not cfg.path:
        issues.append(Issue("warn", "bindings",
                            "no binding file found; built-in defaults are in use. Add "
                            ".agents/skill-bindings.toml to bind this repository's layout"))

    # Catalogues carry their own checks in validate.load_catalogue; mirror the summary
    # here so `doctor` is a single place to look.
    from .validate import load_catalogue
    ids, problems = load_catalogue(cfg)
    for cat in cfg.catalogues:
        payload["catalogues"].append({
            "path": cat.path, "column": cat.column, "resolved": cfg.resolve(cat.path),
            "exists": os.path.exists(cfg.resolve(cat.path)),
        })
    for cat, msg in problems:
        issues.append(Issue("error", cat.path, msg))
    payload["catalogueIdentifiers"] = len(ids)

    # Where a scenario step's Uses finds the pattern it calls. Unbound is fine: the
    # folders above each document are searched instead. Bound to nothing is an error.
    from .chain import Resolver
    search = Resolver(cfg).describe()
    payload["chain"] = {**search, "approvedStatuses": list(cfg.approved_statuses),
                        "patternId": cfg.pattern_id}
    if search["patternsRoot"] and not search["exists"]:
        issues.append(Issue("error", search["from"],
                            f"the patterns root {search['patternsRoot']} does not exist"))

    contract = load_contract(skill_dir)
    if contract:
        values = dict(cfg.suite.get(skill, {}))
        resolved, more = check_section(values, contract, cfg, f"suite.{skill}")
        payload["resolved"] = resolved
        issues += more

    payload["issues"] = [i.to_dict() for i in issues]
    payload["result"] = ("error" if any(i.level == "error" for i in issues)
                         else "warn" if issues else "ok")
    return payload, issues
