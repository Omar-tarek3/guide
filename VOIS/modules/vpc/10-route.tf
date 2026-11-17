// =============================================================================
// Route: private_to_internet
// -----------------------------------------------------------------------------
resource "aws_route" "private_to_internet" {
  for_each = var.enable_nat_gateway ? {
    for az in local.private_azs : az => az
  } : {}

  route_table_id         = aws_route_table.private[each.key].id
  destination_cidr_block = "0.0.0.0/0"

  # NAT path when NF is disabled
  nat_gateway_id = !var.enable_network_firewall ? (
    var.single_nat_gateway
    ? aws_nat_gateway.single[0].id
    : aws_nat_gateway.this[each.key].id
  ) : null

  # NF path when enabled: send traffic to firewall endpoint in same AZ
  vpc_endpoint_id = var.enable_network_firewall ? lookup(local.firewall_endpoints_by_az, each.key, null) : null
}

// =============================================================================
// Route: public_to_internet
// -----------------------------------------------------------------------------

resource "aws_route" "public_to_internet" {
  for_each = aws_route_table.public

  route_table_id         = each.value.id
  destination_cidr_block = "0.0.0.0/0"

  # Direct IGW route (NF bypass for public subnets)
  gateway_id = aws_internet_gateway.this.id
}

// =============================================================================
// Route: firewall_to_internet
// -----------------------------------------------------------------------------

resource "aws_route" "firewall_to_internet" {
  for_each = var.enable_network_firewall ? aws_route_table.firewall : {}

  route_table_id         = each.value.id
  destination_cidr_block = "0.0.0.0/0"

  # NAT path after firewall inspection
  nat_gateway_id = var.single_nat_gateway ? aws_nat_gateway.single[0].id : aws_nat_gateway.this[each.key].id
}

// =============================================================================
// Route: Internet Back Through NF(If Enabled)
// =============================================================================
# resource "aws_route" "public_return_path_via_nfw" {
#   for_each = var.enable_network_firewall ? {
#     for k, s in aws_subnet.subnets :
#     "${s.availability_zone}:${s.cidr_block}" => {
#       az   = s.availability_zone
#       cidr = s.cidr_block
#     }
#     if try(s.tags["Zone"], "") != "public" && try(s.tags["Zone"], "") != "firewall"
#   } : {}

#   # Public/NAT route table for that AZ
#   route_table_id         = local.public_rtb_by_az[each.value.az]

#   # More-specific route beats the implicit "local" VPC route
#   destination_cidr_block = each.value.cidr

#   # Steer via the AZ-local Network Firewall endpoint
#   vpc_endpoint_id        = local.nfw_endpoints_by_az[each.value.az]

#   depends_on = [aws_networkfirewall_firewall.this]
# }