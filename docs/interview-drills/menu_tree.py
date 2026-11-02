"""Restaurant menu tree traversal drills (levels 1-11) with self-checking tests.

Run: python3 -B docs/interview-drills/menu_tree.py
"""
from collections import deque
from dataclasses import dataclass, field
from math import prod
from typing import Optional


@dataclass
class Node:
    id: str
    name: str
    kind: str                       # menu | category | item | group | option
    price: int = 0                  # cents, never floats
    available: bool = True
    children: list = field(default_factory=list)
    min_sel: int = 0                # groups only: minimum options a diner must pick
    max_sel: Optional[int] = None   # groups only: maximum (None = unlimited)


def n(id, name, kind, price=0, available=True, *children, min_sel=0, max_sel=None):
    return Node(id, name, kind, price, available, list(children), min_sel, max_sel)


def sample_menu():
    return n("m", "Dinner", "menu", 0, True,
        n("c1", "Starters", "category", 0, True,
            n("i1", "Soup", "item", 600),
            n("i2", "Wings", "item", 1100, True,
                n("g1", "Sauce", "group", 0, True,
                    n("o1", "Buffalo", "option", 0),
                    n("o2", "BBQ", "option", 0)))),
        n("c2", "Mains", "category", 0, True,
            n("i3", "Burger", "item", 1500, True,
                n("g2", "Extras", "group", 0, True,
                    n("o3", "Bacon", "option", 200),
                    n("o4", "Avocado", "option", 150))),
            n("c3", "Pasta", "category", 0, True,
                n("i4", "Penne", "item", 1400),
                n("i5", "Gnocchi", "item", 1600, False))),
        n("c4", "Drinks", "category", 0, True,
            n("i6", "Cola", "item", 300, False)))


# L1: preorder DFS, print with indentation (recursive)
def render(node, depth=0):
    out = ["  " * depth + node.name]
    for ch in node.children:
        out.extend(render(ch, depth + 1))
    return out


# L2: path from root to a node (DFS with backtracking)
def find_path(node, target_id, path=None):
    path = (path or []) + [node.name]
    if node.id == target_id:
        return path
    for ch in node.children:
        found = find_path(ch, target_id, path)
        if found:
            return found
    return None


# L3: all items under a node, ITERATIVE DFS (no recursion limit), left-to-right order
def items_under(root):
    out, stack = [], [root]
    while stack:
        cur = stack.pop()
        if cur.kind == "item":
            out.append(cur.name)
        stack.extend(reversed(cur.children))    # reversed so the first child is popped first
    return out


# L4: level order (BFS): menu shown depth by depth
def level_order(root):
    levels, q = [], deque([root])
    while q:
        level = []
        for _ in range(len(q)):                 # snapshot the size: exactly one level per pass
            cur = q.popleft()
            level.append(cur.name)
            q.extend(cur.children)
        levels.append(level)
    return levels


# L5: post-order aggregation: (min, max, item_count) of item prices for every subtree
def price_ranges(node, out=None):
    out = {} if out is None else out
    lo, hi, cnt = (node.price, node.price, 1) if node.kind == "item" else (None, None, 0)
    for ch in node.children:
        price_ranges(ch, out)
        c_lo, c_hi, c_cnt = out[ch.id]
        if c_cnt:
            lo = c_lo if lo is None else min(lo, c_lo)
            hi = c_hi if hi is None else max(hi, c_hi)
            cnt += c_cnt
    out[node.id] = (lo, hi, cnt)
    return out


# L6: return a NEW tree without unavailable items; drop categories left with no items
def prune_unavailable(node):
    kept = [p for p in (prune_unavailable(c) for c in node.children) if p is not None]
    if node.kind == "item":
        if not node.available:
            return None
        return Node(node.id, node.name, node.kind, node.price, node.available, kept, node.min_sel, node.max_sel)
    if node.kind == "category" and not any(_has_item(k) for k in kept):
        return None
    return Node(node.id, node.name, node.kind, node.price, node.available, kept, node.min_sel, node.max_sel)


def _has_item(node):
    return node.kind == "item" or any(_has_item(c) for c in node.children)


# L7: lowest common ancestor in ONE post-order pass
def lca(root, a_id, b_id):
    found = {"node": None}

    def visit(node):                            # returns how many of {a, b} are in this subtree
        hits = sum(visit(c) for c in node.children) + (node.id in (a_id, b_id))
        if hits == 2 and found["node"] is None:
            found["node"] = node                # first (deepest) node that sees both
        return hits

    visit(root)
    return found["node"]


