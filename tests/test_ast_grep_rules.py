#!/usr/bin/env python3
"""Characterization tests for skill-code-map ast-grep rules (Go, Python, Vault) via local_extract.py."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import local_extract as le  # noqa: E402

GO = """package app

import (
	"net/http"
	"os/exec"

	"github.com/spf13/cobra"
)

func NewJobController(c Client) *JobController { return nil }
func NewHelper(c Client) *Helper { return nil }

func run() {
	f := informers.NewSharedInformerFactory(client, 0)
	_ = f
	cmd := &cobra.Command{Use: "kubelet", Short: "x"}
	_ = cmd
	if utilfeature.DefaultFeatureGate.Enabled(features.PodLevelResources) {
	}
	_ = exec.Command("iptables", "-L")
	mux.Handle("/healthz", h)
	mux.HandleFunc("/livez", h2)
}
"""

PY = """import os
import subprocess
import hvac
import typer

app = typer.Typer()

@app.command()
def login(name: str):
    token = os.environ["VAULT_TOKEN"]
    addr = os.environ.get("VAULT_ADDR", "x")
    subprocess.run("ls", shell=True)
    subprocess.run(["ls"], check=True)
    c = hvac.Client(url=addr, verify=False)
    requests.get(addr, verify=False)

class BaseAuthStrategy: pass
class LdapAuth(BaseAuthStrategy):
    pass
class Unrelated(object):
    pass

def plain():
    pass
