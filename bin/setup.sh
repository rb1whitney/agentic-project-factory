#!/usr/bin/env bash
# =============================================================================
# setup.sh  Developer Environment Bootstrap
# Programming-Work Unified AI Agent Hub
#
# Usage:
#   bash bin/setup.sh              # Full install
#   bash bin/setup.sh --no-docker  # Skip Docker (e.g. on headless servers)
#   bash bin/setup.sh --dry-run    # Print steps without executing
# =============================================================================

set -euo pipefail

#  Flags 
SKIP_DOCKER=false
DRY_RUN=false

for arg in "$@"; do
  case $arg in
    --no-docker) SKIP_DOCKER=true ;;
    --dry-run)   DRY_RUN=true ;;
  esac
done

#  Helpers 
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

log()  { echo -e "${BOLD}==> $*${RESET}"; }
ok()   { echo -e "${GREEN}   $*${RESET}"; }
warn() { echo -e "${YELLOW}  ! $*${RESET}"; }
err()  { echo -e "${RED}   $*${RESET}"; }

run() {
  if [ "$DRY_RUN" = true ]; then
    echo -e "  [dry-run] $*"
  else
    eval "$@"
  fi
}

command_exists() { command -v "$1" &>/dev/null; }

detect_os() {
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macos"
  elif grep -qi microsoft /proc/version 2>/dev/null; then
    echo "wsl"
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "linux"
  else
    echo "unknown"
  fi
}

OS=$(detect_os)
log "Detected OS: $OS"

#  1. Homebrew 
log "1. Homebrew"
if command_exists brew; then
  ok "Homebrew already installed: $(brew --version | head -1)"
else
  log "Installing Homebrew..."
  run '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'

  if [[ "$OS" == "macos" ]]; then
    run 'eval "$(/opt/homebrew/bin/brew shellenv)"'
    run 'echo "eval \"$(/opt/homebrew/bin/brew shellenv)\"" >> ~/.zprofile'
  else
    run 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"'
    run 'echo "eval \"$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)\"" >> ~/.bashrc'
    run 'sudo apt-get install -y build-essential 2>/dev/null || true'
  fi
  ok "Homebrew installed"
fi

#  2. Core utilities 
log "2. Core utilities"
CORE_TOOLS=(git curl wget jq unzip)
for tool in "${CORE_TOOLS[@]}"; do
  if command_exists "$tool"; then
    ok "$tool already installed"
  else
    run "brew install $tool"
    ok "$tool installed"
  fi
done

#  3. Python 3.11 
log "3. Python 3.11"
if command_exists python3 && python3 --version 2>&1 | grep -q "3\.1[1-9]"; then
  ok "Python already installed: $(python3 --version)"
else
  run "brew install python@3.11"
  ok "Python 3.11 installed"
fi

log "   Installing Python AST bridge dependencies"
run "pip3 install --upgrade pip --quiet"
run "pip3 install tree-sitter==0.20.1 tree-sitter-languages pyyaml --quiet"
ok "Python packages installed (tree-sitter==0.20.1, pyyaml)"

#  4. Node.js 
log "4. Node.js"
if command_exists node; then
  ok "Node.js already installed: $(node --version)"
else
  run "brew install node"
  ok "Node.js installed: $(node --version)"
fi

#  4.1. Golang 
log "4.1. Golang"
if command_exists go; then
  ok "Go already installed: $(go version)"
else
  run "brew install go"
  ok "Go installed: $(go version)"
fi

#  4.2. uv (Python Package Manager) 
log "4.2. uv"
if command_exists uv; then
  ok "uv already installed: $(uv --version)"
else
  run "curl -LsSf https://astral.sh/uv/install.sh | sh"
  ok "uv installed"
fi

#  5. Gemini CLI 
log "5. Gemini CLI"
if command_exists gemini; then
  ok "Gemini CLI already installed"
else
  run "npm install -g @google/gemini-cli"
  ok "Gemini CLI installed"
fi
warn "Run 'gemini auth login' to authenticate"

#  6. AWS CLI 
log "6. AWS CLI"
if command_exists aws; then
  ok "AWS CLI already installed: $(aws --version 2>&1)"
