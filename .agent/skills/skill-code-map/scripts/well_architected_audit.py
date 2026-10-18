#!/usr/bin/env python3
"""
well_architected_audit.py - 6-Pillar Well-Architected Code Auditor for Python, Java, and Go.

Mirrors the AWS Well-Architected Agent architecture at the source-code level by combining:
1. Engine 1: Deterministic relational ast-grep rule packs (Security, Reliability, Performance, Operations).
2. Engine 2: Topological AST call/import graph analysis (Tarjan SCC circular dependencies, God nodes,
   untested high-in-degree SPOF hubs, cross-community coupling, and N+1 loop cost multipliers).
3. Engine 3: 6-Pillar Scorecard + concrete remediation recipes (JSON + WELL_ARCHITECTED_REPORT.md).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import graph_builder as gb  # noqa: E402
import local_extract as le  # noqa: E402

PILLAR_NAMES: Dict[str, str] = {
    "SEC": "Security",
    "REL": "Reliability",
    "OPS": "Operational Excellence",
    "PERF": "Performance Efficiency",
    "COST": "Cost Optimization",
    "SUS": "Sustainability & Maintainability",
}

RULE_TO_PILLAR_AND_FIX: Dict[str, Dict[str, str]] = {
    "architecture_violation": {
        "pillar": "SEC",
        "severity": "HIGH",
        "problem": (
            "Spring @Controller/@RestController injects *Repository directly, "
            "bypassing service-layer transaction and authorization boundaries."
        ),
        "fix": "Inject a @Service domain facade instead of accessing the *Repository directly in the controller.",
    },
    "go_sql_concat_taint": {
        "pillar": "SEC",
        "severity": "CRITICAL",
        "problem": "SQL query built via fmt.Sprintf string interpolation inside db.Query/db.Exec (SQL injection sink).",
        "fix": "Use parameterized placeholders ($1 / ?) with bound arguments in db.QueryContext / db.ExecContext.",
    },
    "python_dynamic_exec_taint": {
        "pillar": "SEC",
        "severity": "CRITICAL",
        "problem": "Dynamic code execution via eval()/exec() inside function scope.",
        "fix": "Replace eval()/exec() with ast.literal_eval() or an explicit dispatch table.",
    },
    "python_subprocess_shell": {
        "pillar": "SEC",
        "severity": "HIGH",
        "problem": "Subprocess invoked with shell=True enabling command injection.",
        "fix": "Pass an argument list (['cmd', arg]) with shell=False and check=True.",
    },
    "python_tls_verify_disabled": {
        "pillar": "SEC",
        "severity": "HIGH",
        "problem": "TLS certificate verification disabled (verify=False).",
        "fix": "Enable TLS verification (verify=True or path to CA bundle).",
    },
    "go_exec_command": {
        "pillar": "SEC",
        "severity": "MEDIUM",
        "problem": "OS process execution via os/exec.Command.",
        "fix": "Validate allowlisted arguments and use exec.CommandContext with a bounded timeout context.",
    },
    "wa_py_bare_except": {
        "pillar": "REL",
        "severity": "HIGH",
        "problem": (
            "Bare `except:` catches SystemExit/KeyboardInterrupt and masks transient "
            "failures without retry or telemetry."
        ),
        "fix": (
            "Catch specific exception types (`except ( requests.RequestException, ValueError ) as exc:`) "
            "and log/propagate."
        ),
    },
    "wa_go_http_no_timeout": {
        "pillar": "REL",
        "severity": "HIGH",
        "problem": (
            "net/http default client (`http.Get`/`http.Post`) has no request timeout "
            "and can hang goroutines indefinitely."
        ),
        "fix": "Use an explicit `&http.Client{Timeout: 10 * time.Second}` and `http.NewRequestWithContext(ctx, ...)`.",
    },
    "wa_java_sysout": {
        "pillar": "OPS",
        "severity": "MEDIUM",
        "problem": (
            "Unstructured `System.out`/`System.err` logging bypasses log levels, "
            "correlation IDs, and JSON log aggregation."
        ),
        "fix": 'Replace with parameterized SLF4J logger (`log.info("event={}", val)`).',
    },
    "wa_py_http_in_loop": {
        "pillar": "PERF",
        "severity": "HIGH",
        "problem": (
            "Synchronous HTTP request executed inside a `for`/`while` loop (N+1 network latency & egress multiplier)."
        ),
        "fix": "Batch the API request or use `asyncio.gather` / `httpx.AsyncClient` with bounded concurrency.",
    },
    "wa_java_repo_in_loop": {
        "pillar": "PERF",
        "severity": "HIGH",
        "problem": "Spring Repository query/mutation executed inside a loop (N+1 database round-trip anti-pattern).",
        "fix": (
            "Batch-fetch outside the loop using `findAllById(ids)` / `saveAll(entities)` "
            "or a `@Query` `WHERE id IN :ids`."
        ),
    },
    "wa_go_defer_in_loop": {
        "pillar": "PERF",
        "severity": "HIGH",
        "problem": (
            "`defer` inside a `for` loop retains file descriptors/locks/sockets until the enclosing function exits."
        ),
        "fix": (
            "Close the resource explicitly at the end of each loop iteration "
            "or extract the loop body into a helper function."
        ),
    },
}


DEFAULT_POLICIES_DIR = SCRIPT_DIR.parent / "resources" / "policies"


def load_markdown_policies(policies_dir: str) -> List[Dict[str, Any]]:
    """Parse Kodus-style Policy-as-Code Markdown files (single-rule or multi-rule YAML frontmatter + Markdown body)."""
    try:
        import yaml
    except ImportError:
        return []
    pdir = Path(policies_dir)
    if not pdir.is_dir():
        return []
    policies: List[Dict[str, Any]] = []
    seen_ids: set = set()
    for md_file in sorted(pdir.rglob("*.md")):
        try:
            raw = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if not raw.startswith("---"):
            continue
        parts = raw.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            front = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(front, dict):
            continue
        body_lines = [ln.strip().lstrip("#").strip() for ln in parts[2].strip().splitlines() if ln.strip()]
        default_problem = " — ".join(body_lines[:2]) if body_lines else ""

        # Support multi-rule pack frontmatter (`rules: [...]`) or single-rule frontmatter (`id` + `rule`)
        raw_entries = front.get("rules") if isinstance(front.get("rules"), list) else [front]
        pack_pillar = str(front.get("pillar", "OPS")).upper()
        pack_lang = str(front.get("language", "python"))
        pack_sev = str(front.get("severity", "MEDIUM")).upper()

        for entry in raw_entries:
            if not isinstance(entry, dict) or not entry.get("id") or not entry.get("rule"):
                continue
            rid = str(entry["id"])
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            prob = str(entry.get("problem") or entry.get("message") or default_problem or rid)
            policies.append(
                {
                    "id": rid,
                    "pillar": str(entry.get("pillar", pack_pillar)).upper(),
                    "severity": str(entry.get("severity", pack_sev)).upper(),
                    "language": str(entry.get("language", pack_lang)),
                    "fix": str(entry.get("fix", front.get("fix", "Follow architectural policy in Markdown file."))),
                    "problem": prob,
                    "rule": entry["rule"],
                    "constraints": entry.get("constraints") or front.get("constraints"),
                    "source_policy": str(md_file),
                }
            )
    return policies


def evaluate_markdown_policies(target_dir: str, policies_dir: str) -> List[Dict[str, Any]]:
    """Compile Kodus-style Markdown policies into temporary multi-doc ast-grep rules and scan target_dir."""
    import subprocess
    import tempfile

    try:
        import yaml
    except ImportError:
        return []
    policies = load_markdown_policies(policies_dir)
    if not policies:
        return []
    by_id = {p["id"]: p for p in policies}

    def _write_and_scan(active_pols: List[Dict[str, Any]], troot: Path) -> Tuple[int, str, List[Dict[str, Any]]]:
        rules_sub = troot / "rules"
        if rules_sub.exists():
            for f in rules_sub.glob("*.yml"):
                f.unlink()
        else:
            rules_sub.mkdir()
        by_lang_docs: Dict[str, List[Dict[str, Any]]] = {}
        for pol in active_pols:
            rule_doc: Dict[str, Any] = {
                "id": pol["id"],
                "language": pol["language"],
                "rule": pol["rule"],
            }
            if pol.get("constraints"):
                rule_doc["constraints"] = pol["constraints"]
            by_lang_docs.setdefault(pol["language"], []).append(rule_doc)
        for lang, docs in by_lang_docs.items():
            (rules_sub / f"{lang}.yml").write_text(yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8")
        sg_cfg = troot / "sgconfig.yml"
        sg_cfg.write_text("ruleDirs:\n  - rules\n", encoding="utf-8")
        proc = subprocess.run(
            ["ast-grep", "scan", "--config", str(sg_cfg), "--json=stream", str(target_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        parsed: List[Dict[str, Any]] = []
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return proc.returncode, (proc.stderr or ""), parsed

    with tempfile.TemporaryDirectory() as tmp:
        troot = Path(tmp)
        rc, stderr_txt, matches = _write_and_scan(policies, troot)
        if rc != 0 or "Cannot parse rule" in stderr_txt:
            import hydrate_policies as hp

            valid_pols, _ = hp.validate_policies_with_ast_grep(policies)
            if valid_pols:
                _, _, matches = _write_and_scan(valid_pols, troot)
            else:
                matches = []

    findings: List[Dict[str, Any]] = []
    for m in matches:
        rid = m.get("ruleId", "")
        pol = by_id.get(rid)
        if not pol:
            continue
        fpath = m.get("file", "")
        line_no = m.get("range", {}).get("start", {}).get("line", 0) + 1
        findings.append(
            {
                "pillar": pol["pillar"] if pol["pillar"] in PILLAR_NAMES else "OPS",
                "rule": rid,
                "severity": pol["severity"],
                "location": f"{fpath}:{line_no}",
                "path": fpath,
                "line": line_no,
                "symbol": Path(fpath).stem,
                "problem": pol["problem"],
                "fix": pol["fix"],
            }
        )
    return findings


def audit_directory(
    target_dir: str,
    diff_text: Optional[str] = None,
    policies_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Run deterministic AST rules, Markdown policies, and topological graph checks across 6 Pillars."""
    import semantic_query as sq

    root = Path(target_dir).resolve()
    pillars: Dict[str, Dict[str, Any]] = {
        k: {"name": v, "score": 100, "status": "PASS", "findings": []} for k, v in PILLAR_NAMES.items()
    }

    graph = gb.GraphBuilder(str(root)).build_graph()
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", [])

    # Optional Open Code Review style diff-scoped PR gate
    diff_scope: Optional[Dict[str, Any]] = None
    allowed_rel_files: Optional[set] = None
    if diff_text is not None:
        q = sq.SemanticQuery.from_dict(graph)
        diff_scope = q.diff_impact(diff_text)
        allowed_rel_files = {f.replace("\\", "/").lstrip("./") for f in diff_scope.get("modified_files", [])}
        for sym in diff_scope.get("modified_symbols", []) + diff_scope.get("impacted_production", []):
            sfile = nodes.get(sym, {}).get("file", "")
            if sfile:
                allowed_rel_files.add(sfile.replace("\\", "/").lstrip("./"))

    def _norm_rel(fpath: str) -> str:
        p_obj = Path(fpath)
        resolved = p_obj.resolve() if p_obj.is_absolute() else (root / p_obj).resolve()
        try:
            return str(resolved.relative_to(root)).replace("\\", "/")
        except ValueError:
            return fpath.replace("\\", "/").lstrip("./")

    def _in_diff_scope(fpath: str) -> bool:
        if allowed_rel_files is None:
            return True
        return _norm_rel(fpath) in allowed_rel_files

    # 1. Engine 1: Relational ast-grep rule scan + Kodus-style Markdown Policies
    raw_matches = le.run_ast_grep_scan(le.DEFAULT_CONFIG, [str(root)])
    rule_meta = le.load_rule_metadata(le.DEFAULT_CONFIG)
    records = [r for r in (le.normalize_record(m, rule_meta=rule_meta) for m in raw_matches) if r is not None]

    def _is_test_path(p: str) -> bool:
        low = p.replace("\\", "/").lower()
        name = Path(low).name
        return (
            "/test/" in low
            or "/tests/" in low
            or low.endswith("_test.go")
            or name.startswith("test_")
            or name.endswith("test.java")
            or name.endswith("tests.java")
        )

    seen_pillar_locs: set = set()
    for rec in records:
        rtype = rec.get("record_type", "")
        rpath = str(rec.get("path", ""))
        if not _in_diff_scope(rpath):
            continue
        if rtype == "wa_java_sysout" and _is_test_path(rpath):
            continue
        spec = RULE_TO_PILLAR_AND_FIX.get(rtype)
        if not spec:
            continue
        pillar_key = spec["pillar"]
        line_no = int(rec.get("line", 1))
        loc_key = (pillar_key, _norm_rel(rpath), line_no)
        if loc_key in seen_pillar_locs:
            continue
        seen_pillar_locs.add(loc_key)
        finding = {
            "rule": rtype,
            "severity": spec["severity"],
            "location": f"{rpath}:{line_no}",
            "symbol": rec.get("source_name", ""),
            "problem": spec["problem"],
            "fix": spec["fix"],
        }
        pillars[pillar_key]["findings"].append(finding)
        # Dual-pillar model: N+1 loop patterns get primary HIGH in PERF and secondary MEDIUM in COST
        if rtype in ("wa_py_http_in_loop", "wa_java_repo_in_loop", "wa_go_defer_in_loop"):
            cost_key = ("COST", _norm_rel(rpath), line_no)
            seen_pillar_locs.add(cost_key)
            pillars["COST"]["findings"].append(
                {
                    **finding,
                    "severity": "MEDIUM",
                    "problem": f"[Cost Multiplier] {spec['problem']}",
                }
            )

    active_pol_dir = policies_dir if policies_dir is not None else str(DEFAULT_POLICIES_DIR)
    for pf in evaluate_markdown_policies(str(root), active_pol_dir):
        if not _in_diff_scope(pf["path"]) or _is_test_path(pf["path"]):
            continue
        loc_key = (pf["pillar"], _norm_rel(pf["path"]), int(pf["line"]))
        if loc_key in seen_pillar_locs:
            continue
        seen_pillar_locs.add(loc_key)
        pillars[pf["pillar"]]["findings"].append(
            {
                "rule": pf["rule"],
                "severity": pf["severity"],
                "location": pf["location"],
                "symbol": pf["symbol"],
                "problem": pf["problem"],
                "fix": pf["fix"],
            }
        )

    # 2. Engine 2: Topological call/import graph analysis
    # 2a. Post-order Tarjan SCC circular dependencies -> Operational Excellence (OPS)
    cycles = gb.find_cycles_postorder(nodes, edges)
    for cyc in cycles:
        cfile = nodes.get(cyc[0], {}).get("file", cyc[0])
        if not _in_diff_scope(cfile):
            continue
        pillars["OPS"]["findings"].append(
            {
                "rule": "wa_topology_circular_dependency",
                "severity": "HIGH",
                "location": cfile,
                "symbol": " -> ".join(cyc),
                "problem": f"Circular dependency across {len(cyc)} symbols/modules ({', '.join(cyc)}).",
                "fix": "Break the cycle by extracting shared interfaces/DTOs into a lower-level leaf package.",
            }
        )

    # 2b. High-degree God nodes -> Operational Excellence (OPS) & Sustainability (SUS)
    in_deg: Dict[str, int] = {n: 0 for n in nodes}
    out_deg: Dict[str, int] = {n: 0 for n in nodes}
    tested_targets = set()
    for e in edges:
        u, v = str(e.get("from", "")), str(e.get("to", ""))
        out_deg[u] = out_deg.get(u, 0) + 1
        in_deg[v] = in_deg.get(v, 0) + 1
        u_file = nodes.get(u, {}).get("file", "") or u
        if _is_test_path(u_file):
            tested_targets.add(v)

    for nid, info in nodes.items():
        nfile = str(info.get("file", ""))
        if not _in_diff_scope(nfile) or _is_test_path(nfile) or nfile.endswith((".tf", ".hcl")):
            continue
        tot_deg = in_deg.get(nid, 0) + out_deg.get(nid, 0)
        if tot_deg >= 8:
            pillars["OPS"]["findings"].append(
                {
                    "rule": "wa_topology_god_node",
                    "severity": "MEDIUM",
                    "location": f"{nfile}:{info.get('line', 1)}",
                    "symbol": nid,
                    "problem": (
                        f"Architectural hub `{nid}` has degree {tot_deg} "
                        f"(in={in_deg.get(nid, 0)}, out={out_deg.get(nid, 0)})."
                    ),
                    "fix": "Decompose into smaller single-responsibility domain services.",
                }
            )
        # Untested Single-Point-of-Failure (SPOF) hub -> Reliability (REL)
        if in_deg.get(nid, 0) >= 3 and nid not in tested_targets:
            pillars["REL"]["findings"].append(
                {
                    "rule": "wa_topology_untested_spof",
                    "severity": "MEDIUM",
                    "location": f"{nfile}:{info.get('line', 1)}",
                    "symbol": nid,
                    "problem": f"Shared dependency `{nid}` has {in_deg[nid]} callers but zero direct test edges.",
                    "fix": f"Add unit/contract tests covering `{nid}` before modifying its dependents.",
                }
            )

    # 2c. Cross-community coupling ratio -> Sustainability & Maintainability (SUS)
    if edges and diff_text is None:
        comms = gb.detect_communities(nodes, edges)
        cross_edges = sum(1 for e in edges if comms.get(str(e.get("from", ""))) != comms.get(str(e.get("to", ""))))
        if len(edges) >= 6 and (cross_edges / len(edges)) > 0.6:
            pillars["SUS"]["findings"].append(
                {
                    "rule": "wa_topology_boundary_bleed",
                    "severity": "MEDIUM",
                    "location": str(root),
                    "symbol": "cross_community_edges",
                    "problem": (
                        f"{cross_edges}/{len(edges)} edges cross subsystem community boundaries (>60% coupling)."
                    ),
                    "fix": "Introduce package-private visibility and facade interfaces between domain slices.",
                }
            )

    # 3. Compute Pillar Scores & Overall Score
    severity_weights = {"CRITICAL": 25, "HIGH": 15, "MEDIUM": 8, "LOW": 3}
    for pkey, pdata in pillars.items():
        penalty = sum(severity_weights.get(f["severity"], 5) for f in pdata["findings"])
        score = max(0, 100 - penalty)
        pdata["score"] = score
        pdata["status"] = "PASS" if score >= 85 else ("WARN" if score >= 60 else "FAIL")

    overall_score = round(sum(p["score"] for p in pillars.values()) / len(pillars), 1)
    result: Dict[str, Any] = {
        "target_dir": str(root),
        "overall_score": overall_score,
        "graph_stats": {"nodes": len(nodes), "edges": len(edges), "cycles": len(cycles)},
        "pillars": pillars,
    }
    if diff_scope is not None:
        result["diff_scope"] = diff_scope
    return result


