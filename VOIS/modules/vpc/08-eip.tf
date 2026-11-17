# ---------------------------------------------------------------------------
# Multi-NAT EIPs
# - Created when NAT is enabled AND single_nat_gateway is false
# - Allocates one EIP per private AZ in local.private_azs
# ---------------------------------------------------------------------------
resource "aws_eip" "nat_gw_eip" {
  for_each = var.enable_nat_gateway && !var.single_nat_gateway ? {
    for az in local.private_azs : az => az
  } : {}

  # Restrict EIP to use within VPC context (not EC2-Classic)
  domain = "vpc"

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-ngw-${each.key}"
      Purpose = "EIP for Nat Gateway ${var.prefix_name}-ngw-${each.key}"
    }
  )
}

# ---------------------------------------------------------------------------
# Single NAT EIP
# - Created when NAT is enabled AND single_nat_gateway is true
# - Allocates a single EIP for the shared NAT Gateway
# ---------------------------------------------------------------------------
resource "aws_eip" "nat_gw_eip_single" {
  count = var.enable_nat_gateway && var.single_nat_gateway ? 1 : 0

  # Restrict EIP to use within VPC context (not EC2-Classic)
  domain = "vpc"

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-ngw"
      Purpose = "EIP for Nat Gateway ${var.prefix_name}"
    }
  )
}
