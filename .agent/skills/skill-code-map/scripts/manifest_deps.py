#!/usr/bin/env python3
"""Experiment 2: derive real cross-repo dependency edges from package manifests.

For every repo it (1) finds manifests with `git ls-files` (no tree scan), (2) collects the repo's own
package identities and (3) the dependencies each manifest declares. An edge A -> B exists when A declares a
dependency that matches an identity owned by B. Read-only.

Usage:
  python3 scripts/manifest_deps.py --root <dir containing the clones> --repos a b c > edges.json
"""

import argparse
import collections
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ALL_REPOS = [
    "adk-python",
    "ax",
    "brotli",
    "comprehensive-rust",
    "dagger",
    "filament",
    "flatbuffers",
    "googletest",
    "gson",
    "guava",
    "gvisor",
    "kubernetes",
    "langextract",
    "libphonenumber",
    "magika",
    "or-tools",
    "skills",
    "styleguide",
    "yapf",
    "zx",
]
MANIFESTS = [
    "pom.xml",
    "go.mod",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "requirements*.txt",
    "MODULE.bazel",
    "WORKSPACE",
    "*.bzl",
    "*.gradle",
    "*.gradle.kts",
    "CMakeLists.txt",
]
# Names that identify the same project in different build systems.
ALIASES = {"gtest": "googletest", "gmock": "googletest", "googletest": "googletest"}
SKIP = re.compile(r"(^|/)(third_party|vendor|node_modules|testdata|tests?_data|examples?|docs?)(/|$)")
MAX_FILES = 3000


def manifests(root: Path, repo: str) -> list[str]:
    spec = [f"*{m}" for m in MANIFESTS]
    out = subprocess.run(
        ["git", "-C", str(root / repo), "ls-files", "--", *spec], capture_output=True, text=True, check=True
    ).stdout.split()
    return [p for p in out if not SKIP.search(p)][:MAX_FILES]


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def parse_pom(text: str):
    own, deps = set(), set()
    try:
        text = re.sub(r"<\?xml[^>]*\?>", "", text)
        text = re.sub(r"\s(xmlns(:\w+)?|xsi:\w+)=\"[^\"]*\"", "", text)
        root = ET.fromstring(text)
    except ET.ParseError:
        return own, deps
    gid = root.findtext("groupId") or root.findtext("parent/groupId")
    aid = root.findtext("artifactId")
    if gid and aid:
        own.add(f"{gid}:{aid}")
    for d in root.iter("dependency"):
        g, a = d.findtext("groupId"), d.findtext("artifactId")
        if g and a and "${" not in g:
            deps.add(f"{g}:{a}")
    return own, deps


def parse_gomod(text: str):
    own, deps = set(), set()
    m = re.search(r"^module\s+(\S+)", text, re.M)
    if m:
        own.add(m.group(1))
    for line in re.findall(r"^\s*(?:require\s+)?([\w.\-]+\.[\w.\-]+/\S+)\s+v[\w.\-+]+", text, re.M):
        deps.add(line)
    return own, deps


def parse_pyproject(text: str):
    own, deps = set(), set()
    m = re.search(r"^\[project\][^\[]*?^name\s*=\s*[\"']([^\"']+)", text, re.M | re.S)
    if m:
        own.add(norm(m.group(1)))
    for block in re.findall(r"dependencies\s*=\s*\[(.*?)\]", text, re.S):
        for name in re.findall(r"[\"']([A-Za-z0-9_.\-]+)", block):
            deps.add(norm(name))
    return own, deps


def parse_bazel_gradle(text: str):
    own, deps = set(), set()
    m = re.search(r"module\(\s*name\s*=\s*\"([^\"]+)\"", text)
    if m:
        own.add(norm(m.group(1)))
    deps |= {norm(x) for x in re.findall(r"bazel_dep\(\s*name\s*=\s*\"([^\"]+)\"", text)}
    for g, a in re.findall(r"[\"']([A-Za-z][\w.\-]*\.[\w.\-]+):([\w.\-]+)(?::[^\"']*)?[\"']", text):
        deps.add(f"{g}:{a}")
    return own, deps


def parse_cmake(text: str):
    own = {norm(x) for x in re.findall(r"^\s*project\(\s*([\w\-]+)", text, re.M | re.I)}
    deps = {norm(x) for x in re.findall(r"find_package\(\s*([\w\-]+)", text, re.I)}
    deps |= {norm(x) for x in re.findall(r"FetchContent_Declare\(\s*([\w\-]+)", text, re.I)}
    return own, deps