def render_well_architected_markdown(report: Dict[str, Any]) -> str:
    """Format a 6-Pillar Well-Architected report in caveman-prose Markdown (`Location | Problem | Fix`)."""
    lines = [
        "# Well-Architected Code Review (Python / Java / Go)",
        "",
        f"- **Target**: `{report['target_dir']}`",
        f"- **Overall Score**: **{report['overall_score']} / 100**",
        (
            f"- **Graph Topology**: {report['graph_stats']['nodes']} nodes, "
            f"{report['graph_stats']['edges']} edges, {report['graph_stats']['cycles']} circular SCCs"
        ),
    ]
    if "diff_scope" in report:
        ds = report["diff_scope"]
        lines.append(
            f"- **PR Diff Blast Radius**: {len(ds.get('modified_symbols', []))} modified symbols, "
            f"{len(ds.get('impacted_production', []))} impacted callers, "
            f"{len(ds.get('impacted_tests', []))} impacted tests"
        )
    lines.extend(
        [
            "",
            "## 1. Pillar Scorecard",
            "",
            "| Pillar | Score | Status | Findings |",
            "|---|---|---|---|",
        ]
    )
    for pkey in ("SEC", "REL", "OPS", "PERF", "COST", "SUS"):
        p = report["pillars"][pkey]
        lines.append(f"| **{pkey} — {p['name']}** | {p['score']}/100 | **{p['status']}** | {len(p['findings'])} |")

    lines.extend(["", "## 2. Deterministic Findings (`Location | Pillar | Rule | Problem | Fix`)", ""])
    lines.append("| Location | Pillar | Rule | Severity | Problem | Fix |")
    lines.append("|---|---|---|---|---|---|")
    any_finding = False
    for pkey in ("SEC", "REL", "OPS", "PERF", "COST", "SUS"):
        for f in report["pillars"][pkey]["findings"]:
            any_finding = True
            lines.append(
                f"| `{f['location']}` | **{pkey}** | `{f['rule']}` | {f['severity']} | {f['problem']} | {f['fix']} |"
            )
    if not any_finding:
        lines.append("| None | ALL | — | — | Zero violations detected. | — |")
    return "\n".join(lines) + "\n"


