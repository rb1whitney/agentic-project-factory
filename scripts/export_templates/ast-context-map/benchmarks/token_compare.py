#!/usr/bin/env python3
"""Compare raw-source context with AST map / graph-query output on the bundled synthetic sample.

Sizes are bytes of text; "approx tokens" is bytes / 4, a rough proxy (not a tokenizer).
Run:  python3 benchmarks/token_compare.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "payments-java"
SCRIPTS = ROOT / "scripts"
TARGET = "PaymentRequest"


def run(*args) -> str:
    cmd = [sys.executable, *[str(a) for a in args]]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def measure() -> list[dict]:
    sources = sorted(SAMPLE.rglob("*.java"))
    texts = {p: p.read_text(encoding="utf-8") for p in sources}
    raw_all = "".join(texts.values())
    mentioning = "".join(t for t in texts.values() if TARGET in t)
    with tempfile.TemporaryDirectory() as out:
        run(SCRIPTS / "code_mapper.py", SAMPLE, "--force", "--out-dir", out)
        code_map = (Path(out) / "code_map.md").read_text(encoding="utf-8")
        impact = run(SCRIPTS / "semantic_query.py", "--graph", Path(out) / "relationship_graph.json", "impact", TARGET)
    rows = [
        ("Whole repo: raw source vs AST map (code_map.md)", raw_all, code_map),
        (f"Blast radius of {TARGET}: files mentioning it vs `impact` query", mentioning, impact),
    ]
    result = []
    for label, raw, mapped in rows:
        raw_b, map_b = len(raw.encode()), len(mapped.encode())
        result.append(
            {"label": label, "raw_bytes": raw_b, "mapped_bytes": map_b, "reduction_pct": round(100 * (1 - map_b / raw_b), 1)}
        )
    return result


def main() -> None:
    print(f"{'scenario':<72} {'raw B':>8} {'ast B':>8} {'~tok raw':>9} {'~tok ast':>9} {'saved':>7}")
    for r in measure():
        print(
            f"{r['label']:<72} {r['raw_bytes']:>8} {r['mapped_bytes']:>8} "
            f"{r['raw_bytes'] // 4:>9} {r['mapped_bytes'] // 4:>9} {r['reduction_pct']:>6}%"
        )


if __name__ == "__main__":
    main()
