import pytest
from projects.vault.bin.manage_dr_state import check_dr_status
from projects.vault.bin.encrypt_secret_data import encrypt_data
from projects.vault.bin.cluster_init import initialize_cluster

def test_manage_dr_state_import():
    assert callable(check_dr_status)

def test_encrypt_secret_data_import():
    assert callable(encrypt_data)

def test_cluster_init_import():
    assert callable(initialize_cluster)