"""


def by_type(records):
    out = {}
    for r in records:
        out.setdefault(r["record_type"], []).append(r)
    return out


class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("ast-grep"):
            raise unittest.SkipTest("ast-grep not installed")
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        (root / "a.go").write_text(GO)
        (root / "v.py").write_text(PY)
        matches = le.run_ast_grep_scan(le.DEFAULT_CONFIG, [str(root)])
        cls.recs = by_type([le.normalize_record(m) for m in matches])

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def names(self, rtype, key="source_name"):
        return sorted(r[key] for r in self.recs.get(rtype, []))

    def test_go_controller_constructor_regex_constraint(self):
        self.assertEqual(self.names("go_controller_constructor"), ["NewJobController"])

    def test_go_informer_factory(self):
        self.assertEqual(len(self.recs["go_informer_factory"]), 1)

    def test_go_cobra_command_use(self):
        self.assertEqual(self.names("go_cobra_command"), ['"kubelet"'])

    def test_go_feature_gate(self):
        self.assertEqual(self.names("go_feature_gate_check"), ["PodLevelResources"])

    def test_go_exec_and_routes(self):
        self.assertEqual(len(self.recs["go_exec_command"]), 1)
        self.assertEqual(self.names("go_http_route", "source_name"), ['"/healthz"', '"/livez"'])

    def test_py_typer_command(self):
        self.assertEqual(self.names("python_cli_command"), ["login"])

    def test_py_env_reads(self):
        self.assertEqual(self.names("python_env_read"), ['"VAULT_ADDR"', '"VAULT_TOKEN"'])

    def test_py_subprocess_shell_only_flags_shell_true(self):
        self.assertEqual(len(self.recs["python_subprocess_shell"]), 1)

    def test_py_tls_verify_disabled(self):
        self.assertEqual(len(self.recs["python_tls_verify_disabled"]), 2)

    def test_vault_auth_strategy_only_direct_subclasses(self):
        self.assertEqual(self.names("vault_auth_strategy"), ["LdapAuth"])

    def test_vault_hvac_client(self):
        self.assertEqual(len(self.recs["vault_hvac_client"]), 1)

    def test_scope_comes_from_rule_metadata(self):
        self.assertEqual(self.recs["go_exec_command"][0]["source_scope"], "go_process_exec")
        self.assertEqual(self.recs["vault_auth_strategy"][0]["source_scope"], "vault_security")

    def test_legacy_records_unchanged(self):
        m = {
            "ruleId": "extract-vault-api-path",
            "file": "x.yaml",
            "metaVariables": {"single": {"PATH": {"text": "sys/health"}, "ACTION": {"text": "get"}}},
            "range": {"start": {"line": 2}},
        }
        r = le.normalize_record(m)
        self.assertEqual(
            (r["record_type"], r["source_scope"], r["source_name"]), ("vault_api_path", "vault_security", "sys/health")
        )

    def test_relational_arch_and_taint_rules(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "BadController.java").write_text(
                '@RestController("orders")\n'
                "public class BadController {\n"
                "    private final OrderRepository orderRepository;\n"
                "}\n"
            )
            (root / "GoodController.java").write_text(
                "@RestController\npublic class GoodController {\n    private OrderService orderService;\n}\n"
            )
            (root / "sql.go").write_text(
                "package main\n"
                'import "fmt"\n'
                "func (s *Store) queryUser(name string) {\n"
                "    s.db.Query(fmt.Sprintf(\"SELECT * FROM users WHERE name='%s'\", name))\n"
                "}\n"
            )
            (root / "eval_taint.py").write_text("async def bad_run(user_input):\n    return eval(user_input)\n")
            matches = le.run_ast_grep_scan(le.DEFAULT_CONFIG, [str(root)])
            recs = by_type([le.normalize_record(m) for m in matches])
            self.assertEqual([r["source_name"] for r in recs.get("architecture_violation", [])], ["orderRepository"])
            self.assertEqual(len(recs.get("go_sql_concat_taint", [])), 1)
            self.assertEqual(len(recs.get("python_dynamic_exec_taint", [])), 1)

    def test_well_architected_six_pillar_audit(self):
        import well_architected_audit as waa

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "OrderController.java").write_text(
                "@RestController\n"
                "public class OrderController {\n"
                "    private OrderRepository orderRepo;\n"
                "    public void processAll(java.util.List<String> ids) {\n"
                '        System.out.println("processing");\n'
                "        for (String id : ids) {\n"
                "            orderRepo.findById(id);\n"
                "        }\n"
                "    }\n"
                "}\n"
            )
            (root / "worker.go").write_text(
                "package main\n"
                "import (\n"
                '    "fmt"\n'
                '    "net/http"\n'
                '    "os"\n'
                ")\n"
                "func fetchAll(urls []string, db *DB) {\n"
                "    for _, u := range urls {\n"
                "        f, _ := os.Open(u)\n"
                "        defer f.Close()\n"
                "        func() {\n"
                "            f2, _ := os.Open(u)\n"
                "            defer f2.Close()\n"
                "        }()\n"
                "        http.Get(u)\n"
                "        db.Query(fmt.Sprintf(\"SELECT * FROM t WHERE u='%s'\", u))\n"
                "    }\n"
                "}\n"
            )
            (root / "service.py").write_text(
                "import requests\n"
                "def sync_items(urls):\n"
                "    try:\n"
                "        res = [requests.get(u, verify=False) for u in urls]\n"
                "    except:\n"
                "        pass\n"
            )
            report = waa.audit_directory(str(root))
            pillars = report["pillars"]
            self.assertEqual(set(pillars.keys()), {"SEC", "REL", "OPS", "PERF", "COST", "SUS"})
            self.assertGreaterEqual(len(pillars["SEC"]["findings"]), 2)
            self.assertGreaterEqual(len(pillars["REL"]["findings"]), 2)
            self.assertGreaterEqual(len(pillars["OPS"]["findings"]), 1)
            self.assertGreaterEqual(len(pillars["PERF"]["findings"]), 3)
            # Closure-scoped defer inside func() { defer f2.Close() }() must NOT be flagged (only 1 defer finding)
            go_defer_findings = [f for f in pillars["PERF"]["findings"] if f["rule"] == "wa_go_defer_in_loop"]
            self.assertEqual(len(go_defer_findings), 1)

            md = waa.render_well_architected_markdown(report)
            self.assertIn("# Well-Architected Code Review (Python / Java / Go)", md)
            self.assertIn("wa_java_repo_in_loop", md)
            self.assertIn("wa_go_defer_in_loop", md)
            self.assertIn("wa_py_http_in_loop", md)

    def test_kodus_markdown_policies_and_diff_scoped_audit(self):
        import well_architected_audit as waa

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pol_dir = root / "policies"
            pol_dir.mkdir()
            (pol_dir / "no- hardcoded-sleep.md").write_text(
                "---\n"
                "id: policy-py-no-time-sleep\n"
                "pillar: PERF\n"
                "severity: MEDIUM\n"
                "language: python\n"
                'fix: "Use asyncio.sleep() or event-driven timers instead of blocking time.sleep()."\n'
                "rule:\n"
                "  pattern: time.sleep($SECS)\n"
                "---\n"
                "# Avoid Blocking time.sleep in Service Handlers\n"
                "Blocking `time.sleep()` stalls worker threads under load.\n"
            )
            (root / "changed_handler.py").write_text("import time\ndef handle_request():\n    time.sleep(5)\n")
            (root / "untouched_legacy.py").write_text(
                "def legacy_fn(x):\n    try:\n        return eval(x)\n    except:\n        pass\n"
            )
            sample_diff = (
                "--- a/changed_handler.py\n"
                "+++ b/changed_handler.py\n"
                "@@ -1,2 +1,3 @@\n"
                " import time\n"
                " def handle_request():\n"
                "+    time.sleep(5)\n"
            )
            diff_report = waa.audit_directory(
                str(root),
                diff_text=sample_diff,
                policies_dir=str(pol_dir),
            )
            sec_findings = diff_report["pillars"]["SEC"]["findings"]
            rel_findings = diff_report["pillars"]["REL"]["findings"]
            perf_findings = diff_report["pillars"]["PERF"]["findings"]
            # Untouched legacy.py eval() and bare except: must be excluded in diff-scoped mode
            self.assertEqual(len(sec_findings), 0)
            self.assertEqual(len(rel_findings), 0)
            # Markdown policy finding in changed_handler.py must be included
            self.assertTrue(any(f["rule"] == "policy-py-no-time-sleep" for f in perf_findings))
            self.assertIn("diff_scope", diff_report)

    def test_hydrate_policies_curated_and_semgrep_transpiler(self):
        import hydrate_policies as hp
        import well_architected_audit as waa

        loaded = waa.load_markdown_policies(str(waa.DEFAULT_POLICIES_DIR))
        by_lang = {}
        for p in loaded:
            by_lang[p["language"]] = by_lang.get(p["language"], 0) + 1
        self.assertGreaterEqual(by_lang.get("python", 0), 50)
        self.assertGreaterEqual(by_lang.get("java", 0), 50)
        self.assertGreaterEqual(by_lang.get("go", 0), 50)

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sg_dir = root / "semgrep_in"
            sg_dir.mkdir()
            (sg_dir / "custom_sg.yml").write_text(
                "rules:\n"
                "  - id: avoid-pickle-loads\n"
                "    languages: [python]\n"
                "    severity: ERROR\n"
                "    message: Avoid pickle.loads on untrusted data\n"
                "    metadata:\n"
                "      category: security\n"
                "    pattern: pickle.loads(...)\n"
                "  - id: unsupported-taint-rule\n"
                "    mode: taint\n"
                "    languages: [python]\n"
                "    severity: ERROR\n"
                "    message: Taint rule should be skipped\n"
            )
            transpiled = hp.import_semgrep_dir(str(sg_dir))
            self.assertEqual(len(transpiled), 1)
            self.assertEqual(transpiled[0]["id"], "sg-python-avoid-pickle-loads")
            self.assertEqual(transpiled[0]["pillar"], "SEC")
            self.assertEqual(transpiled[0]["rule"], {"pattern": "pickle.loads($$$ARGS)"})
            valid, quarantined = hp.validate_policies_with_ast_grep(transpiled)
            self.assertEqual(len(valid), 1)
            self.assertEqual(len(quarantined), 0)


if __name__ == "__main__":
    unittest.main()

