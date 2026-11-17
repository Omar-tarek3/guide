// =============================================================================
// Internet Gateway (IGW)
// -----------------------------------------------------------------------------
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}"
      Purpose = "AWS Internet Gateway for ${var.prefix_name}"
    }
  )
}

// =============================================================================
// Creates one NAT Gateway (Multi-AZ) per private AZ  when:
// - NAT is enabled
// - NOT using a single shared NAT
// Provides outbound internet access for private subnets in the same AZ.
// =============================================================================
resource "aws_nat_gateway" "this" {
  for_each = var.enable_nat_gateway && !var.single_nat_gateway ? {
    for az in local.private_azs : az => az
  } : {}

  # Elastic IP allocated specifically for this NAT GW
  allocation_id = aws_eip.nat_gw_eip[each.key].id

  # NAT lives in the public subnet of the same AZ as the private subnets it serves
  subnet_id = aws_subnet.subnets["public-${each.key}"].id

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${each.key}"
      Purpose = "AWS Nat Gateway for ${var.prefix_name}-${each.key}"
    }
  )
}

// =============================================================================
// Creates a single NAT Gateway when:
// - NAT is enabled
// - single_nat_gateway is true
// Typically used for cost savings in smaller environments.
// =============================================================================
resource "aws_nat_gateway" "single" {
  count = var.enable_nat_gateway && var.single_nat_gateway ? 1 : 0

  # Elastic IP allocated for the shared NAT GW
  allocation_id = aws_eip.nat_gw_eip_single[0].id

  # Place shared NAT GW in the first public subnet
  subnet_id = element(
    [for s in aws_subnet.subnets : s.id if s.tags["Zone"] == "public"],
    0
  )

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-single"
      Purpose = "AWS Nat Gateway for ${var.prefix_name}"
    }
  )
}
