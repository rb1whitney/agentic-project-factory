import os
import yaml
from pathlib import Path

def convert_agent(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    if not content.startswith('---'):
        return

    try:
        parts = content.split('---', 2)
        if len(parts) < 3:
            return
        
        frontmatter = yaml.safe_load(parts[1])
        if 'tools' in frontmatter:
            if isinstance(frontmatter['tools'], list):
                tools_list = frontmatter['tools']
                frontmatter['tools'] = {tool: True for tool in tools_list}
            elif isinstance(frontmatter['tools'], dict):
                # Ensure all values are boolean
                frontmatter['tools'] = {k: True for k in frontmatter['tools']}
            
            new_frontmatter = yaml.dump(frontmatter, sort_keys=False)
            new_content = f"---{os.linesep}{new_frontmatter}---{parts[2]}"
            
            with open(file_path, 'w') as f:
                f.write(new_content)
            print(f"Converted {file_path}")
    except Exception as e:
        print(f"Error converting {file_path}: {e}")

agent_dir = Path(".agent/agents")
for agent_file in agent_dir.glob("*.md"):
    convert_agent(agent_file)
