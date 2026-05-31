import json
import os
import subprocess
import time
import pytest

VAULT_DEV_LISTEN_ADDRESS = "localhost:8200"
VAULT_DEV_ROOT_TOKEN_ID = "ePTlEeggAGoYE1OMGiUas8du"

@pytest.fixture(scope="function")
def vault_server():
    """
    Spins up a dev vault server and cleans it up after the test completes.
    """
    env = os.environ.copy()
    env["VAULT_DEV_LISTEN_ADDRESS"] = VAULT_DEV_LISTEN_ADDRESS
    env["VAULT_DEV_ROOT_TOKEN_ID"] = VAULT_DEV_ROOT_TOKEN_ID
    env["VAULT_TOKEN"] = VAULT_DEV_ROOT_TOKEN_ID
    env["VAULT_ADDR"] = f"http://{VAULT_DEV_LISTEN_ADDRESS}"
    
    # Start the vault server in the background
    import shutil
    if not shutil.which("vault"):
        pytest.skip("Vault binary not found in PATH")
        
    process = subprocess.Popen(
        ["vault", "server", "-dev", "-dev-no-store-token"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for vault to initialize
    time.sleep(2)
    
    yield env

    # Teardown
    process.terminate()
    process.wait()

def run_cluster_secret_data(args, env):
    """
    Helper to run bin/cluster_secret_data.py with proper pythonpath and environment
    """
    cmd = ["python3", "bin/cluster_secret_data.py", "--name", "dev"] + args
    return subprocess.run(cmd, env=env, capture_output=True, text=True)

def test_spinning_up_cluster_admin_config(vault_server):
    env = vault_server
    result = run_cluster_secret_data(["--path", "./config/admin"], env)
    assert result.returncode == 0, f"Setup failed: {result.stderr}"

def test_spinning_up_cluster_app1_config(vault_server):
    env = vault_server
    # 1. Admin config
    res1 = run_cluster_secret_data(["--path", "./config/admin"], env)
    assert res1.returncode == 0
    
    # 2. App1 specific config files
    # Instead of find, we just iterate or run on the specific json files
    import glob
    app1_configs = glob.glob("./config/app1/*.json")
    for f in app1_configs:
        res2 = run_cluster_secret_data(["--path", f], env)
        assert res2.returncode == 0
        
    # 3. Vault transit write
    with open("tests/fixtures/app1-transit-key", "r") as f:
        backup_val = f.read().strip()
    
    cmd_transit = [
        "vault", "write", "/transit/restore/app1-transit-key", 
        f"backup={backup_val}", "force=true"
    ]
    res3 = subprocess.run(cmd_transit, env=env, capture_output=True, text=True)
    assert res3.returncode == 0
    
    # 4. App1 kv
    res4 = run_cluster_secret_data(["--path", "./config/app1/kv/"], env)
    assert res4.returncode == 0

def test_spinning_up_improperly_written_json(vault_server):
    env = vault_server
    result = run_cluster_secret_data(["--path", "./tests/fixtures/invalid-file.json"], env)
    assert result.returncode != 0

def test_spinning_up_invalid_json_file(vault_server):
    env = vault_server
    result = run_cluster_secret_data(["--path", "./tests/fixtures/invalid-payload.json"], env)
    assert result.returncode != 0

def test_logging_into_cluster(vault_server):
    env = vault_server
    res1 = run_cluster_secret_data(["--path", "./config/admin"], env)
    assert res1.returncode == 0
    
    username = "vaultdeveloper1"
    # Parse password from tests/fixtures/ldap.ldif
    password = None
    with open("tests/fixtures/ldap.ldif", "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith(f"uid: {username}"):
                for check_line in lines[i:i+4]:
                    if "userpassword:" in check_line.lower():
                        password = check_line.split(" ")[1].strip()
                        break
                break
    assert password is not None
    
    cmd_login = ["vault", "login", "-method=ldap", f"username={username}", f"password={password}"]
    res2 = subprocess.run(cmd_login, env=env, capture_output=True, text=True)
    assert res2.returncode == 0

def test_incorrect_password(vault_server):
    env = vault_server
    res1 = run_cluster_secret_data(["--path", "./config/admin"], env)
    assert res1.returncode == 0
    
    username = "vaultdeveloper1"
    password = "thisisnotright"
    
    cmd_login = ["vault", "login", "-method=ldap", f"username={username}", f"password={password}"]
    res2 = subprocess.run(cmd_login, env=env, capture_output=True, text=True)
    # the bats test expects status 2
    assert res2.returncode == 2

def test_write_wrapped_token(vault_server):
    env = vault_server
    res1 = run_cluster_secret_data(["--path", "./config/admin"], env)
    assert res1.returncode == 0
    
    # Get a wrapped token
    cmd_wrap = ["vault", "write", "sys/wrapping/wrap", "blah=blah"]
    res_wrap = subprocess.run(cmd_wrap, env=env, capture_output=True, text=True)
    assert res_wrap.returncode == 0
    
    wrapped_token = ""
    for line in res_wrap.stdout.splitlines():
        if "wrapping_token:" in line:
            wrapped_token = line.split()[1].strip()
            break
            
    assert wrapped_token != ""
    
    payload = {
        "api_objects": [
            {
                "api_method": "post",
                "api_path": "vault-admin/wrapped-token-test",
                "wrapped_token": wrapped_token
            }
        ]
    }
    
    with open("wrapped-token-test.json", "w") as f:
        json.dump(payload, f)
        
    try:
        res2 = run_cluster_secret_data(["--path", "./wrapped-token-test.json"], env)
        assert res2.returncode == 0
    finally:
        if os.path.exists("wrapped-token-test.json"):
            os.remove("wrapped-token-test.json")
