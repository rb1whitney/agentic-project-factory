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


if __name__ == "__main__":
    unittest.main()
