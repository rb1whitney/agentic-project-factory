import pytest
import os
from unittest.mock import patch, MagicMock

from projects.vault_controller_example.bin.manage_vault import process_file, run_vault_command, process_api_object

def test_run_vault_command_success():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b'{"data": "success"}')
        result = run_vault_command(["vault", "read", "-format=json", "secret/foo"])
        assert result == '{"data": "success"}'

def test_process_api_object_get():
    api_obj = {"api_path": "secret/data/test", "api_method": "get"}
    with patch('projects.vault_controller_example.bin.manage_vault.run_vault_command') as mock_run:
        process_api_object(api_obj)
        mock_run.assert_called_with(["vault", "read", "-format=json", "secret/data/test"])
