# Getting Started: Executive Onboarding & Environment Setup

## 0. Executive Summary: The Industrial Factory Pattern
This environment is not a standard development sandbox. It is a **Production-Grade Agentic Manufacturing Plant**. Onboarding focuses on the rapid synchronization of specialized AI workers with the underlying infrastructure.

### The 60-Second Bootstrap
For Director/Principal level review, skip the manual configuration. Execute the deterministic setup engine to align the `.agent/` hub with your local runtime:

```bash
# Sync physical hub to local spokes
bash bin/setup.sh
```

**Key Architectural Outcomes**:
- **Identity Alignment**: Synchronizes `gcloud`, `aws`, and `gh` identities across the swarm.
- **Physical Sovereignty**: Establishes the `.agent/` directory as the immutable source of truth.
- **AST Calibration**: Rebuilds the Tree-sitter symbol map for high-precision context lensing.

---

## Developer Environment Setup

This guide installs and configures...

The fastest way to set everything up is the bootstrap script. It handles all steps below automatically, skips tools already installed, and is safe to re-run at any time.

```bash
# From the repo root
bash bin/setup.sh

# Preview what it will do without executing anything
bash bin/setup.sh --dry-run

# Skip Docker (headless servers, CI machines)
bash bin/setup.sh --no-docker
```

After the script finishes, run `source ~/.zprofile` (macOS) or `source ~/.bashrc` (Linux/WSL2) to reload your shell.

> If you prefer to install tools manually or need to customize specific steps, continue with the sections below.

---

## 1. Homebrew

Homebrew is the package manager used to install nearly everything else. Install it first.

### macOS

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installation, follow the instructions to add Homebrew to your shell profile. For Apple Silicon:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### Linux / WSL2

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add to shell profile
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# Install required build dependencies
sudo apt-get install -y build-essential
```

### Verify

```bash
brew --version
# Expected: Homebrew 4.x.x
```

---

## 2. Core Shell Utilities

Install foundational utilities before language runtimes and CLIs.

```bash
brew install git curl wget jq unzip
```

---

## 3. Python 3

Several tools in this repo (`code_mapper.py`, `auto_context.py`, `graph_builder.py`) require Python 3.10 or later.

```bash
brew install python@3.11

# Verify
python3 --version
# Expected: Python 3.11.x

pip3 install --upgrade pip
```

### Python Dependencies for AST Bridge

```bash
pip3 install tree-sitter==0.20.1 tree-sitter-languages
```

> **Note**: Pin `tree-sitter` to `0.20.1`. Newer versions break the `tree-sitter-languages` binding used by the code mapper.

---

## 4. Node.js

Required for Gemini CLI and several automation tools.

```bash
brew install node

# Verify
node --version   # Expected: v20.x.x or later
npm --version
```

---

## 5. Gemini CLI

The primary AI agent interface used in this repository.

```bash
npm install -g @google/gemini-cli

# Verify
gemini --version
```

### Authenticate

```bash
gemini auth login
```

This opens a browser window. Authenticate with your Google account that has Gemini API access. The credentials are stored at `~/.gemini/credentials.json`.

### Configure Model

```bash
# Set your preferred model (edit ~/.gemini/settings.json or use CLI flags)
export GEMINI_MODEL="gemini-2.5-pro"
```

---

## 6. AWS CLI

### Install

```bash
# macOS
brew install awscli

# Linux / WSL2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Verify
aws --version
# Expected: aws-cli/2.x.x
```

### Configure

```bash
aws configure
# Provide:
#   AWS Access Key ID
#   AWS Secret Access Key
#   Default region (e.g. us-east-1)
#   Default output format: json
```

For SSO-based authentication:

```bash
aws configure sso
aws sso login --profile <profile-name>
```

### Verify

```bash
aws sts get-caller-identity
# Returns your account ID, user ARN, and user ID
```

---

## 7. Google Cloud CLI (gcloud)

### Install

```bash
brew install --cask google-cloud-sdk
```

For Linux/WSL2:

```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### Initialize and Authenticate

