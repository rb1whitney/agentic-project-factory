import subprocess


def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

def get_inventory():
    print("### GCP Project Context")
    project = run_command("gcloud config get-value project")
    print(f"Active Project: {project}")

    print("\n### GKE Clusters")
    clusters = run_command("gcloud container clusters list --format='table(name,zone,status,currentMasterVersion)'")
    print(clusters)

    print("\n### Cloud Run Services")
    services = run_command("gcloud run services list --format='table(SERVICE,REGION,URL,LAST_DEPLOYED_BY)'")
    print(services)

    print("\n### Compute Engine Instances (Top 5)")
    vms = run_command("gcloud compute instances list --limit=5 "
                      "--format='table(name,zone,status,internal_ip,external_ip)'")
    print(vms)

if __name__ == "__main__":
    get_inventory()
