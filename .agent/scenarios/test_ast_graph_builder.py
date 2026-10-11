#!/usr/bin/env python3
"""
Scenario Test: Java Semantic Graph (class-keyed, typed edges, resolved calls)
Validates bin/ast-bridge/graph_builder.py and semantic_query.py against a small
Spring-style fixture modelled on projects/cloud-boot-app.

Contract under test:
  - Nodes are keyed by "Class" and "Class.method", so same-named methods do not collide.
  - Edge types: injects, uses-type, calls (receiver-resolved only), throws, inherits.
  - Calls on unresolvable receivers (JDK, logger, third-party) emit no edge.
  - semantic_query answers class-level usages, dependencies, and transitive impact.
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BRIDGE = REPO_ROOT / "bin" / "ast-bridge"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, str(BRIDGE / f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


graph_builder = _load("graph_builder")
semantic_query = _load("semantic_query")

FIXTURE = {
    "controller/DataController.java": """
package com.x.controller;

@RestController
@RequestMapping("/api/v1/data")
public class DataController extends BaseController {
    private static final Logger log = LoggerFactory.getLogger(DataController.class);

    @Autowired
    private DataService dataService;

    @GetMapping("/{id}")
    public DataDTO getData(@PathVariable("id") Long id) throws ResourceNotFoundException {
        DataDTO data = this.dataService.getData(id);
        log.debug("got {}", data);
        checkResourceFound(data);
        return data;
    }

    @PostMapping("")
    public void createData(@RequestBody DataDTO dto) {
        dataService.createData(dto);
        RangeValidator.validate(dto);
    }

    private static <T> T checkResourceFound(T resource) throws ResourceNotFoundException {
        if (resource == null) {
            throw new ResourceNotFoundException();
        }
        return resource;
    }
}
""",
    "controller/BaseController.java": """
package com.x.controller;

public abstract class BaseController {
    public String getData() { return "base"; }
}
""",
    "service/DataService.java": """
package com.x.service;

@Service
public class DataService {
    @Autowired
    private DataRepository dataRepository;

    public DataDTO getData(long id) {
        return dataRepository.findById(id).map(this::convertToDTO).orElse(null);
    }

    public DataDTO createData(DataDTO dto) {
        Data saved = dataRepository.save(convertToEntity(dto));
        return convertToDTO(saved);
    }

    private DataDTO convertToDTO(Data data) { return new DataDTO(data.getId()); }
    private Data convertToEntity(DataDTO dto) { return new Data(dto.getId()); }
}
""",
    "repository/DataRepository.java": """
package com.x.repository;

public interface DataRepository extends JpaRepository<Data, Long> {
}
""",
    "domain/Data.java": """
package com.x.domain;

@Entity
public class Data {
    private Long id;
    public Data(Long id) { this.id = id; }
    public Long getId() { return id; }
}
""",
    "dto/DataDTO.java": """
package com.x.dto;

public class DataDTO {
    private Long id;
    public DataDTO(Long id) { this.id = id; }
    public Long getId() { return id; }
}
""",
    "exception/ResourceNotFoundException.java": """
package com.x.exception;

public class ResourceNotFoundException extends RuntimeException {
}
""",
    "validator/RangeValidator.java": """
package com.x.validator;