def main() -> None:
    import subprocess

    ap = argparse.ArgumentParser(description="Run 6-Pillar Well-Architected Code Audit (Python/Java/Go).")
    ap.add_argument("dir", help="Target directory to audit")
    ap.add_argument("--format", choices=("markdown", "json"), default="markdown", help="Output format")
    ap.add_argument(
        "--diff", action="store_true", help="Scope audit strictly to `git diff HEAD` and its 2-hop blast radius"
    )
    ap.add_argument("--diff-file", default=None, help="Path to unified diff file for PR-scoped audit")
    ap.add_argument("--policies", default=None, help="Directory of Kodus-style Markdown Policy-as-Code files (*.md)")
    ap.add_argument("--out", default=None, help="Optional file path to write report")
    args = ap.parse_args()

    if not Path(args.dir).is_dir():
        sys.stderr.write(f"Error: target path is not a directory: {args.dir}\n")
        sys.exit(1)
    if args.diff_file and not Path(args.diff_file).is_file():
        sys.stderr.write(f"Error: diff file does not exist: {args.diff_file}\n")
        sys.exit(1)
    if args.policies and not Path(args.policies).is_dir():
        sys.stderr.write(f"Error: policies directory does not exist: {args.policies}\n")
        sys.exit(1)

    diff_text: Optional[str] = None
    if args.diff_file:
        diff_text = Path(args.diff_file).read_text(encoding="utf-8")
    elif args.diff:
        res = subprocess.run(["git", "-C", args.dir, "diff", "HEAD"], capture_output=True, text=True)
        if res.returncode != 0:
            sys.stderr.write(f"Error running git diff in {args.dir}: {res.stderr}\n")
            sys.exit(1)
        diff_text = res.stdout

    report = audit_directory(args.dir, diff_text=diff_text, policies_dir=args.policies)
    output = json.dumps(report, indent=2) if args.format == "json" else render_well_architected_markdown(report)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
