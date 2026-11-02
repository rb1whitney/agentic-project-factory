# Interview drills: restaurant menu tree traversal

Self-checking reference solutions. Each prints `ok` or `FAIL` per case and `ALL PASS` at the end.

| File | Levels | Run |
|---|---|---|
| `menu_tree.py` | 1-11 | `python3 -B docs/interview-drills/menu_tree.py` |
| `MenuTree.java` | 2, 3, 4, 6, 9, 10 | `javac -d /tmp/menu docs/interview-drills/MenuTree.java && java -cp /tmp/menu MenuTree` |

Levels: 1 render, 2 path, 3 items under (iterative DFS), 4 level order (BFS), 5 per-subtree price range,
6 prune unavailable into a new tree, 7 lowest common ancestor, 8 cycle and shared-node validation,
9 price with nested modifiers, 10 selection-rule validation, 11 memoized configuration count over a DAG.

Money is integer cents. Windows and ends are half-open where intervals appear.
