import os
from pathlib import Path


def init_repo(target_path: str, project_name: str):
    """Bootstraps a directory into a 100% compliant Agentic Repository."""
    base_dir = Path(target_path).resolve()
    print(f"Bootstrapping Agentic Hub: {project_name} at {base_dir}")

    # 1. Create Core Structure
    (base_dir / "agents").mkdir(parents=True, exist_ok=True)
    (base_dir / "skills").mkdir(parents=True, exist_ok=True)
    (base_dir / "conductor").mkdir(parents=True, exist_ok=True)
    (base_dir / ".github").mkdir(parents=True, exist_ok=True)
    (base_dir / ".agents").mkdir(parents=True, exist_ok=True)
    (base_dir / ".antigravitycli").mkdir(parents=True, exist_ok=True)
    (base_dir / ".claude").mkdir(parents=True, exist_ok=True)
    (base_dir / ".copilot").mkdir(parents=True, exist_ok=True)

    # 2. Load and Apply Templates
    template_dir = Path(__file__).parent / "templates"

    # AGENT.md
    agent_path = base_dir / "AGENT.md"
    agent_content = template_dir.joinpath("AGENT.md").read_text().replace("{{ project_name }}", project_name)
    agent_path.write_text(agent_content)

    # .cursorrules
    cursor_path = base_dir / ".cursorrules"
    cursor_content = template_dir.joinpath("cursorrules").read_text().replace("{{ project_name }}", project_name)
    cursor_path.write_text(cursor_content)

    # 3. Establish AI Nexus (Symlinks)
    os.chdir(base_dir)

    # .agents Nexus
    os.system("ln -sf ../AGENT.md .agents/AGENT.md")
    os.system("ln -sf ../agents .agents/agents")
    os.system("ln -sf ../skills .agents/skills")

    # .antigravitycli Nexus
    os.system("ln -sf ../AGENT.md .antigravitycli/AGENT.md")
    os.system("ln -sf ../agents .antigravitycli/agents")
    os.system("ln -sf ../skills .antigravitycli/skills")

    # .claude Nexus
    os.system("ln -sf ../AGENT.md .claude/AGENT.md")
    os.system("ln -sf ../agents .claude/agents")
    os.system("ln -sf ../skills .claude/skills")

    # .copilot Nexus
    os.system("ln -sf ../AGENT.md .copilot/AGENT.md")
    os.system("ln -sf ../agents .copilot/agents")
    os.system("ln -sf ../skills .copilot/skills")

    # .github Instructions
    os.system("ln -sf ../AGENT.md .github/copilot-instructions.md")

    print(f"Successfully institutionalized {project_name}. Hub is now AGENTIC.")


if __name__ == "__main__":
    # Test stub
    import sys

    if len(sys.argv) > 2:
        init_repo(sys.argv[1], sys.argv[2])
