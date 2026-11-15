#!/usr/bin/env python3
"""Score file-list answers against a reference set. Library plus CLI.

An answer is any text with lines `FILE: <path>`. Paths may carry a leading `./`, the absolute repository root, or an
extra leading repository folder; those are format slips, not wrong files, so they are normalised before comparing.

  python3 scripts/eval_score.py answer.txt --reference reference.json [--repo NAME] [--root DIR]
  python3 scripts/eval_score.py batch --questions questions.json --results DIR [--csv out.csv]

`batch` reads `<cond>__<repo>__q<N>__r<K>.json` files written by `claude -p --output-format json` (fields `result`,
`total_cost_usd`, `num_turns`, `duration_ms`, `usage`) and prints medians per condition and repository.
"""

import argparse
import collections
import json
import re
import statistics
import sys
from pathlib import Path

FILE_LINE = re.compile(r"FILE:\s*`?([^\s`]+)")


def parse_answer(text: str, repo: str | None = None, root: str | None = None, reference: set | None = None) -> set:
    """Extract the answered paths and normalise format slips (root prefix, './', extra repo folder)."""
    out = set()
    for raw in FILE_LINE.findall(text or ""):
        path = raw.strip()
        if root:
            path = path.removeprefix(str(root).rstrip("/") + "/")
        path = path.removeprefix("./")
        if repo and reference is not None and path not in reference and path.removeprefix(f"{repo}/") in reference:
            path = path.removeprefix(f"{repo}/")
        out.add(path)
    return out


def prf(answer: set, reference: set) -> tuple[float, float, float]:
    """Precision, recall, F1 of an answered file set against a reference set."""
    hit = len(answer & reference)
    precision = hit / len(answer) if answer else 0.0
    recall = hit / len(reference) if reference else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def score_text(text: str, reference, repo: str | None = None, root: str | None = None) -> dict:
    ref = set(reference)
    answer = parse_answer(text, repo, root, ref)
    precision, recall, f1 = prf(answer, ref)
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "matched": sorted(answer & ref),
        "missing": sorted(ref - answer),
        "extra": sorted(answer - ref),
    }


def batch(questions: dict, results_dir: Path, root_for) -> tuple[list[dict], dict]:
    """Score every saved run. Returns (one row per run, rows grouped by (condition, repo))."""
    runs, grouped = [], collections.defaultdict(list)
    for f in sorted(results_dir.glob("*.json")):
        cond, repo, q, rep = f.stem.split("__")
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        scored = score_text(data.get("result") or "", questions[repo][int(q[1:])]["reference"], repo, root_for(repo))
        usage = data.get("usage") or {}
        row = {
            "condition": cond,
            "repo": repo,
            "question": q,
            "rep": rep.lstrip("r"),
            "cost": data.get("total_cost_usd") or 0,
            "turns": data.get("num_turns") or 0,
            "seconds": (data.get("duration_ms") or 0) / 1000,
            "input_tokens": sum(
                usage.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
            ),
            "output_tokens": usage.get("output_tokens", 0),
            "precision": scored["precision"],
            "recall": scored["recall"],
            "f1": scored["f1"],
            "error": bool(data.get("is_error")),
            "denials": len(data.get("permission_denials") or []),
        }
        runs.append(row)
        grouped[(cond, repo)].append(row)
    return runs, grouped


def print_table(grouped: dict) -> None:
    print(
        f"{'cond':4} {'repo':8} {'n':>2} {'denied':>6} {'cost$':>7} {'turns':>5} {'in-tok':>8} "
        f"{'prec':>5} {'rec':>5} {'F1 med (min-max)':>18}"
    )
    for (cond, repo), rows in sorted(grouped.items()):

        def med(key, rows=rows):
            return statistics.median(r[key] for r in rows)

        f1 = [r["f1"] for r in rows]
        denied = sum(1 for r in rows if r["denials"])
        print(
            f"{cond:4} {repo:8} {len(rows):>2} {denied:>6} {med('cost'):>7.3f} {med('turns'):>5.0f} "
            f"{med('input_tokens'):>8.0f} {med('precision'):>5.2f} {med('recall'):>5.2f} "
            f"{statistics.median(f1):>7.2f} ({min(f1):.2f}-{max(f1):.2f})"
        )


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        ap = argparse.ArgumentParser(prog="eval_score.py batch")
        ap.add_argument("--questions", required=True)
        ap.add_argument("--results", required=True)
        ap.add_argument("--clones", default=None, help="directory holding the clones; strips absolute-root prefixes")
        ap.add_argument("--csv", default=None)
        a = ap.parse_args(sys.argv[2:])
        runs, grouped = batch(
            json.loads(Path(a.questions).read_text()),
            Path(a.results),
            lambda repo: str(Path(a.clones) / repo) if a.clones else None,
        )
        if a.csv:
            cols = list(runs[0]) if runs else []
            Path(a.csv).write_text(
                "\n".join([",".join(cols)] + [",".join(str(r[c]) for c in cols) for r in runs]) + "\n"
            )
        print_table(grouped)
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("answer", help="text file with FILE: lines, or - for stdin")
    ap.add_argument("--reference", required=True, help="JSON list of reference paths")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--root", default=None)
    a = ap.parse_args()
    text = sys.stdin.read() if a.answer == "-" else Path(a.answer).read_text()
    json.dump(score_text(text, json.loads(Path(a.reference).read_text()), a.repo, a.root), sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