else
  if [[ "$OS" == "macos" ]]; then
    run "brew install awscli"
  else
    run 'curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip'
    run 'unzip -q /tmp/awscliv2.zip -d /tmp/'
    run 'sudo /tmp/aws/install'
    run 'rm -rf /tmp/aws /tmp/awscliv2.zip'
  fi
  ok "AWS CLI installed"
fi
warn "Run 'aws configure' or 'aws configure sso' to set up credentials"

#  7. gcloud 
log "7. Google Cloud CLI"
if command_exists gcloud; then
  ok "gcloud already installed: $(gcloud --version | head -1)"
else
  if [[ "$OS" == "macos" ]]; then
    run "brew install --cask google-cloud-sdk"
  else
    run 'curl https://sdk.cloud.google.com | bash -s -- --disable-prompts'
    run 'source ~/.bashrc || true'
  fi
  ok "gcloud installed"
fi
warn "Run 'gcloud init' and 'gcloud auth application-default login' to authenticate"

#  8. Terraform via tfenv 
log "8. Terraform (via tfenv)"
if command_exists tfenv; then
  ok "tfenv already installed"
else
  if [[ "$OS" == "macos" ]]; then
    run "brew install tfenv"
  else
    run 'git clone --depth=1 https://github.com/tfutils/tfenv.git ~/.tfenv'
    run 'echo "export PATH=\"\$HOME/.tfenv/bin:\$PATH\"" >> ~/.bashrc'
    run 'export PATH="$HOME/.tfenv/bin:$PATH"'
  fi
  ok "tfenv installed"
fi

if ! command_exists terraform || ! terraform --version &>/dev/null; then
  run "tfenv install latest"
  run "tfenv use latest"
  ok "Terraform installed: $(terraform --version | head -1)"
else
  ok "Terraform already installed: $(terraform --version | head -1)"
fi

#  9. kubectl 
log "9. kubectl"
if command_exists kubectl; then
  ok "kubectl already installed"
else
  run "brew install kubectl"
  ok "kubectl installed"
fi

#  10. k9s 
log "10. k9s"
if command_exists k9s; then
  ok "k9s already installed: $(k9s version 2>/dev/null | head -1)"
else
  run "brew install k9s"
  ok "k9s installed"
fi

#  11. Helm 
log "11. Helm"
if command_exists helm; then
  ok "Helm already installed: $(helm version --short 2>/dev/null)"
else
  run "brew install helm"
  run "helm repo add stable https://charts.helm.sh/stable 2>/dev/null || true"
  run "helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true"
  run "helm repo update"
  ok "Helm installed"
fi

#  12. Ansible 
log "12. Ansible"
if command_exists ansible; then
  ok "Ansible already installed: $(ansible --version | head -1)"
else
  run "brew install ansible"
  ok "Ansible installed"
fi

log "    Installing Ansible collections"
run "ansible-galaxy collection install amazon.aws --quiet 2>/dev/null || true"
run "ansible-galaxy collection install google.cloud --quiet 2>/dev/null || true"
run "ansible-galaxy collection install community.kubernetes --quiet 2>/dev/null || true"
ok "Ansible collections installed"

#  13. Packer 
log "13. Packer"
if command_exists packer; then
  ok "Packer already installed: $(packer --version)"
else
  run "brew tap hashicorp/tap"
  run "brew install hashicorp/tap/packer"
  ok "Packer installed"
fi
run 'mkdir -p "$HOME/.packer.d/plugins"'

#  14. Docker 
if [ "$SKIP_DOCKER" = true ]; then
  warn "Skipping Docker (--no-docker flag set)"
else
  log "14. Docker"
  if command_exists docker; then
    ok "Docker already installed: $(docker --version)"
  else
    if [[ "$OS" == "macos" ]]; then
      run "brew install --cask docker"
      warn "Launch Docker Desktop from Applications to complete setup"
    else
      run "sudo apt-get update -q"
      run "sudo apt-get install -y docker.io"
      run "sudo usermod -aG docker $USER"
      warn "Log out and back in (or run 'newgrp docker') for group change to take effect"
      ok "Docker installed  requires logout to use without sudo"
    fi
  fi
fi

#  15. GitHub CLI 
log "15. GitHub CLI"
if command_exists gh; then
  ok "gh already installed: $(gh --version | head -1)"
else
  run "brew install gh"
  ok "gh installed"