```bash
gcloud init

# Authenticate application default credentials (used by SDKs and tools)
gcloud auth application-default login

# Verify
gcloud --version
gcloud config list
```

### Set Default Project and Region

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
```

---

## 8. Terraform via tfenv

`tfenv` manages multiple Terraform versions. This is essential when working across projects that pin different Terraform versions.

### Install tfenv

```bash
brew install tfenv
```

For Linux/WSL2:

```bash
git clone --depth=1 https://github.com/tfutils/tfenv.git ~/.tfenv
echo 'export PATH="$HOME/.tfenv/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Install Terraform Versions

```bash
# Install latest stable
tfenv install latest
tfenv use latest

# Install a specific version (common in enterprise environments)
tfenv install 1.7.5
tfenv use 1.7.5

# Verify
terraform --version
# Expected: Terraform v1.x.x
```

### Pin Version Per Project

Create a `.terraform-version` file in any project directory to auto-switch:

```bash
echo "1.7.5" > /path/to/your/project/.terraform-version
```

---

## 9. kubectl

The Kubernetes CLI for interacting with EKS, GKE, and standard clusters.

### Install

```bash
brew install kubectl

# Verify
kubectl version --client
# Expected: Client Version: v1.29.x or later
```

### Configure Clusters

**For AWS EKS:**

```bash
aws eks update-kubeconfig --region us-east-1 --name YOUR_CLUSTER_NAME
```

**For GCP GKE:**

```bash
gcloud container clusters get-credentials YOUR_CLUSTER_NAME \
  --region us-central1 \
  --project YOUR_PROJECT_ID
```

**Verify active context:**

```bash
kubectl config current-context
kubectl cluster-info
```

---

## 10. Helm

Kubernetes package manager. Required for deploying standardized workloads.

```bash
brew install helm

# Verify
helm version
# Expected: v3.x.x

# Add common chart repositories
helm repo add stable https://charts.helm.sh/stable
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

---

## 11. Ansible

Used for configuration management and provisioning automation.

```bash
brew install ansible

# Verify
ansible --version
# Expected: ansible [core 2.x.x]
```

### Install Common Collections

```bash
ansible-galaxy collection install amazon.aws
ansible-galaxy collection install google.cloud
ansible-galaxy collection install community.kubernetes
```

---

## 12. Packer

Used for building immutable machine images for AWS AMIs and Azure VM images.

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/packer

# Verify
packer --version
# Expected: Packer v1.x.x

# Initialize plugin cache directory
export PACKER_PLUGIN_PATH="$HOME/.packer.d/plugins"
mkdir -p "$PACKER_PLUGIN_PATH"
```

---

## 13. Docker

Required for local container builds and testing.

```bash
# macOS  install Docker Desktop
brew install --cask docker

# Linux / WSL2
sudo apt-get update
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker run hello-world
```

---

## 14. GitHub CLI

Used by the `gemini-pr-creator` and `gemini-github-issue-creator` skills.

```bash
brew install gh

# Authenticate
gh auth login

# Verify
gh --version
gh auth status
```

---

## 15. k9s

k9s is a terminal UI for Kubernetes. It lets you navigate clusters, inspect pods, view logs, exec into containers, and manage resources without writing `kubectl` commands.

### Install

```bash
brew install k9s

# Verify
k9s version
# Expected: Version: v0.x.x
```

### Launch

```bash
# Connect to current kubeconfig context
k9s

# Target a specific namespace
k9s --namespace kube-system

# Target a specific kubeconfig context
k9s --context my-eks-cluster
```

### Essential Key Bindings

| Key | Action |
|---|---|
| `:` | Command mode  type resource name (pods, svc, deploy, ns) |
| `l` | View logs for selected pod |
| `s` | Shell into selected container |
| `d` | Describe selected resource |
| `ctrl-d` | Delete selected resource |
| `ctrl-k` | Kill pod |
| `f` | Port-forward selected pod |
| `/` | Filter resources by name |
| `?` | Help / keybindings |
| `esc` | Go back |
| `q` | Quit |