# L8: real-world data is often a graph: shared items, accidental cycles. Validate before traversing.
def validate_menu_graph(children, root):
    problems, color, parents = [], {}, {}       # color: 1 = on current path, 2 = done
    stack = [(root, iter(children.get(root, [])))]
    color[root] = 1
    while stack:
        node, it = stack[-1]
        for ch in it:
            parents.setdefault(ch, set()).add(node)
            if color.get(ch) == 1:
                problems.append(f"cycle: {node} -> {ch}")
            elif ch not in color:
                color[ch] = 1
                stack.append((ch, iter(children.get(ch, []))))
                break
        else:
            color[node] = 2
            stack.pop()
    problems += [f"shared node {c} has {len(p)} parents" for c, p in parents.items() if len(p) > 1]
    return problems


# L9: price one order line with NESTED modifiers (DFS). Only selected options contribute,
# and only the groups under a selected option are active.
def line_price(item, selected):
    def walk(node):
        total = node.price
        for g in node.children:
            if g.kind != "group":
                continue
            for opt in g.children:
                if opt.id in selected:
                    total += walk(opt)
        return total
    return walk(item)


# L10: validate selection rules recursively ("pick 1-2 sides"), including orphan selections
def validate_selection(item, selected):
    errors, reachable = [], set()

    def check(owner):
        for g in owner.children:
            if g.kind != "group":
                continue
            picked = [o for o in g.children if o.id in selected]
            reachable.update(o.id for o in picked)
            if len(picked) < g.min_sel:
                errors.append(f"{g.name}: pick at least {g.min_sel} (got {len(picked)})")
            if g.max_sel is not None and len(picked) > g.max_sel:
                errors.append(f"{g.name}: pick at most {g.max_sel} (got {len(picked)})")
            for o in picked:
                check(o)                        # nested groups under a SELECTED option are now active

    check(item)
    errors += [f"unknown or inapplicable option: {i}" for i in sorted(set(selected) - reachable)]
    return errors


# L11: HARD. Count valid configurations of an item. A modifier group reused by many items makes the
# menu a DAG: memoize per group id, and detect cycles with an in-progress set.
def count_configurations(item, memo=None, calls=None, visiting=None):
    memo = {} if memo is None else memo
    visiting = set() if visiting is None else visiting

    def group_count(g):
        if g.id in memo:
            return memo[g.id]                   # shared group: computed once, reused by every item
        if g.id in visiting:
            raise ValueError(f"cycle at group {g.id}")
        visiting.add(g.id)
        if calls is not None:
            calls.append(g.id)
        # weight of an option = configurations of the groups nested under it
        weights = [prod(group_count(sub) for sub in o.children if sub.kind == "group") for o in g.children]
        e = [1] + [0] * len(weights)            # e[k] = ways to choose k options, weighted
        for w in weights:
            for k in range(len(weights), 0, -1):
                e[k] += e[k - 1] * w
        hi = len(weights) if g.max_sel is None else min(g.max_sel, len(weights))
        total = sum(e[k] for k in range(g.min_sel, hi + 1))
        visiting.discard(g.id)
        memo[g.id] = total
        return total

    return prod(group_count(g) for g in item.children if g.kind == "group")