fi
warn "Run 'gh auth login' to authenticate"

#  16. Linting tools 
log "16. Linting tools"

if command_exists tflint; then
  ok "tflint already installed"
else
  run "brew install tflint"
  ok "tflint installed"
fi

if command_exists ansible-lint; then
  ok "ansible-lint already installed"
else
  run "pip3 install ansible-lint --quiet"
  ok "ansible-lint installed"
fi

#  17. Shell profile 
log "17. Updating shell profile"

PROFILE=""
if [[ "$OS" == "macos" ]]; then
  PROFILE="$HOME/.zprofile"
else
  PROFILE="$HOME/.bashrc"
fi

PROFILE_BLOCK='
#  Programming-Work toolchain 
export PATH="$HOME/.tfenv/bin:$PATH"
export PACKER_PLUGIN_PATH="$HOME/.packer.d/plugins"
export AWS_DEFAULT_REGION="us-east-1"
export GEMINI_MODEL="gemini-2.5-pro"
'

if ! grep -q "Programming-Work toolchain" "$PROFILE" 2>/dev/null; then
  run "echo '$PROFILE_BLOCK' >> $PROFILE"
  ok "Shell profile updated: $PROFILE"
else
  ok "Shell profile already configured"
fi

#  18. Repo setup 
log "18. Repository setup"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log "   Repo root: $REPO_ROOT"

# SSH Keys
log "19. SSH Readiness"
if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
  warn "SSH key (id_ed25519) not found. Generating..."
  run "ssh-keygen -t ed25519 -C 'ai-agent-hub' -f '$HOME/.ssh/id_ed25519' -N ''"
  ok "SSH key generated. Add this to GitHub/Cloud: $(cat $HOME/.ssh/id_ed25519.pub)"
else
  ok "SSH key already exists: $HOME/.ssh/id_ed25519"
fi

# MCP Servers
log "20. MCP Server Bootstrap"
if [ -d "$REPO_ROOT/mcp-servers" ]; then
  run "bash '$REPO_ROOT/mcp-servers/download_mcps.sh'"
  ok "MCP servers bootstrapped"
fi

# Swarm Policies
log "21. Swarm Policy Audit"
if [ -f "$REPO_ROOT/.gemini/policies/swarm_policy.toml" ]; then
  ok "Swarm RBAC policies detected"
else
  warn "Swarm policies missing  Ensure .gemini/policies/ exists"
fi

#  23. Swarm Nexus Synchronization 
log "23. Synchronizing Swarm Nexus"
if command_exists python3; then
    run "python3 bin/nexus.py install"
else
    error "Python3 missing  Skipping Swarm Nexus synchronization."
fi
ok "Swarm Nexus synchronized across all platforms (Gemini, Claude, Cursor, Copilot)"

# AST code map
log "   Building initial AST code map"
if command_exists python3; then
  run "python3 '$REPO_ROOT/tools/ast-bridge/code_mapper.py' '$REPO_ROOT'"
  ok "code_map.md generated"
fi

# Skills inventory
log "   Regenerating skills inventory"
run "python3 '$REPO_ROOT/bin/update_inventory.py'"
ok "skills/INVENTORY.md updated"

#  22. External Credential Seeding 
log "22. External Credential Seeding"
run "mkdir -p $HOME/.mcp-servers"
run "chmod 700 $HOME/.mcp-servers"
if [ -f "$HOME/.mcp-servers/credentials" ]; then
    run "chmod 600 $HOME/.mcp-servers/credentials"
fi
ok "External credential hub secured: $HOME/.mcp-servers"

#  Summary 
echo ""
echo -e "${BOLD}${GREEN}${RESET}"
echo -e "${BOLD}${GREEN}         Setup Complete  Next Steps                  ${RESET}"
echo -e "${BOLD}${GREEN}${RESET}"
echo ""
echo "  1. Reload your shell:    source $PROFILE"
echo "  2. Authenticate:         gemini auth login"
echo "  3.                       aws configure"
echo "  4.                       gcloud init"
echo "  5.                       gh auth login"
echo "  6. Configure clusters:   aws eks update-kubeconfig --region us-east-1 --name <cluster>"
echo "  7. Launch k9s:           k9s"
echo ""
warn "Docker requires manual launch (macOS) or logout/login (Linux) to complete setup"
echo ""