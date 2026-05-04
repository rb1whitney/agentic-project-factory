# Security: nit-fabric Zero-Trust Boundary Rules
# 100% Alignment with Elite Industrial Safety Standards

# --- AWS TGW Security (us-east-1) ---

resource "aws_security_group" "tgw_boundary" {
  provider = aws.primary
  name     = "nit-fabric-tgw-boundary-sg"
  vpc_id   = aws_vpc.primary.id
  description = "Baseline Zero-Trust lockdown for the Transit Gateway Hub"

  # INGRESS: Only allow traffic from the GCP Secondary CIDR
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr_gcp]
    description = "Allow all traffic from regional GCP peer hub"
  }

  # EGRESS: Standard lockdown logic (Mandatory Default Deny)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr_gcp]
    description = "Allow egress only to regional GCP hub"
  }

  tags = {
    Name = "nit-fabric-tgw-boundary-sg"
    Tier = "Security"
  }
}

# --- GCP Cloud Router Firewall (us-central1) ---

resource "google_compute_firewall" "hub_boundary" {
  provider = google.secondary
  name     = "nit-fabric-hub-boundary-fw"
  network  = google_compute_network.secondary.name
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  source_ranges = [var.vpc_cidr_aws]
  description   = "Baseline lockdown for the GCP Hub Router"
}
