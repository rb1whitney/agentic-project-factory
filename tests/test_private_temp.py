"""Anything kept in a shared temp directory must be private to the user, or not used at all."""

import inspect
import os
import stat
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agent" / "skills" / "skill-code-map" / "scripts"))

import code_mapper as cm  # noqa: E402
import hydrate_policies as hp  # noqa: E402
import noise_gate as ng  # noqa: E402


def mode(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


def test_gate_state_lives_in_a_directory_only_the_user_can_open(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    state = ng._default_state({"session_id": "s"}, "repo")
    assert state.parent.parent == tmp_path
    assert mode(state.parent) == 0o700


def test_gate_refuses_a_state_directory_someone_else_planted(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    victim = tmp_path / "victim"
    victim.mkdir()
    (tmp_path / f"noise_gate-{os.getuid()}").symlink_to(victim)
    with pytest.raises(OSError):
        ng._default_state({"session_id": "s"}, "repo")
    assert list(victim.iterdir()) == []


@pytest.mark.parametrize("module", [ng, cm])
def test_a_directory_owned_by_another_user_is_refused(tmp_path, monkeypatch, module):
    target = tmp_path / "d"
    target.mkdir()
    real = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: real + 1)
    with pytest.raises(OSError):
        module._private_dir(target)


def test_mapper_temp_fallback_refuses_a_symlink(tmp_path):
    link = tmp_path / "link"
    link.symlink_to(tmp_path)
    with pytest.raises(OSError):
        cm._private_dir(link)


def test_downloaded_rules_are_not_cached_in_shared_temp():
    default = inspect.signature(hp.hydrate).parameters["cache_dir"].default
    assert default == hp.DEFAULT_RULE_CACHE
    assert not default.startswith(tempfile.gettempdir())
    assert default.endswith("upstream-rules")
