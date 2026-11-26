# Graph or Search: What the Measurements Say

**Read when**: choosing between a graph query and plain search for a code question, wiring an agent to a graph tool, indexing several repositories, or reporting a graph's benefit. Evidence: [FINDINGS.md](https://github.com/rb1whitney/ast-context-map/blob/main/research/graph-of-graphs/FINDINGS.md) (about 330 real model runs over 20 public repositories: 233 Claude Code runs on Haiku and 109 Antigravity runs). Samples are small; read the numbers as direction.

## Signal -> Command -> Decision
| Signal | Command | Decision |
| :--- | :--- | :--- |
| A named symbol and "who uses it" | `git grep -w <Name>` | Search first. In trials plain search cost less and matched or beat the graph on recall; a capped graph answer names at most about 40 percent of the files that mention a symbol. |
| Relations search cannot show (inherits, injects, a call chain) | `semantic_query.py trace-dependencies <Name>` or `impact <Name>`, then read the files it names | Use the graph to find candidates, then read the files before answering. Agents that answered from graph output alone and read no source found 0.46 of the right files against 0.75 for search. |
| A flow over several hops (blast radius, "how does X work end to end") | `auto_context.py "<task naming the class>" --src <dir> --top 40`, then read | About 40 percent fewer input tokens than search, but less complete on its own. Verify by reading. |
| Which of many repositories | `graph_of_graphs.py overview`, then `drill` | Use the index, not raw graphs: seven repositories (164,385 symbols) became a 138 KB index, and one repository's whole `code_map.md` was 3.1 MB. |
| How repositories depend on each other | `manifest_deps.py --root <clones> --repos <names>` | Use declared manifest dependencies. Never link graphs by shared node id: merging nine graphs gave 0 direct cross-repo edges and bridges that were standard-library names. |
| Claiming a graph helps | `eval_score.py` against an independent reference (git grep, manifests, import closure) | Report precision, recall, cost and turns. Check the denied-calls count and whether the graph was used at all. |

## Routing policy (Findings 19 and 20)
1. **Grep first.** One `git grep -l` / Grep for the name. On Go import questions at kubernetes scale (up to 587 matching files) it returned the answer exactly, and plain search matched an exact graph on accuracy (F1 1.00 in every condition).
2. **Map when the search is noisy or the question is a relation.** The map is a filter and a guide, not the answer. Measured: naming the map cut Claude's median cost on noisy questions by 28 percent ($0.0095 against $0.0132). On Antigravity it first raised tokens by 43 percent (111,339 against 77,959) because the footer told agents to re-search; with the exact footer the map cost 0.44 and the noise gate 0.65 of plain search (33,909 and 50,398 against 77,042).
3. **Then search or read inside the files the map names.**
4. **Make the map say how far to trust it.** Agents re-searched the whole repository after receiving a complete answer, because the footer told them to ("Verify before changing shared code: git grep"). Mean searches rose from 1.6 to 5.0 on Antigravity, and fell to 0.25 once the footer said the list was complete (a before and after comparison; Claude Code was not rerun). `find-usages` now says "complete for those files" on Go package imports; every other list keeps the generic footer, and `closure` verifies in the right direction (reading what the entry file imports and calls).
5. **A nudge decides whether the map is used at all.** With no mention, 0 of 9 Claude runs and 0 of 9 Antigravity runs queried it. The installer's rule alone did nothing on Antigravity; only an enforcing PreToolUse hook worked. Using the map did not change recall (0.92 to 0.96 on Claude).
6. **The noise gate** (`scripts/noise_gate.py`) automates 1 to 3: silent on quiet searches (0 of 8 map uses), redirects noisy ones once. With the exact footer it cost 0.65 of search on Antigravity, but the map-only condition was cheaper (0.44), so the gate's value is that the policy lives in a hook and not in a prompt, not that it saves tokens.

Not tested: queries with thousands of raw hits, ambiguous names, questions the graph answers less exactly, and a trust footer on a repository where the list is not exact.

## Rules for wiring an agent
- Cap every graph answer and end it with the next command (`--limit`, "K more").
- Antigravity runs hook commands with the working directory `<workspace>/.agents/`, so a relative script path needs `../`, and a hook that fails blocks the tool call: wrap it so it falls back to allow.
- Allow-rules match the start of a command. Tell the agent to run one command per call (no `cd`, variables, pipes or loops), or its calls are refused. Count denied calls per run.
- A soft prompt line ("use it first; verify with search when unsure") was enough: the graph was the first call in 18 of 18 runs, and a stronger prompt changed nothing. Log tool calls to see real use.
- Tell the agent to read the files the graph names. In the trial, agents made 20 to 40 one-hop queries and opened no file.

## Gotchas
- Graph coverage plateaus: on three of four repositories about 0.4 of the files that mention a symbol.
- Merged graphs and whole-repository maps are too large for context. Measure the size before handing one over.
- Results are from one small model, three repeats per cell and approximate references. The tool shape tested (one-hop, symbol-level) drove them; a file-level closure tool is untested.
- Token figures from simulation are characters divided by 4; the trials report API cost.
