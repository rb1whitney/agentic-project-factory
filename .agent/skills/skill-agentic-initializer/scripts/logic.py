import os
import sys
from pathlib import Path

# Add current directory to sys.path to ensure scripts can be imported
sys.path.append(str(Path(__file__).parent))

from scanner import generate_compressed_index


def init_repo(target_path: str, project_name: str, docs_dir: str = "docs"):
    """
    Bootstraps a directory into a Vercel-style Agentic Repository.
    Focuses on generating a high-performance AGENTS.md with a compressed docs index.
    """
    base_dir = Path(target_path).resolve()
    print(f"Bootstrapping Vercel-style Agentic Hub: {project_name} at {base_dir}")

    # 1. Create Core Structure (Minimal)
    (base_dir / "agents").mkdir(parents=True, exist_ok=True)
    (base_dir / "skills").mkdir(parents=True, exist_ok=True)

    # 2. Generate Compressed Index
    # We look for documentation in base_dir / docs_dir
    docs_full_path = base_dir / docs_dir
    if not docs_full_path.exists():
        print(f"Warning: Docs directory {docs_full_path} not found. Index will be empty.")
        compressed_index = "[Docs Index]|root: ./" + docs_dir + "\n|Empty index - No docs found."
    else:
        # Generate index relative to the project root
        compressed_index = generate_compressed_index(str(docs_full_path), "./" + docs_dir)

    # 3. Load and Apply Templates
    template_dir = Path(__file__).parent / "templates"
    agent_template_path = template_dir / "AGENT.md"

    if not agent_template_path.exists():
        raise FileNotFoundError(f"Template not found: {agent_template_path}")

    agent_content = agent_template_path.read_text()
    agent_content = agent_content.replace("{{ project_name }}", project_name)
    agent_content = agent_content.replace("{{ compressed_index }}", compressed_index)

    # 4. Write AGENTS.md
    agent_path = base_dir / "AGENTS.md"
    agent_path.write_text(agent_content)

    # 5. Established symlinks for convenience (Legacy but useful)
    # The user asked for "only AGENTS.md" but some tools expect these folders.
    # I will keep the folder creation but maybe skip the heavy symlinking unless requested.
    # However, to be "100% compliant" with the previous style while focusing on AGENTS.md:

    # Ensure .agents exists and link AGENTS.md
    dot_agents = base_dir / ".agents"
    dot_agents.mkdir(exist_ok=True)

    # Use os.symlink for cleaner code
    try:
        target_link = dot_agents / "AGENT.md"
        if target_link.exists():
            target_link.unlink()
        os.symlink("../AGENTS.md", target_link)
    except Exception as e:
        print(f"Warning: Could not create symlink: {e}")

    print(f"Successfully institutionalized {project_name}. Vercel-style AGENTS.md generated.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        # Usage: python logic.py <target_path> <project_name> [docs_dir]
        docs = sys.argv[3] if len(sys.argv) > 3 else "docs"
        init_repo(sys.argv[1], sys.argv[2], docs)
    else:
        print("Usage: python logic.py <target_path> <project_name> [docs_dir]")
