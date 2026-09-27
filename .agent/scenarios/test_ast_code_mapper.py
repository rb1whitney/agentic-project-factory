#!/usr/bin/env python3
"""
Scenario Test: Multi-Language AST Symbol & Semantic Graph Extraction
Validates that bin/ast-bridge/code_mapper.py accurately extracts symbols and declarations
across Python, Java, Golang, Terraform (HCL), Kubernetes manifests, and Ansible playbooks.
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CODE_MAPPER_PATH = REPO_ROOT / "bin" / "ast-bridge" / "code_mapper.py"

spec = importlib.util.spec_from_file_location("code_mapper", str(CODE_MAPPER_PATH))
code_mapper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(code_mapper_module)
CodeMapper = code_mapper_module.CodeMapper


class TestAstCodeMapper(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.mapper = CodeMapper(str(self.root))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_python_ast_extraction(self):
        py_file = self.root / "service.py"
        py_file.write_text(
            "class OrderProcessor:\n"
            "    def process_order(self):\n"
            "        pass\n\n"
            "def calculate_tax():\n"
            "    pass\n",
            encoding="utf-8",
        )
        cache = self.mapper.map_repo()
        entry = cache.get("service.py", {})
        self.assertIn("OrderProcessor", entry.get("public_types", []))
        self.assertIn("process_order", entry.get("public_functions", []))
        self.assertIn("calculate_tax", entry.get("public_functions", []))

    def test_golang_ast_extraction(self):
        go_file = self.root / "handler.go"
        go_file.write_text(
            "package main\n\n"
            "type UserStore struct {}\n"
            "type AuthManager interface {}\n\n"
            "func (u *UserStore) GetUser() {}\n"
            "func InitializeServer() {}\n",
            encoding="utf-8",
        )
        cache = self.mapper.map_repo()
        entry = cache.get("handler.go", {})
        self.assertIn("UserStore", entry.get("public_types", []))
        self.assertIn("AuthManager", entry.get("public_types", []))
        self.assertIn("GetUser", entry.get("public_functions", []))
        self.assertIn("InitializeServer", entry.get("public_functions", []))

    def test_java_ast_extraction(self):
        java_file = self.root / "AccountService.java"
        java_file.write_text(
            "public class AccountService {\n"
            "    public void deposit() {}\n"
            "}\n",
            encoding="utf-8",
        )
        cache = self.mapper.map_repo()
        entry = cache.get("AccountService.java", {})
        self.assertIn("AccountService", entry.get("public_types", []))
        self.assertIn("deposit", entry.get("public_functions", []))

    def test_terraform_hcl_ast_extraction(self):
        tf_file = self.root / "main.tf"
        tf_file.write_text(
            'resource "aws_s3_bucket" "audit_bucket" {\n'
            '  bucket = "audit-log"\n'
            '}\n\n'
            'module "vpc" {\n'
            '  source = "terraform-aws-modules/vpc/aws"\n'
            '}\n',
            encoding="utf-8",
        )
        cache = self.mapper.map_repo()
        entry = cache.get("main.tf", {})
        declarations = entry.get("declarations", [])
        self.assertIn("resource:aws_s3_bucket/audit_bucket", declarations)
        self.assertIn("module:vpc", declarations)

    def test_kubernetes_manifest_extraction(self):
        k8s_file = self.root / "deployment.yaml"
        k8s_file.write_text(
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: payment-api\n"
            "  namespace: production\n"
            "spec:\n"
            "  replicas: 3\n",
            encoding="utf-8",
        )
        cache = self.mapper.map_repo()
        entry = cache.get("deployment.yaml", {})
        declarations = entry.get("declarations", [])
        self.assertIn("k8s:Deployment/production/payment-api", declarations)

    def test_ansible_playbook_extraction(self):
        ansible_file = self.root / "playbook.yml"
        ansible_file.write_text(
            "- name: Configure Web Servers\n"
            "  hosts: webservers\n"
            "  tasks:\n"
            "    - name: Ensure Nginx is installed\n"
            "      apt:\n"
            "        name: nginx\n"
            "        state: present\n",
            encoding="utf-8",
        )
        cache = self.mapper.map_repo()
        entry = cache.get("playbook.yml", {})
        declarations = entry.get("declarations", [])
        self.assertIn("ansible:play/Configure Web Servers", declarations)


if __name__ == "__main__":
    unittest.main()