def run_tests():
    fails = 0

    def eq(got, want, name):
        nonlocal fails
        ok = got == want
        fails += 0 if ok else 1
        print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  got={got!r} want={want!r}"))

    m = sample_menu()
    eq(render(m)[:4], ["Dinner", "  Starters", "    Soup", "    Wings"], "L1 render preorder")
    eq(find_path(m, "o2"), ["Dinner", "Starters", "Wings", "Sauce", "BBQ"], "L2 path to deep node")
    eq(find_path(m, "zzz"), None, "L2 path missing")
    eq(find_path(m, "m"), ["Dinner"], "L2 path to root")
    eq(items_under(m), ["Soup", "Wings", "Burger", "Penne", "Gnocchi", "Cola"], "L3 items in menu order")
    deep = n("r", "r", "menu")
    cur = deep
    for i in range(5000):
        nxt = n(f"x{i}", f"x{i}", "category")
        cur.children.append(nxt)
        cur = nxt
    cur.children.append(n("leaf", "Deep Item", "item", 1))
    eq(items_under(deep), ["Deep Item"], "L3 iterative survives depth 5000")
    try:
        render(deep)
        eq("no error", "RecursionError", "L3 recursive render at depth 5000")
    except RecursionError:
        eq(True, True, "L3 recursive render hits RecursionError at depth 5000 (why we offer iterative)")
    eq(level_order(m)[:3], [["Dinner"], ["Starters", "Mains", "Drinks"], ["Soup", "Wings", "Burger", "Pasta", "Cola"]], "L4 levels")
    eq(level_order(n("x", "Solo", "menu")), [["Solo"]], "L4 single node")
    pr = price_ranges(m)
    eq(pr["c2"], (1400, 1600, 3), "L5 Mains range+count")
    eq(pr["m"], (300, 1600, 6), "L5 whole menu")
    eq(pr["g1"], (None, None, 0), "L5 no items under group")
    p = prune_unavailable(m)
    eq(items_under(p), ["Soup", "Wings", "Burger", "Penne"], "L6 unavailable items removed")
    eq([c.name for c in p.children], ["Starters", "Mains"], "L6 empty Drinks category dropped")
    eq(len(m.children), 3, "L6 original tree not mutated")
    eq(lca(m, "o1", "o2").name, "Sauce", "L7 siblings share group")
    eq(lca(m, "o1", "i1").name, "Starters", "L7 across items")
    eq(lca(m, "o1", "o3").name, "Dinner", "L7 across categories")
    eq(lca(m, "i2", "o1").name, "Wings", "L7 one is ancestor of the other")
    eq(lca(m, "i1", "nope"), None, "L7 missing node")
    dag = {"m": ["c1", "c2"], "c1": ["i1"], "c2": ["i1", "i2"], "i2": ["c1"]}
    eq(sorted(validate_menu_graph(dag, "m")), ["shared node c1 has 2 parents", "shared node i1 has 2 parents"], "L8 DAG: shared nodes, NOT a cycle")
    cyc = {"m": ["c1", "c2"], "c1": ["i1"], "c2": ["i1", "i2"], "i1": ["c1"]}
    eq(sorted(validate_menu_graph(cyc, "m")), ["cycle: i1 -> c1", "shared node c1 has 2 parents", "shared node i1 has 2 parents"], "L8 real cycle + shared nodes")
    eq(validate_menu_graph({"m": ["a"], "a": []}, "m"), [], "L8 clean tree")

    sauce = n("g1", "Sauce", "group", 0, True, n("o1", "Buffalo", "option", 0), n("o2", "BBQ", "option", 0), min_sel=1, max_sel=1)
    cheese_type = n("gt", "Type", "group", 0, True, n("ot1", "Cheddar", "option", 0), n("ot2", "Swiss", "option", 50), min_sel=1, max_sel=1)
    extras = n("g2", "Extras", "group", 0, True,
               n("o3", "Bacon", "option", 200), n("o4", "Avocado", "option", 150),
               n("o5", "Cheese", "option", 100, True, cheese_type), min_sel=0, max_sel=3)
    wings = n("i2", "Wings", "item", 1100, True, sauce)
    burger = n("i3", "Burger", "item", 1500, True, extras)
    eq(line_price(wings, {"o1"}), 1100, "L9 price: base + zero-cost option")
    eq(line_price(burger, {"o3", "o4"}), 1850, "L9 price: two extras")
    eq(line_price(burger, {"o5", "ot2"}), 1650, "L9 price: nested modifier (cheese + swiss)")
    eq(line_price(burger, {"ot2"}), 1500, "L9 price: nested option ignored when parent not selected")
    eq(validate_selection(wings, set()), ["Sauce: pick at least 1 (got 0)"], "L10 required group missing")
    eq(validate_selection(wings, {"o1", "o2"}), ["Sauce: pick at most 1 (got 2)"], "L10 too many")
    eq(validate_selection(wings, {"o2"}), [], "L10 valid")
    eq(validate_selection(burger, set()), [], "L10 optional group empty is valid")
    eq(validate_selection(burger, {"o5"}), ["Type: pick at least 1 (got 0)"], "L10 nested required group activated by selection")
    eq(validate_selection(burger, {"ot2"}), ["unknown or inapplicable option: ot2"], "L10 orphan nested selection")
    eq(validate_selection(burger, {"zzz"}), ["unknown or inapplicable option: zzz"], "L10 unknown id")
    eq(count_configurations(wings), 2, "L11 count: required pick-1 of 2")
    eq(count_configurations(burger), 12, "L11 count: 1 + 4 + 5 + 2 with nested weight")
    shared = n("gs", "Sides", "group", 0, True, n("s1", "Fries", "option", 0), n("s2", "Salad", "option", 0), n("s3", "Rice", "option", 0), min_sel=1, max_sel=2)
    a, b, c = (n(f"k{i}", f"Combo{i}", "item", 1000, True, shared) for i in range(3))
    memo, calls = {}, []
    eq([count_configurations(x, memo, calls) for x in (a, b, c)], [6, 6, 6], "L11 shared group (DAG) counts 3+3")
    eq(calls, ["gs"], "L11 shared group computed ONCE across three items")
    loop_group = n("gl", "Loop", "group", 0, True, n("ol", "Again", "option", 0), min_sel=0, max_sel=1)
    loop_group.children[0].children.append(loop_group)          # option contains its own group: cycle
    try:
        count_configurations(n("il", "Loopy", "item", 1, True, loop_group))
        eq("no error", "ValueError", "L11 cycle detected")
    except ValueError as e:
        eq(str(e), "cycle at group gl", "L11 cycle detected")

    print("ALL PASS" if fails == 0 else f"{fails} FAILED")
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if run_tests() else 0)
