# nit-fabric | Modular Industrial Hub
# Status: [GOLD STANDARD] | Structure: [MODULAR]

module "aws_hub" {
  source     = "./modules/aws_hub"
  vpc_cidr   = var.vpc_cidr_aws
  asn        = 64512
  subnet_ids = [aws_subnet.transit_0.id]
  
  # SENIOR SAFEGUARD: Prevent accidental hub excision
  lifecycle {
    prevent_destroy = true
  }
}

module "gcp_spoke" {
  source = "./modules/gcp_spoke"
  asn    = 64600

  lifecycle {
    prevent_destroy = true
  }
}

# Regional Transit Subnet (Algebraic IPAM)
resource "aws_subnet" "transit_0" {
  provider   = aws.primary
  vpc_id     = module.aws_hub.vpc_id # Note: Need output from module
  cidr_block = cidrsubnet(var.vpc_cidr_aws, 8, 100)
  tags       = { Name = "nit-fabric-transit-0" }
}
