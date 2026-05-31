import subprocess
import sys
from projects.vault.lib.logger import get_logger

logger = get_logger("secure_cmd")

def run(cmd, check=True, cwd=None, capture_output=True):
    """
    Execute a subprocess command securely.
    Ensures that cmd is a list of arguments, preventing shell injection.
    """
    if not isinstance(cmd, list):
        logger.error(f"Command must be a list to prevent shell injection, got: {type(cmd)}")
        sys.exit(1)
        
    logger.info(f"Running secure command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,  # We handle the check manually
            shell=False,  # Strictly forbidden
            cwd=cwd
        )
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        sys.exit(1)
        
    if check and result.returncode != 0:
        logger.error(f"Command failed with exit code {result.returncode}: {result.stderr}")
        sys.exit(result.returncode)
        
    return result
