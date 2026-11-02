import java.util.*;

/** Restaurant menu tree traversal drills (levels 2, 3, 4, 6, 9, 10) with self-checking tests.
 *  Run: javac -d /tmp/menu docs/interview-drills/MenuTree.java && java -cp /tmp/menu MenuTree */
public class MenuTree {
    static class Node {
        int minSel = 0; Integer maxSel = null;                      // groups only
        Node sel(int min, Integer max) { this.minSel = min; this.maxSel = max; return this; }
        final String id, name, kind; final long price; final boolean available; final List<Node> children;
        Node(String id, String name, String kind, long price, boolean available, Node... kids) {
            this.id = id; this.name = name; this.kind = kind; this.price = price; this.available = available;
            this.children = new ArrayList<>(Arrays.asList(kids));
        }
    }

    // L2: path to a node (DFS + backtracking on a shared mutable path)
    static List<String> findPath(Node root, String id) {
        Deque<String> path = new ArrayDeque<>();
        return dfs(root, id, path) ? new ArrayList<>(path) : null;
    }
    private static boolean dfs(Node cur, String id, Deque<String> path) {
        path.addLast(cur.name);
        if (cur.id.equals(id)) return true;
        for (Node ch : cur.children) if (dfs(ch, id, path)) return true;
        path.removeLast();                                          // backtrack
        return false;
    }

    // L3: iterative DFS, left-to-right
    static List<String> itemsUnder(Node root) {
        List<String> out = new ArrayList<>();
        Deque<Node> stack = new ArrayDeque<>();
        stack.push(root);
        while (!stack.isEmpty()) {
            Node cur = stack.pop();
            if (cur.kind.equals("item")) out.add(cur.name);
            for (int i = cur.children.size() - 1; i >= 0; i--) stack.push(cur.children.get(i));
        }
        return out;
    }

    // L4: level order, one level per outer pass
    static List<List<String>> levelOrder(Node root) {
        List<List<String>> levels = new ArrayList<>();
        Deque<Node> q = new ArrayDeque<>();
        q.add(root);
        while (!q.isEmpty()) {
            List<String> level = new ArrayList<>();
            for (int size = q.size(); size > 0; size--) {            // snapshot size
                Node cur = q.poll();
                level.add(cur.name);
                q.addAll(cur.children);
            }
            levels.add(level);
        }
        return levels;
    }

    // L6: new tree without unavailable items; empty categories dropped; input untouched
    static Node prune(Node node) {
        List<Node> kept = new ArrayList<>();
        for (Node c : node.children) { Node p = prune(c); if (p != null) kept.add(p); }
        if (node.kind.equals("item") && !node.available) return null;
        boolean hasItem = kept.stream().anyMatch(MenuTree::hasItem);
        if (node.kind.equals("category") && !hasItem) return null;
        Node copy = new Node(node.id, node.name, node.kind, node.price, node.available, kept.toArray(new Node[0]));
        return copy.sel(node.minSel, node.maxSel);                    // keep selection rules on the copy
    }
    static boolean hasItem(Node n) { return n.kind.equals("item") || n.children.stream().anyMatch(MenuTree::hasItem); }

    // L9: price a line with NESTED modifiers (DFS): only selected options contribute
    static long linePrice(Node item, Set<String> selected) {
        long total = item.price;
        for (Node g : item.children) {
            if (!g.kind.equals("group")) continue;
            for (Node opt : g.children) if (selected.contains(opt.id)) total += linePrice(opt, selected);
        }
        return total;
    }

    // L10: validate selection rules recursively, including selections that do not apply
    static List<String> validate(Node item, Set<String> selected) {
        List<String> errors = new ArrayList<>();
        Set<String> reachable = new HashSet<>();
        check(item, selected, errors, reachable);
        for (String id : new TreeSet<>(selected)) if (!reachable.contains(id)) errors.add("unknown or inapplicable option: " + id);
        return errors;
    }
    private static void check(Node owner, Set<String> selected, List<String> errors, Set<String> reachable) {
        for (Node g : owner.children) {
            if (!g.kind.equals("group")) continue;
            int count = 0;
            for (Node opt : g.children) {
                if (!selected.contains(opt.id)) continue;
                count++; reachable.add(opt.id);
                check(opt, selected, errors, reachable);            // groups under a selected option become active
            }
            if (count < g.minSel) errors.add(g.name + ": pick at least " + g.minSel + " (got " + count + ")");
            if (g.maxSel != null && count > g.maxSel) errors.add(g.name + ": pick at most " + g.maxSel + " (got " + count + ")");
        }
    }

