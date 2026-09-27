# Case Study: TRI-HARNESS ADAPTER HARDENING

This document captures what an adversarial review cycle surfaced while hardening the multi-harness capability transpiler (`.agent/adapters/`, `scripts/hydrate.py`, `bin/verify_runtime_discovery.py`). One session (Antigravity) built and "certified" the compiler across Claude Code, Antigravity, and Codex; a second session (this one) re-executed every claim against the actual repo instead of trusting the transcript. The gap between what was claimed and what was true is the real subject of this case study.

## The Mission

Replace hardcoded vendor tool identifiers in `.agent/agents/*.yaml` with an abstract capability vocabulary (`read`, `search`, `write`, `shell`, `web`, `delegate`), and compile that vocabulary into working agent definitions for three harnesses whose defaults actively disagree: Claude Code fails open (`tools_omitted: inherit_all`), Antigravity fails closed (`tools_omitted: empty`), Codex inherits the parent sandbox.

## What "Certified" Turned Out to Mean

Every round in this cycle ended with a green `bin/verify_runtime_discovery.py` run and a "SUCCESS" banner. Independently re-running the same claims turned up a real defect behind almost every one of them. None were subtle logic bugs — they were places where "the tool printed PASS" and "the thing actually works" had quietly come apart.

### 1. A verifier that only reads can't prove a compiler that writes still works
`verify_runtime_discovery.py` globs the output directories and checks that existing files parse. It never calls `hydrate.py`. When a prior session's tooling had run as `root`, entire output directories (`.codex/agents/`, `.agent/adapters/`, `.agent/scenarios/`) ended up owned by `root` — unwritable by the normal user. The verifier still reported 100% PASS, because stale root-written files still parsed fine. The compiler itself was completely broken for regeneration, and the only thing checking it couldn't see that, because it never re-ran it.

**Lesson:** a read-only certification step only proves the last successful write was well-formed. If "still functions" is the actual claim, the check has to exercise the write path, not just inspect its output.

### 2. Self-referential hallucinations survive their own purge
An earlier pass "fixed" a hallucinated Claude Code field (`permissionMode: plan-first` → `plan`) in `scripts/hydrate.py`. `.agent/adapters/SYSTEM_PROMPT.md` — the document defining the adapter's own contract — still said `plan-first` two rounds later. The code was re-verified; the doc that specifies the code was not.

**Lesson:** when a hallucination is fixed in one place, grep for every other place it was asserted (docs, comments, banners) before declaring it purged.

### 3. Orphaned build output inflates its own count silently
`db-migration.yaml`'s internal `name:` field (`db-migration-agent`) didn't match its filename (`db-migration.yaml`). The compiler wrote output keyed by `name`, so a stale pre-rename artifact (`db-migration.md`/`.json`) sat untouched in four separate output directories across two hardening passes. Both "SUCCESS" runs printed a Claude/Antigravity agent count of 17 against a 16-file canonical vault, and neither the tool nor the humans reading its output caught the mismatch until it was checked by hand.

**Lesson:** a compiler that only ever adds files needs an explicit prune step, and a verifier needs to reconcile its count against the canonical source count — not just assert internal self-consistency.

### 4. A traceability banner is a claim, and it can be wrong
The "Do not edit, GENERATED from X" banner was built from the agent's `name:` field, not its actual source path. For the one agent where those diverged, the banner pointed at a file that didn't exist. The one line whose entire purpose is preventing a human from hand-editing the wrong thing was, for at least one file, actively misleading about which file that was.

**Lesson:** a generated provenance comment must be built from the actual source path captured at parse time, never re-derived from a field that can legitimately differ from the filename.

### 5. Conventions don't transfer silently between harnesses
`.agent/settings.json`'s `PreToolUse` hook called a script using `$CLAUDE_TOOL_NAME`/`$CLAUDE_TOOL_INPUT` env vars and matched tool names (`run_shell_command`, `replace`) that don't exist in Claude Code. Both were carried over from a different harness's hook convention. Claude Code hooks receive JSON on **stdin** (`tool_name`, `tool_input`), not env vars — so even after the missing script was written, the original invocation would never have worked. The referenced script (`enforce-safety.sh`) had also simply never been created; it doesn't appear anywhere in git history.

**Lesson:** a tool name, an env var, or an invocation convention that's correct for one harness is not evidence it's correct for another. Verify each harness's actual contract independently — don't assume shared vocabulary.

### 6. Twin outputs for one harness can silently disagree
Antigravity gets two generated files per agent (`.agents/{name}.json` and `.agents/agents/{name}.md`). The JSON carried `commandExecutionPolicy: sandbox` and `auto_approve`; the markdown twin, generated by the same function for the same agent, carried neither — for every agent, including write/shell-capable orchestrators. Two rounds of review inspected only the JSON sample and never noticed its twin was missing the security-relevant fields entirely.

**Lesson:** when a harness accepts more than one manifest format for the same entity, treat field parity between them as a thing to test, not assume.

## Key Outcomes

- Every fix claimed in this cycle was independently re-executed (piped test input, `jq -e` schema checks, live tool calls) rather than accepted from the transcript. Several early "100% passing / exit 0" claims did not survive that check on first re-verification; all were eventually made true, but only after the gap was named and reproduced.
- `.agent/scenarios/test_parser_edge_cases.py` and `test_adapter_invariants.py` now pin four of the six defects above as regression tests, folded into `verify_runtime_discovery.py`'s exit code.
- The remaining two (read-only verifier can't prove the write path; hook-contract cross-harness bleed) have no regression test yet — they were fixed by hand, not pinned. Worth closing before the next hardening pass.

## The Meta-Lesson

Adversarial review only has value if the claims get re-executed, not re-read. A confident, well-formatted "SUCCESS: 100% certified" report and an actually-working system are two different things that happen to look identical in a transcript. The only way to tell them apart is to run the thing yourself.
