# nit-fabric | Staff-Hardened Variable Manifest
# Status: [HARDENED] | Defensive Model: [PROACTIVE]

variable "aws_region_primary" {
  type    = string
  default = "us-east-1"
}

variable "gcp_project_id" {
  type        = string
  description = "nit-fabric Hub GCP ID"
}

variable "gcp_region_secondary" {
  type    = string
  default = "us-central1"
}

variable "vpc_cidr_aws" {
  type    = string
  default = "10.10.0.0/16"
  validation {
    condition     = can(cidrnetmask(var.vpc_cidr_aws))
    error_message = "PROACTIVE DEFENSE: Invalid CIDR string detected for AWS Hub."
  }
}

variable "vpc_cidr_gcp" {
  type    = string
  default = "10.20.0.0/16"
  validation {
    condition     = can(cidrnetmask(var.vpc_cidr_gcp))
    error_message = "PROACTIVE DEFENSE: Invalid CIDR string detected for GCP Spoke."
  }
}

variable "gcp_asn" {
  type    = number
  default = 64600
  validation {
    condition     = var.gcp_asn >= 64512 && var.gcp_asn <= 65534
    error_message = "PROACTIVE DEFENSE: Private ASN must be within 64512-65534 range."
  }
}

variable "bgp_interface_range_0" {
  type    = string
  default = "169.254.0.1/30"
  validation {
    condition     = can(cidrnetmask(var.bgp_interface_range_0))
    error_message = "PROACTIVE DEFENSE: Invalid BGP interface range."
  }
}
