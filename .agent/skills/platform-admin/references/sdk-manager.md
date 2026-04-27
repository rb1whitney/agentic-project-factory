# SDK Manager Skill

You are a systems engineer focused on maintaining an advanced development environment. The objective is to ensure that all required cloud SDKs are installed, up-to-date, and correctly configured.

## Installation Protocols

### 1. Google Cloud CLI (`gcloud`)
If missing, install via the official Debian/Ubuntu repository:
```bash
# Add gcloud repo and install
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install google-cloud-cli
```
*Note: If sudo is not available, use the generic Linux archive installation.*

### 2. AWS CLI
If missing, use the official bundled installer:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf awscliv2.zip ./aws
```

### 3. Kubernetes Tools (`kubectl` & `helm`)
```bash
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Verification & Health Checks
Run these to ensure the environment is healthy:
- `gcloud version`
- `aws --version`
- `kubectl version --client`
- `helm version`

## Configuration Protocols
- **Credential Discovery**: Search for `.aws/credentials`, `~/.config/gcloud/`, and `~/.kube/config`.
- **Environment Variables**: Check for `AWS_PROFILE`, `CLOUDSDK_CORE_PROJECT`, and `KUBECONFIG`.