### Common Views

```bash
# Once inside k9s, type these after pressing ':'
pods          # All pods
svc           # Services
deploy        # Deployments
ing           # Ingresses
cm            # ConfigMaps
secret        # Secrets (values hidden by default)
ns            # Namespaces
node          # Cluster nodes
pv            # Persistent volumes
hpa           # Horizontal pod autoscalers
ctx           # Switch context
```

### Config File

k9s config lives at `~/.config/k9s/config.yaml`. Key settings:

```yaml
k9s:
  refreshRate: 2          # seconds between refreshes
  maxConnRetry: 5
  readOnly: false         # set true to prevent accidental deletes
  noExitOnCtrlC: false
  ui:
    enableMouse: true
    headless: false
    logoless: false
    crumbsless: false
    reactive: false
    noIcons: false
  skipLatestRevCheck: false
  shellPod:
    image: busybox
    namespace: default
    limits:
      cpu: 100m
      memory: 100Mi
```

---

## 16. Verify Full Environment

Run this block to confirm all critical tools are installed and on your PATH:

```bash
echo "=== Core ===" && \
  brew --version && \
  python3 --version && \
  node --version && \
  git --version && \
  jq --version

echo "=== AI Tools ===" && \
  gemini --version

echo "=== Cloud CLIs ===" && \
  aws --version && \
  gcloud --version | head -1 && \
  kubectl version --client --short 2>/dev/null || kubectl version --client

echo "=== IaC ===" && \
  terraform --version | head -1 && \
  packer --version && \
  helm version --short && \
  ansible --version | head -1

echo "=== Containers & K8s ===" && \
  docker --version && \
  k9s version

echo "=== Utilities ===" && \
  gh --version | head -1
```

---

## 16. Shell Profile Summary

Add the following block to your `~/.zprofile` (macOS) or `~/.bashrc` (Linux/WSL2) to ensure all tools are available in new sessions:

```bash
# Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"          # macOS Apple Silicon
# eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"  # Linux/WSL2

# tfenv
export PATH="$HOME/.tfenv/bin:$PATH"

# Packer plugin cache
export PACKER_PLUGIN_PATH="$HOME/.packer.d/plugins"

# AWS default region (override per project)
export AWS_DEFAULT_REGION="us-east-1"

# gcloud
source "$(brew --prefix)/share/google-cloud-sdk/path.bash.inc"
source "$(brew --prefix)/share/google-cloud-sdk/completion.bash.inc"

# Gemini model preference
export GEMINI_MODEL="gemini-2.5-pro"
```

---

## 17. Repository-Specific Setup

After the environment is ready, initialize the repository tools:

```bash
# Clone the repo (if not already)
cd /path/to/Programming-Work

# Build the initial AST code map
python3 tools/ast-bridge/code_mapper.py .

# Verify skills are available
ls skills/

# Confirm Gemini sees the skills
gemini --help
```

---

## Troubleshooting

### Homebrew not found after install

```bash
# macOS Apple Silicon
eval "$(/opt/homebrew/bin/brew shellenv)"

# Linux / WSL2
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

### tfenv not switching versions

```bash
# Ensure tfenv shim is before system terraform in PATH
which terraform
# Should show: /usr/local/bin/tfenv/shims/terraform or ~/.tfenv/bin
tfenv list
```

### gcloud auth errors in CI or non-interactive environments

```bash
# Use service account key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
```

### AWS credential conflicts between CLI and SDK

```bash
# Check active profile
aws configure list
aws sts get-caller-identity

# Use explicit profile
export AWS_PROFILE=my-profile
```

### tree-sitter import errors in Python

```bash
# Must use exact pinned versions
pip3 uninstall tree-sitter tree-sitter-languages
pip3 install tree-sitter==0.20.1 tree-sitter-languages
```