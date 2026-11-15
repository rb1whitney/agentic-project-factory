# Graph Registry: Shared Per-Repo Graphs

**Read when**: people need to ask questions about a repo's structure (symbols, callers, entry points, architecture docs) without a checkout, or CI must publish a Graphify graph for each commit. The script is `.agent/skills/skill-code-map/scripts/graph_registry.py`; run it with `--help`. Reading from the store is read-only; publishing writes only under the store root.

Status: the store is a local directory. `s3://` and `gs://` URIs are rejected with an error until a bucket backend exists and is tested. No bucket was exercised.

## Signal -> Command -> Decision
| Signal | Command | Decision |
| :--- | :--- | :--- |
| A commit landed and the graph is stale | `graphify extract <repo> --code-only`, then `graph_registry.py publish --repo <name> --sha <sha> --graph <repo>/graphify-out/graph.json --repo-root <repo>` | `--code-only` is local AST: no API key, no code leaves the machine. An existing `repo/sha` snapshot is never rewritten. |
| Which repo answers this question | `graph_registry.py route "<question>" --json` | Exit 0: use the one candidate. Exit 3: show the candidates with their entry points and hubs, ask the user to narrow. Exit 4: say nothing matched, list the indexed repos, ask for a repo name or symbol. |
| Need callers, paths or impact in a repo | `graph_registry.py query --repo <name> --op query "<question>"` (also `explain`, `affected`, `path`) | Result is graph-derived. The graph holds `source_file` and `source_location`, not code: fetch the file from the git host at the printed sha with the caller's own permissions. |
| Need the graph file itself | `graph_registry.py fetch --repo <name> [--sha <sha>]` | Prints a cached local path; pass it to other `graphify --graph` commands. |

## Layout
```
graphs/<repo>/<sha>/graph.json.gz   immutable snapshot
graphs/<repo>/latest.json           sha, branch, built_at, graphify_version
catalog/<repo>.json                 entry, hubs, architecture docs, README summary, token index
```
One catalog file per repo means concurrent CI jobs never race on a shared file.

## Gotchas
- **Thresholds are uncalibrated.** `--floor 4.0` and `--ratio 1.5` come from early tests, not from the people who will ask. Recalibrate on their questions, and judge by "confidently wrong" first.
- **Routing signals, in order of strength.** A repo named in the question (including joined words such as "Google Test" or "OR-Tools") adds a large boost; a hub symbol named in it adds a smaller one; other words are scored by squared inverse document frequency, with how-to filler words (how, configure, best practices) removed. Without the name boost, one large repo (`adk-python`) outranked the right repo on most how-to questions.
- **Measured on 18 repos, 20 user-written questions (not yet a held-out test):** 11 confident and correct, 1 confident and wrong, 8 ambiguous. All 14 answerable questions and the 2 Kubernetes ones name the repo or a symbol, so this overstates name-free performance. On 20 name-free questions written by the assistant: 9 confident and correct, 2 confident and wrong, 2 ambiguous, 7 no match.
- **Questions about a repo that is not indexed** (here `kubernetes` and `filament`, whose extraction timed out) come back ambiguous or no match, never a correct answer.
- **The token index must stay complete.** Keeping only the top 400 tokens per repo produced a confidently wrong route in testing; the default is now 4,000. Catalog entries grew from about 8 KB to about 33 KB per repo.
- **Generated and minified files poison routing.** Paths like `chunk-*.js`, `*_generated*` and `third_party/` are excluded from tokens and hubs.
- **Hubs need structure.** Annotations and imported-only nodes have many incoming edges and no outgoing structure; hubs require at least two outgoing structural edges and skip tests, benchmarks and external nodes.
- **A graph is source-sensitive.** It lists every path and symbol. Give the store the same access control as the code, and never put credentials in `--store`.
- **Scores are not comparable across questions.** Only the ranking and the gap between first and second place mean anything.
- **Entry points are declared ones.** Libraries without a `main`, scripts table or `bin` field show no entry; use the hubs and README summary instead.