public class RangeValidator {
    public static void validate(DataDTO dto) { }
}
""",
}


class TestJavaSemanticGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        for rel, src in FIXTURE.items():
            path = cls.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(src, encoding="utf-8")
        cls.graph = graph_builder.GraphBuilder(str(cls.root)).build_graph()
        graph_path = cls.root / "graph.json"
        import json

        graph_path.write_text(json.dumps(cls.graph), encoding="utf-8")
        cls.query = semantic_query.SemanticQuery(str(graph_path))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def edges(self, frm=None, to=None, typ=None):
        return [
            e
            for e in self.graph["edges"]
            if (frm is None or e["from"] == frm)
            and (to is None or e["to"] == to)
            and (typ is None or e["type"] == typ)
        ]

    # --- nodes -------------------------------------------------------------

    def test_nodes_keyed_by_class_and_method(self):
        nodes = self.graph["nodes"]
        for key in ("DataController", "DataService", "DataController.getData", "DataService.getData"):
            self.assertIn(key, nodes)

    def test_same_method_name_does_not_collide(self):
        nodes = self.graph["nodes"]
        self.assertTrue(nodes["DataController.getData"]["file"].endswith("DataController.java"))
        self.assertTrue(nodes["DataService.getData"]["file"].endswith("DataService.java"))
        self.assertTrue(nodes["BaseController.getData"]["file"].endswith("BaseController.java"))

    def test_route_and_annotations_recorded(self):
        node = self.graph["nodes"]["DataController.getData"]
        self.assertEqual(node.get("route"), "GET /api/v1/data/{id}")
        self.assertIn("RestController", self.graph["nodes"]["DataController"].get("annotations", []))

    # --- edges -------------------------------------------------------------

    def test_injects_edges(self):
        self.assertTrue(self.edges("DataController", "DataService", "injects"))
        self.assertTrue(self.edges("DataService", "DataRepository", "injects"))

    def test_uses_type_edges(self):
        self.assertTrue(self.edges("DataController.getData", "DataDTO", "uses-type"))
        self.assertTrue(self.edges("DataService.createData", "Data", "uses-type"))
        self.assertTrue(self.edges("DataRepository", "Data", "uses-type"))

    def test_calls_resolved_through_field_type(self):
        self.assertTrue(self.edges("DataController.getData", "DataService.getData", "calls"))
        self.assertTrue(self.edges("DataController.createData", "DataService.createData", "calls"))

    def test_calls_resolved_for_static_and_same_class(self):
        self.assertTrue(self.edges("DataController.createData", "RangeValidator.validate", "calls"))
        self.assertTrue(self.edges("DataController.getData", "DataController.checkResourceFound", "calls"))

    def test_no_edge_to_wrong_same_named_method(self):
        wrong = self.edges("DataController.getData", "DataController.getData", "calls")
        self.assertFalse(wrong)
        self.assertFalse(self.edges("DataController.getData", "BaseController.getData", "calls"))

    def test_unresolvable_calls_emit_no_edge(self):
        node_ids = set(self.graph["nodes"])
        for edge in self.graph["edges"]:
            self.assertIn(edge["to"], node_ids, f"dangling edge target: {edge}")

    def test_throws_edges(self):
        self.assertTrue(self.edges("DataController.getData", "ResourceNotFoundException", "throws"))
        self.assertTrue(self.edges("DataController.checkResourceFound", "ResourceNotFoundException", "throws"))

    def test_throw_does_not_duplicate_as_uses_type(self):
        self.assertTrue(self.edges("DataController.checkResourceFound", "ResourceNotFoundException", "throws"))
        self.assertFalse(self.edges("DataController.checkResourceFound", "ResourceNotFoundException", "uses-type"))

    def test_inherits_edges(self):
        self.assertTrue(self.edges("DataController", "BaseController", "inherits"))
        self.assertTrue(self.edges("DataRepository", "JpaRepository", "inherits") == [])  # external, not in graph

    # --- query layer -------------------------------------------------------

    def test_find_usages_of_class(self):
        out = self.query.find_usages("DataDTO")
        self.assertIn("DataController", out)
        self.assertIn("DataService", out)

    def test_trace_dependencies_accepts_class_name(self):
        out = self.query.trace_dependencies("DataController")
        self.assertIn("DataService", out)
        self.assertIn("injects", out)

    def test_impact_is_transitive(self):
        out = self.query.impact("Data")
        for dependent in ("DataService", "DataRepository", "DataController"):
            self.assertIn(dependent, out)


class TestWalkSkipsVendorDirs(unittest.TestCase):
    """Repo-wide runs happen at session start; vendor/cache trees must never be parsed."""

    def test_skip_dirs_not_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, cls in (
                ("src/Keep.java", "Keep"),
                ("node_modules/pkg/Vendored.java", "Vendored"),
                (".venv/lib/Venv.java", "Venv"),
                (".git/hooks/Git.java", "Git"),
                ("target/Built.java", "Built"),
                ("temp_scratch/Temp.java", "Temp"),
            ):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"public class {cls} {{}}", encoding="utf-8")
            nodes = graph_builder.GraphBuilder(str(root)).build_graph()["nodes"]
            self.assertIn("Keep", nodes)
            for skipped in ("Vendored", "Venv", "Git", "Built", "Temp"):
                self.assertNotIn(skipped, nodes)


class TestSinglePassPerformance(unittest.TestCase):
    """Walk once, parse each file once, compile each query once."""

    def _repo(self, root: Path):
        (root / "main.tf").write_text(
            'variable "region" {}\nresource "aws_x" "y" {\n  r = var.region\n}\n', encoding="utf-8"
        )
        (root / "A.java").write_text("public class A { }", encoding="utf-8")

    def test_prewalked_file_list_skips_second_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            files = [root / "main.tf", root / "A.java"]
            original = graph_builder.os.walk

            def boom(*a, **k):
                raise AssertionError("os.walk called despite pre-walked file list")

            graph_builder.os.walk = boom
            try:
                graph = graph_builder.GraphBuilder(str(root)).build_graph(files=files)
            finally:
                graph_builder.os.walk = original
            self.assertIn("A", graph["nodes"])
            self.assertIn("region", graph["nodes"])

    def test_hcl_files_parsed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            builder = graph_builder.GraphBuilder(str(root))
            real = builder.parsers["hcl"]
            calls = []

            class CountingParser:
                def parse(self, content, *a, **k):
                    calls.append(1)
                    return real.parse(content, *a, **k)

            builder.parsers["hcl"] = CountingParser()
            builder.build_graph()
            self.assertEqual(len(calls), 1)

    def test_hcl_results_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            graph = graph_builder.GraphBuilder(str(root)).build_graph()
            self.assertEqual(graph["nodes"]["region"]["file"], "main.tf")

    def test_mapper_exposes_walked_graph_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            (root / "notes.md").write_text("x", encoding="utf-8")
            mapper = _load("code_mapper").CodeMapper(str(root), cache_dir=str(Path(tmp) / "cache_out"))
            mapper.map_repo()
            names = sorted(p.name for p in mapper.graph_files)
            self.assertEqual(names, ["A.java", "main.tf"])


class TestMapperStatFastPath(unittest.TestCase):
    """Warm runs must not read every file: unchanged (mtime, size) skips hashing entirely."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        self.cache = str(Path(self._tmp.name) / "cache")
        self.src = self.root / "x.py"
        self.src.write_text("def a(): pass\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _mapper(self):
        return _load("code_mapper").CodeMapper(str(self.root), cache_dir=self.cache)

    def test_unchanged_file_is_not_rehashed(self):
        self._mapper().map_repo()
        warm = self._mapper()
        calls = []
        real = warm.get_hash
        warm.get_hash = lambda p: (calls.append(p), real(p))[1]
        warm.map_repo()
        self.assertEqual(calls, [])

    def test_same_size_content_change_is_detected(self):
        self._mapper().map_repo()
        self.src.write_text("def b(): pass\n", encoding="utf-8")  # same length as before
        import os

        st = self.src.stat()
        os.utime(self.src, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
        cache = self._mapper().map_repo()
        self.assertIn("b", cache["x.py"]["public_functions"])

    def test_touch_without_content_change_is_not_reindexed(self):
        self._mapper().map_repo()
        import os

        st = self.src.stat()
        os.utime(self.src, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
        warm = self._mapper()
        indexed = []
        real = warm._index_file
        warm._index_file = lambda *a, **k: (indexed.append(a[1]), real(*a, **k))[1]
        warm.map_repo()
        self.assertEqual(indexed, [])


class TestParallelWalkParity(unittest.TestCase):
    """Parallel directory walk must select exactly the files a serial os.walk with pruning would."""

    def test_matches_serial_walk(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            for rel in (
                "a/x.py",
                "a/b/c/y.java",
                "a/b/z.tf",
                "node_modules/n/skip.py",
                ".venv/lib/skip.py",
                "temp_dir/skip.py",
                "skills/skip.py",
                "deep/1/2/3/4/5/leaf.go",
                "top.hcl",
            ):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            os.symlink(root / "a", root / "link_to_a")  # os.walk lists it but never descends
            os.symlink(root / "top.hcl", root / "link_to_file.hcl")

            skip = {".git", ".venv", "venv", "node_modules", "target", "build", "dist",
                    "__pycache__", ".ast_cache", "temp_", "skills"}
            serial = set()
            for d, dirs, names in os.walk(root):
                dirs[:] = [x for x in dirs if x not in skip and not x.startswith("temp_")]
                serial.update(str(Path(d) / n) for n in names)

            mapper = _load("code_mapper").CodeMapper(str(root), cache_dir=str(Path(tmp) / "cache"))
            parallel = {str(p) for p in mapper._walk_files(skip)}
            self.assertEqual(parallel, serial)


class TestCodeMapCatalog(unittest.TestCase):
    """code_map.md must carry the structural catalog (routes, injections, calls), not just names."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        for rel, src in FIXTURE.items():
            path = root / "src" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(src, encoding="utf-8")
        code_mapper = _load("code_mapper")
        mapper = code_mapper.CodeMapper(str(root))
        mapper.map_repo()
        mapper.attach_catalog()
        cls.catalogs = mapper.catalogs
        out = root / "code_map.md"
        mapper.serialize_markdown(str(out))
        cls.text = out.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_no_placeholder_fields(self):
        self.assertNotIn("Pending", self.text)
        self.assertNotIn("**Summary**", self.text)

    def test_catalog_lists_class_annotations_and_injections(self):
        self.assertIn("DataController @RestController", self.text)
        self.assertIn("injects: DataService", self.text)

    def test_catalog_lists_routes_with_resolved_calls(self):
        self.assertIn("GET /api/v1/data/{id}", self.text)
        self.assertIn("DataService.getData", self.text)

    def test_catalog_lists_throws(self):
        self.assertIn("throws: ResourceNotFoundException", self.text)

    def test_catalog_is_smaller_than_its_source(self):
        # Whole-map size is dominated by fixed per-file boilerplate on a tiny fixture,
        # so compare each catalog against the source it summarizes.
        for rel, src in FIXTURE.items():
            catalog = self.catalogs.get(f"src/{rel}", "")
            self.assertLess(len(catalog), len(src), rel)


class TestAutoContext(unittest.TestCase):
    """auto_context must rank files from the graph, not wrap the whole map in a prompt."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        for rel, src in FIXTURE.items():
            path = cls.root / "src" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(src, encoding="utf-8")
        graph = graph_builder.GraphBuilder(str(cls.root / "src")).build_graph()
        cls.lens = _load("auto_context").ContextLens(graph)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def files(self, task, top=10):
        return [r["file"] for r in self.lens.rank(task, top)]

    def test_named_class_is_first_and_dependents_follow(self):
        files = self.files("add a field to DataDTO")
        self.assertEqual(files[0], "dto/DataDTO.java")
        self.assertIn("service/DataService.java", files)
        self.assertIn("controller/DataController.java", files)

    def test_unrelated_files_are_excluded(self):
        self.assertNotIn("exception/ResourceNotFoundException.java", self.files("add a field to DataDTO"))

    def test_qualified_method_anchors_on_owning_class(self):
        files = self.files("fix DataService.createData")
        self.assertEqual(files[0], "service/DataService.java")
        self.assertIn("repository/DataRepository.java", files)  # dependency of the seed

    def test_plain_lowercase_word_is_not_a_symbol(self):
        # "getData" is camelCase and anchors; the prose word "validate" must not hit RangeValidator.validate.
        self.assertEqual(self.files("please validate things"), [])

    def test_annotation_query(self):
        self.assertEqual(self.files("review @Entity classes")[0], "domain/Data.java")

    def test_top_limits_results(self):
        self.assertLessEqual(len(self.files("DataService", top=2)), 2)

    def test_no_match_returns_empty(self):
        self.assertEqual(self.files("rotate the moon"), [])

    def test_reasons_are_reported(self):
        first = self.lens.rank("add a field to DataDTO")[0]
        self.assertEqual(first["roles"], ["seed"])
        self.assertTrue(first["reasons"])


class TestAutoContextCli(unittest.TestCase):
    def run_cli(self, *args):
        import subprocess
        import sys

        return subprocess.run(
            [sys.executable, str(BRIDGE / "auto_context.py"), *args], capture_output=True, text=True
        )

    def test_src_mode_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel, src in FIXTURE.items():
                path = Path(tmp) / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(src, encoding="utf-8")
            ok = self.run_cli("change DataDTO", "--src", tmp, "--json")
            self.assertEqual(ok.returncode, 0, ok.stderr)
            import json

            self.assertEqual(json.loads(ok.stdout)[0]["file"], "dto/DataDTO.java")
            miss = self.run_cli("rotate the moon", "--src", tmp)
            self.assertEqual(miss.returncode, 2)

    def test_missing_graph_path_fails(self):
        self.assertEqual(self.run_cli("x", "--graph", "/nonexistent/graph.json").returncode, 1)


class TestSearchMap(unittest.TestCase):
    def search(self, text, query):
        import contextlib
        import io

        search_map = _load("search_map")
        with tempfile.TemporaryDirectory() as tmp:
            mp = Path(tmp) / "map.md"
            mp.write_text(text, encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                count = search_map.search_map(query, str(mp))
        return count, buf.getvalue()

    def test_code_mapper_format_returns_only_matching_blocks(self):
        text = "# Repository Code Map\n\n### a/A.java\n- Types: Alpha\n\n### b/B.java\n- Types: Beta\n"
        count, out = self.search(text, "beta")
        self.assertEqual(count, 1)
        self.assertIn("b/B.java", out)
        self.assertNotIn("a/A.java", out)
        self.assertNotIn("Repository Code Map", out)

    def test_file_format_is_still_supported(self):
        count, out = self.search("FILE: x.py\ndef run(): pass\n----\nFILE: y.py\nclass Y: pass\n", "run")
        self.assertEqual(count, 1)
        self.assertIn("x.py", out)

    def test_no_match(self):
        self.assertEqual(self.search("### a.java\nx\n", "zzz")[0], 0)

    def test_truncates_at_ten(self):
        text = "".join(f"### f{i}.java\nmatch\n" for i in range(15))
        count, out = self.search(text, "match")
        self.assertEqual(count, 10)
        self.assertIn("Truncated", out)


class TestSemanticEdit(unittest.TestCase):
    """semantic_edit replaces one AST declaration and never anything else."""

    JAVA = (
        "public class A {\n  void keep() {}\n  void target() { int x = 1; }\n  void dup() {}\n}\n"
        "class B { void dup() {} }\n"
    )

    def setUp(self):
        self.edit = _load("semantic_edit")
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, text):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_replaces_only_the_named_method(self):
        p = self.write("A.java", self.JAVA)
        self.assertTrue(self.edit.semantic_replace(p, "method", "A.target", "void target() { int x = 2; }"))
        self.assertEqual(Path(p).read_text(), self.JAVA.replace("int x = 1", "int x = 2"))

    def test_ambiguous_bare_name_is_refused_and_file_untouched(self):
        p = self.write("A.java", self.JAVA)
        self.assertFalse(self.edit.semantic_replace(p, "method", "dup", "void dup() {}"))
        self.assertEqual(Path(p).read_text(), self.JAVA)

    def test_missing_symbol_is_refused(self):
        p = self.write("A.java", self.JAVA)
        self.assertFalse(self.edit.semantic_replace(p, "method", "A.nope", "void nope() {}"))
        self.assertEqual(Path(p).read_text(), self.JAVA)

    def test_text_in_other_nodes_does_not_match(self):
        # "int x" appears inside a method body; it must not be treated as a symbol.
        p = self.write("A.java", self.JAVA)
        self.assertFalse(self.edit.semantic_replace(p, "method", "x", "void x() {}"))

    def test_unparseable_replacement_is_refused(self):
        p = self.write("A.java", self.JAVA)
        self.assertFalse(self.edit.semantic_replace(p, "method", "A.target", "void target( {"))
        self.assertEqual(Path(p).read_text(), self.JAVA)

    def test_dry_run_does_not_write(self):
        import contextlib
        import io

        p = self.write("A.java", self.JAVA)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertTrue(self.edit.semantic_replace(p, "method", "A.target", "void target() {}", dry_run=True))
        self.assertIn("+  void target() {}", buf.getvalue())
        self.assertEqual(Path(p).read_text(), self.JAVA)

    def test_terraform_resource_by_type_and_name(self):
        tf = 'resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n\nvariable "env" {}\n'
        p = self.write("m.tf", tf)
        new = 'resource "aws_vpc" "main" {\n  cidr_block = "10.1.0.0/16"\n}'
        self.assertTrue(self.edit.semantic_replace(p, "resource", "aws_vpc.main", new))
        self.assertEqual(Path(p).read_text(), tf.replace("10.0.0.0", "10.1.0.0"))

    def test_yaml_dotted_key(self):
        p = self.write("d.yaml", "spec:\n  replicas: 2\n  name: x\n")
        self.assertTrue(self.edit.semantic_replace(p, "key", "spec.replicas", "replicas: 5"))
        self.assertEqual(Path(p).read_text(), "spec:\n  replicas: 5\n  name: x\n")

    def test_unsupported_extension(self):
        p = self.write("a.txt", "x")
        self.assertFalse(self.edit.semantic_replace(p, "method", "x", "y"))


class TestSkillCopiesStayInSync(unittest.TestCase):
    """bin/ast-bridge is canonical; skill-code-map ships byte-identical copies."""

    def test_copies_identical(self):
        skill = REPO_ROOT / ".agent" / "skills" / "skill-code-map" / "scripts"
        for name in ("auto_context", "search_map", "semantic_query", "semantic_edit", "graph_builder", "code_mapper"):
            self.assertEqual(
                (BRIDGE / f"{name}.py").read_bytes(), (skill / f"{name}.py").read_bytes(), name
            )


if __name__ == "__main__":
    unittest.main()
