# Graph or Search: What the Measurements Say

**Read when**: choosing between a graph query and plain search for a code question, wiring an agent to a graph tool, indexing several repositories, or reporting a graph's benefit. Evidence: [FINDINGS.md](https://github.com/rb1whitney/ast-context-map/blob/main/research/graph-of-graphs/FINDINGS.md) (about 80 real model runs of one small model over 20 public repositories). Samples are small; read the numbers as direction.

## Signal -> Command -> Decision
| Signal | Command | Decision |
| :--- | :--- | :--- |
| A named symbol and "who uses it" | `git grep -w <Name>` | Search first. In trials plain search cost less and matched or beat the graph on recall; a capped graph answer names at most about 40 percent of the files that mention a symbol. |
| Relations search cannot show (inherits, injects, a call chain) | `semantic_query.py trace-dependencies <Name>` or `impact <Name>`, then read the files it names | Use the graph to find candidates, then read the files before answering. Agents that answered from graph output alone and read no source found 0.46 of the right files against 0.75 for search. |
| A flow over several hops (blast radius, "how does X work end to end") | `auto_context.py "<task naming the class>" --src <dir> --top 40`, then read | About 40 percent fewer input tokens than search, but less complete on its own. Verify by reading. |
| Which of many repositories | `graph_of_graphs.py overview`, then `drill` | Use the index, not raw graphs: seven repositories (164,385 symbols) became a 138 KB index, and one repository's whole `code_map.md` was 3.1 MB. |
| How repositories depend on each other | `manifest_deps.py --root <clones> --repos <names>` | Use declared manifest dependencies. Never link graphs by shared node id: merging nine graphs gave 0 direct cross-repo edges and bridges that were standard-library names. |
| Claiming a graph helps | `eval_score.py` against an independent reference (git grep, manifests, import closure) | Report precision, recall, cost and turns. Check the denied-calls count and whether the graph was used at all. |

## Rules for wiring an agent
- Cap every graph answer and end it with the next command (`--limit`, "K more").
- Allow-rules match the start of a command. Tell the agent to run one command per call (no `cd`, variables, pipes or loops), or its calls are refused. Count denied calls per run.
- A soft prompt line ("use it first; verify with search when unsure") was enough: the graph was the first call in 18 of 18 runs, and a stronger prompt changed nothing. Log tool calls to see real use.
- Tell the agent to read the files the graph names. In the trial, agents made 20 to 40 one-hop queries and opened no file.

## Gotchas
- Graph coverage plateaus: on three of four repositories about 0.4 of the files that mention a symbol.
- Merged graphs and whole-repository maps are too large for context. Measure the size before handing one over.
- Results are from one small model, three repeats per cell and approximate references. The tool shape tested (one-hop, symbol-level) drove them; a file-level closure tool is untested.
- Token figures from simulation are characters divided by 4; the trials report API cost.
