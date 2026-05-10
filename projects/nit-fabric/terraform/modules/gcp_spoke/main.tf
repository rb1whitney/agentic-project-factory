resource "google_compute_network" "main" {
  name                    = "nit-fabric-gcp-spoke"
  auto_create_subnetworks = false
  
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_subnetwork" "primary" {
  name          = "nit-fabric-spoke-primary"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.main.id
}

resource "google_compute_router" "hub_router" {
  name    = "nit-fabric-router"
  network = google_compute_network.main.name
  bgp {
    asn = var.asn
  }
}

resource "google_compute_vpn_gateway" "hub_vpn" {
  name    = "nit-fabric-ha-vpn"
  network = google_compute_network.main.name
}

variable "subnet_cidr" {}
variable "region" {}

variable "asn" {}
