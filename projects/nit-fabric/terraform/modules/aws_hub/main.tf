resource "aws_vpc" "primary" {
  cidr_block = var.vpc_cidr
  tags       = { Name = "nit-fabric-aws-hub" }
  
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_ec2_transit_gateway" "hub" {
  amazon_side_asn = var.asn
  tags            = { Name = "nit-fabric-tgw" }
  
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "primary" {
  subnet_ids              = var.subnet_ids
  transit_gateway_id      = aws_ec2_transit_gateway.hub.id
  vpc_id                  = aws_vpc.primary.id
  appliance_mode_support  = "enable"
  
  tags = {
    Name = "nit-fabric-tgw-attachment"
    Deterministic = "true"
  }
}

variable "vpc_cidr" {}
variable "asn" {}
variable "subnet_ids" { type = list(string) }
