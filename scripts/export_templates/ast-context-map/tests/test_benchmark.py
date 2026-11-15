import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "token_compare", Path(__file__).resolve().parents[1] / "benchmarks" / "token_compare.py"
)
token_compare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(token_compare)


def test_ast_output_is_smaller_than_raw_source():
    rows = token_compare.measure()
    assert len(rows) == 2
    for row in rows:
        assert row["mapped_bytes"] < row["raw_bytes"], row


def test_targeted_query_beats_whole_repo_map():
    whole, targeted = token_compare.measure()
    assert targeted["reduction_pct"] > whole["reduction_pct"]
