#!/usr/bin/env python3
"""With/without-guide mini-eval for reference guides.

Each task in tests/evals/skill_value.yaml is answered by a headless `claude -p` run with no tools, once with the
question alone (baseline) and once with the guide text prepended (treatment). Scoring is deterministic regex
matching, so no model judges another model. Runs from a neutral working directory so repo instructions do not leak
into the baseline. Usage:
    .venv/bin/python scripts/sap/eval_skill_value.py --out <dir> [--model sonnet] [--guide pki-guide] [--n 1]
"""

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS = REPO_ROOT / "tests/evals/skill_value.yaml"

PROMPT_BASE = "Answer concisely and directly. Do not ask clarifying questions.\n\nQuestion: {q}\n"
PROMPT_GUIDE = (
    "Answer concisely and directly. Do not ask clarifying questions. A reference document is provided; "
    "use it if it is relevant and ignore it if it is not.\n\n<reference>\n{g}\n</reference>\n\nQuestion: {q}\n"
)


def score(answer: str, task: dict) -> bool:
    flags = re.IGNORECASE | re.MULTILINE
    ok_all = all(re.search(rx, answer, flags) for rx in task.get("all", []))
    ok_none = not any(re.search(rx, answer, flags) for rx in task.get("none", []))
    return ok_all and ok_none


def ask(prompt: str, model: str, cwd: Path) -> str:
    cmd = [
        "claude",
        "-p",
        "--tools",
        "",
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--no-session-persistence",
        "--model",
        model,
        prompt,
    ]
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=240, check=False)
    except subprocess.TimeoutExpired:
        return "ERROR: timeout"
    return r.stdout.strip() if r.returncode == 0 else f"ERROR: rc={r.returncode} {r.stderr.strip()[:200]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--guide", default=None)
    ap.add_argument("--n", type=int, default=1, help="samples per cell")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cwd = args.out / "cwd"
    cwd.mkdir(exist_ok=True)

    spec = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
    jobs = []
    for g in spec["guides"]:
        if args.guide and g["id"] != args.guide:
            continue
        text = (REPO_ROOT / g["path"]).read_text(encoding="utf-8")
        for t in g["tasks"]:
            for cond in ("baseline", "guide"):
                for i in range(args.n):
                    p = (PROMPT_BASE if cond == "baseline" else PROMPT_GUIDE).format(q=t["q"], g=text)
                    jobs.append((g["id"], t, cond, i, p))

    def run(job):
        gid, t, cond, i, p = job
        ans = ask(p, args.model, cwd)
        return {"guide": gid, "task": t["id"], "cond": cond, "sample": i, "pass": score(ans, t), "answer": ans}

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(run, jobs))
    (args.out / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")

    errors = [r for r in results if r["answer"].startswith("ERROR")]
    print(f"model={args.model} runs={len(results)} errors={len(errors)}")
    print(f"{'guide':<24}{'baseline':>10}{'with guide':>12}{'delta':>8}")
    for gid in sorted({r["guide"] for r in results}):
        rate = {}
        for cond in ("baseline", "guide"):
            rs = [r for r in results if r["guide"] == gid and r["cond"] == cond]
            rate[cond] = (sum(r["pass"] for r in rs), len(rs))
        d = rate["guide"][0] - rate["baseline"][0]
        print(f"{gid:<24}{rate['baseline'][0]}/{rate['baseline'][1]:>7}{rate['guide'][0]}/{rate['guide'][1]:>9}{d:>+8}")
    print("\nper-task (B=baseline pass, G=guide pass):")
    for tid in sorted({r["task"] for r in results}):
        b = [r["pass"] for r in results if r["task"] == tid and r["cond"] == "baseline"]
        g = [r["pass"] for r in results if r["task"] == tid and r["cond"] == "guide"]
        print(f"  {tid:<8} B={sum(b)}/{len(b)} G={sum(g)}/{len(g)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
