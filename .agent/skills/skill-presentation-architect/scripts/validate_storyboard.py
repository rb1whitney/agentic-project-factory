#!/usr/bin/env python3
"""Deterministic gate for presentation-architect artifacts.

Usage:
  validate_storyboard.py <storyboard.yaml>           # schemas/storyboard.md shape
  validate_storyboard.py --brief <narrative-brief.yaml>  # schemas/narrative-brief.md shape

Exit 0 = pass, 1 = defects found (listed one per line), 2 = unreadable input.
Heuristics only: a pass does not replace the human narrative review.
"""

import re
import sys
from pathlib import Path

import yaml

STATUSES = {"SOURCED", "DERIVED", "UNKNOWN", "CONFLICTED"}
STRUCTURES = {
    "sparkline", "explainer", "pitch", "hook-meat-payoff", "scqa",
    "heros-journey", "a-la-carte", "diagram-centric", "custom",
}
MAX_TITLE_WORDS = 15
MIN_TITLE_WORDS = 5
MAX_TAKEAWAYS = 3
# Verbs/linking words an assertion title usually carries; topic labels rarely do.
ASSERTION_HINT = re.compile(
    r"\b(is|are|was|were|can|cannot|does|do|did|will|would|should|must|"
    r"makes?|lets?|keeps?|costs?|cuts?|drops?|beats?|needs?|fails?|"
    r"turns?|becomes?|became|ends?|stops?|enables?|prevents?|replaces?|"
    r"scores?|gates?|compiles?|collapses?|forbids?|decides?|hides?|"
    r"shows?|proves?|removes?|avoids?|requires?|ships?|reads?)\b",
    re.IGNORECASE,
)


def _load(path: str) -> dict | list:
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        print(f"UNREADABLE | {path} | {exc}")
        sys.exit(2)


def check_storyboard(data) -> list[str]:
    defects: list[str] = []
    slides = data.get("storyboard") if isinstance(data, dict) else data
    if not isinstance(slides, list) or not slides:
        return ["storyboard | missing or empty list under 'storyboard'"]
    seen_numbers = set()
    for idx, s in enumerate(slides, 1):
        tag = f"slide {s.get('slide', idx)}"
        num = s.get("slide")
        if num in seen_numbers:
            defects.append(f"{tag} | duplicate slide number")
        seen_numbers.add(num)
        title = (s.get("title") or "").strip()
        words = len(title.split())
        if not title:
            defects.append(f"{tag} | empty title")
        else:
            if words < MIN_TITLE_WORDS:
                defects.append(f"{tag} | title is {words} words; topic label, not assertion: '{title}'")
            if words > MAX_TITLE_WORDS:
                defects.append(f"{tag} | title is {words} words; limit {MAX_TITLE_WORDS}")
            if words >= MIN_TITLE_WORDS and not ASSERTION_HINT.search(title):
                defects.append(f"{tag} | no assertion verb detected; review title: '{title}'")
        for key in ("purpose", "narrative_beat", "audience_question", "visual_thesis"):
            if not str(s.get(key) or "").strip():
                defects.append(f"{tag} | missing {key}")
        thesis = str(s.get("visual_thesis") or "")
        if re.fullmatch(r"\s*(cover|title|bullets?|two[- ]column|card grid|layout)\s*", thesis, re.I):
            defects.append(f"{tag} | visual_thesis is a layout name, not a claim about what to see")
        for ev in s.get("evidence") or []:
            status = ev.get("status") if isinstance(ev, dict) else None
            if isinstance(ev, dict) and status not in STATUSES:
                defects.append(f"{tag} | evidence status '{status}' not in {sorted(STATUSES)}")
    return defects


def check_brief(data) -> list[str]:
    defects: list[str] = []
    if not isinstance(data, dict):
        return ["brief | root must be a mapping"]
    sentence = ((data.get("big_idea") or {}).get("sentence") or "").strip()
    if not sentence:
        defects.append("big_idea.sentence | empty")
    elif len(sentence.split()) > 45:
        defects.append(f"big_idea.sentence | {len(sentence.split())} words; not speakable in one breath (limit 45)")
    for part in ("point_of_view", "stakes"):
        if not ((data.get("big_idea") or {}).get(part) or "").strip():
            defects.append(f"big_idea.{part} | empty")
    audience = data.get("audience") or {}
    if not (audience.get("persona_name") or "").strip():
        defects.append("audience.persona_name | empty (name the persona)")
    takeaways = audience.get("takeaways") or []
    if len(takeaways) > MAX_TAKEAWAYS:
        defects.append(f"audience.takeaways | {len(takeaways)} items; cap {MAX_TAKEAWAYS}")
    if not takeaways:
        defects.append("audience.takeaways | empty")
    story = data.get("story") or {}
    structure = (story.get("structure") or "").strip().lower()
    if structure not in STRUCTURES:
        defects.append(f"story.structure | '{structure}' not in {sorted(STRUCTURES)}")
    if not (story.get("rationale") or "").strip():
        defects.append("story.rationale | empty (why this structure fits)")
    if not story.get("beats"):
        defects.append("story.beats | empty")
    for ev in data.get("evidence") or []:
        status = ev.get("status")
        if status not in STATUSES:
            defects.append(f"evidence {ev.get('id', '?')} | status '{status}' invalid")
        if status == "UNKNOWN" and not re.search(r"\[.*\]", str(ev.get("claim", ""))):
            defects.append(f"evidence {ev.get('id', '?')} | UNKNOWN claim must carry a [bracketed] placeholder")
        if status == "DERIVED" and not str(ev.get("reasoning") or "").strip():
            defects.append(f"evidence {ev.get('id', '?')} | DERIVED needs visible arithmetic in 'reasoning'")
        if status == "SOURCED" and not str(ev.get("source") or "").strip():
            defects.append(f"evidence {ev.get('id', '?')} | SOURCED needs 'source'")
    if not data.get("objections"):
        defects.append("objections | empty; every recommendation needs its strongest objection")
    return defects


def main(argv: list[str]) -> int:
    brief_mode = "--brief" in argv
    args = [a for a in argv if a != "--brief"]
    if len(args) != 1:
        print(__doc__)
        return 2
    data = _load(args[0])
    defects = check_brief(data) if brief_mode else check_storyboard(data)
    kind = "brief" if brief_mode else "storyboard"
    if defects:
        print(f"FAIL | {kind} | {len(defects)} defect(s)")
        for d in defects:
            print(f"  {d}")
        return 1
    print(f"PASS | {kind} | heuristics clear (human narrative review still required)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