def parse_requirements(text: str):
    deps = {
        norm(m.group(1))
        for line in text.splitlines()
        if (m := re.match(r"\s*([A-Za-z0-9_.\-]+)", line)) and not line.lstrip().startswith(("#", "-"))
    }
    return set(), deps


def parse_package_json(text: str):
    try:
        d = json.loads(text)
    except json.JSONDecodeError:
        return set(), set()
    own = {d["name"]} if isinstance(d.get("name"), str) else set()
    deps = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        deps |= set((d.get(key) or {}))
    return own, deps


def parse_cargo(text: str):
    own, deps = set(), set()
    m = re.search(r"^\[package\][^\[]*?^name\s*=\s*\"([^\"]+)\"", text, re.M | re.S)
    if m:
        own.add(norm(m.group(1)))
    for sect in re.findall(r"^\[(?:dev-|build-)?dependencies\]\s*(.*?)(?=^\[|\Z)", text, re.M | re.S):
        deps |= {norm(k) for k in re.findall(r"^([A-Za-z0-9_\-]+)\s*=", sect, re.M)}
    return own, deps


PARSERS = {
    "pom.xml": parse_pom,
    "go.mod": parse_gomod,
    "pyproject.toml": parse_pyproject,
    "package.json": parse_package_json,
    "Cargo.toml": parse_cargo,
}


def parse(path: str, text: str):
    name = path.rsplit("/", 1)[-1]
    if name in ("MODULE.bazel", "WORKSPACE") or name.endswith((".bzl", ".gradle", ".gradle.kts")):
        return parse_bazel_gradle(text)
    if name == "CMakeLists.txt":
        return parse_cmake(text)
    if name.startswith("requirements"):
        return parse_requirements(text)
    return PARSERS[name](text)


def eco(path: str, name: str) -> str:
    """Ecosystem of a manifest entry. Matches only count within one ecosystem (Rust googletest != C++ googletest)."""
    base = path.rsplit("/", 1)[-1]
    if base == "pom.xml":
        return "maven"
    if base == "go.mod":
        return "go"
    if base == "Cargo.toml":
        return "cargo"
    if base == "package.json":
        return "npm"
    if base == "pyproject.toml" or base.startswith("requirements"):
        return "pypi"
    return "maven" if ":" in name else "native"  # Bazel/Gradle/CMake


def matches(dep: str, ident: str) -> bool:
    dep, ident = ALIASES.get(dep, dep), ALIASES.get(ident, ident)
    if ":" in ident:  # maven group:artifact. match on exact artifact or the whole group
        return dep == ident or dep.split(":")[0] == ident.split(":")[0]
    if "/" in ident:  # go module path prefix
        return dep == ident or dep.startswith(ident + "/")
    return dep == ident


def derive(root: Path, repos: list[str]) -> dict:
    """Dependency edges between the given repositories (clones under `root`), with evidence."""
    own = collections.defaultdict(set)
    declared = collections.defaultdict(list)  # repo -> [(dep, file)]
    files_seen = {}
    for repo in repos:
        paths = manifests(root, repo)
        files_seen[repo] = len(paths)
        for p in paths:
            try:
                text = (root / repo / p).read_text(encoding="utf-8", errors="ignore")
                o, d = parse(p, text)
            except (OSError, KeyError):
                continue
            own[repo] |= {(eco(p, x), x) for x in o}
            declared[repo] += [((eco(p, x), x), p) for x in d]

    edges = {}
    for a in repos:
        for dep, path in declared[a]:
            for b in repos:
                if a == b:
                    continue
                if any(dep[0] == ident[0] and matches(dep[1], ident[1]) for ident in own[b]):
                    edges.setdefault((a, b), (f"{dep[0]}:{dep[1]}", path))
    result = {
        "manifest_files": files_seen,
        "identities": {r: sorted(f"{e}:{n}" for e, n in v)[:6] for r, v in own.items()},
        "edges": [
            {"from": a, "to": b, "dependency": d, "evidence": f"{a}/{p}"} for (a, b), (d, p) in sorted(edges.items())
        ],
    }
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="directory that contains the clones")
    ap.add_argument("--repos", nargs="+", default=ALL_REPOS)
    args = ap.parse_args()
    json.dump(derive(Path(args.root).resolve(), args.repos), sys.stdout, indent=2)


if __name__ == "__main__":
    main()
