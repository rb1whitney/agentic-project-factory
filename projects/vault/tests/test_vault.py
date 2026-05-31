import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from projects.vault.bin.cluster_encrypt_ops import handle_encrypt
from projects.vault.bin.cluster_init import init_cluster
from projects.vault.bin.cluster_backup import backup

def test_cluster_encrypt_ops_import():
    assert callable(handle_encrypt)

def test_cluster_init_import():
    assert callable(init_cluster)

def test_cluster_backup_import():
    assert callable(backup)