    static Node sample() {
        return new Node("m", "Dinner", "menu", 0, true,
            new Node("c1", "Starters", "category", 0, true,
                new Node("i1", "Soup", "item", 600, true),
                new Node("i2", "Wings", "item", 1100, true,
                    new Node("g1", "Sauce", "group", 0, true,
                        new Node("o1", "Buffalo", "option", 0, true),
                        new Node("o2", "BBQ", "option", 0, true)))),
            new Node("c2", "Mains", "category", 0, true,
                new Node("i3", "Burger", "item", 1500, true),
                new Node("c3", "Pasta", "category", 0, true,
                    new Node("i4", "Penne", "item", 1400, true),
                    new Node("i5", "Gnocchi", "item", 1600, false))),
            new Node("c4", "Drinks", "category", 0, true, new Node("i6", "Cola", "item", 300, false)));
    }

    static int fails = 0;
    static void eq(Object got, Object want, String name) {
        boolean ok = Objects.equals(got, want);
        if (!ok) fails++;
        System.out.println((ok ? "ok   " : "FAIL ") + name + (ok ? "" : "  got=" + got + " want=" + want));
    }
    public static void main(String[] a) {
        Node m = sample();
        eq(findPath(m, "o2"), List.of("Dinner", "Starters", "Wings", "Sauce", "BBQ"), "L2 path");
        eq(findPath(m, "zzz"), null, "L2 missing");
        eq(itemsUnder(m), List.of("Soup", "Wings", "Burger", "Penne", "Gnocchi", "Cola"), "L3 items");
        eq(levelOrder(m).get(1), List.of("Starters", "Mains", "Drinks"), "L4 level 1");
        Node p = prune(m);
        eq(itemsUnder(p), List.of("Soup", "Wings", "Burger", "Penne"), "L6 pruned items");
        eq(p.children.size(), 2, "L6 Drinks dropped");
        eq(m.children.size(), 3, "L6 original untouched");

        Node type = new Node("gt", "Type", "group", 0, true, new Node("ot1", "Cheddar", "option", 0, true), new Node("ot2", "Swiss", "option", 50, true)).sel(1, 1);
        Node extras = new Node("g2", "Extras", "group", 0, true, new Node("o3", "Bacon", "option", 200, true),
            new Node("o4", "Avocado", "option", 150, true), new Node("o5", "Cheese", "option", 100, true, type)).sel(0, 3);
        Node burger = new Node("i3", "Burger", "item", 1500, true, extras);
        Node sauce = new Node("g1", "Sauce", "group", 0, true, new Node("o1", "Buffalo", "option", 0, true), new Node("o2", "BBQ", "option", 0, true)).sel(1, 1);
        Node wings = new Node("i2", "Wings", "item", 1100, true, sauce);
        eq(linePrice(burger, Set.of("o3", "o4")), 1850L, "L9 two extras");
        eq(linePrice(burger, Set.of("o5", "ot2")), 1650L, "L9 nested modifier");
        eq(linePrice(burger, Set.of("ot2")), 1500L, "L9 orphan nested ignored");
        eq(validate(wings, Set.of()), List.of("Sauce: pick at least 1 (got 0)"), "L10 required missing");
        eq(validate(wings, Set.of("o1", "o2")), List.of("Sauce: pick at most 1 (got 2)"), "L10 too many");
        eq(validate(burger, Set.of("o5")), List.of("Type: pick at least 1 (got 0)"), "L10 nested required");
        eq(validate(burger, Set.of("ot2")), List.of("unknown or inapplicable option: ot2"), "L10 orphan");
        System.out.println(fails == 0 ? "ALL PASS" : fails + " FAILED");
        if (fails != 0) System.exit(1);
    }
}
