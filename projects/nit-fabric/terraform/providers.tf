# nit-fabric | Industrial Provider Configuration
# Status: [HARDENED] | State Management: [REMOTE]

terraform {
  required_version = ">= 1.0.0"

  # OPERATIONAL SECURITY MANDATE: All state MUST be resident in an encrypted S3 backend
  # backend "s3" {
  #   bucket         = "nit-fabric-industrial-state"
  #   key            = "hubs/primary/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "nit-fabric-state-lock"
  # }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  alias  = "primary"
  region = "us-east-1"
}

provider "google" {
  alias   = "secondary"
  project = var.gcp_project_id
  region  = "us-central1"
}
