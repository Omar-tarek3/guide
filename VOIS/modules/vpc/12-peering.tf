# =============================================================================
# Creates VPC peering connections from THIS VPC to one or more peer VPCs.
# =============================================================================
resource "aws_vpc_peering_connection" "this" {
  for_each = local.peerings_by_name

  vpc_id        = aws_vpc.this.id
  peer_vpc_id   = each.value.peer_vpc_id
  peer_owner_id = try(each.value.peer_owner_id, null) # needed for cross-account
  peer_region   = try(each.value.peer_region, null)   # required for cross-region
  auto_accept   = try(each.value.auto_accept, false)  # true only if same account/region

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${each.value.name}"
      Purpose = "VPC Peering between ${aws_vpc.this.id} and ${each.value.peer_vpc_id}"
    }
  )
}

# =============================================================================
# Adds routes into THIS VPC's route tables to reach the peer VPC CIDRs.
# =============================================================================
resource "aws_route" "peer_routes" {
  for_each                  = var.first_run ? {} : { for s in local.peering_route_specs : s.key => s }
  route_table_id            = each.value.rt_id
  destination_cidr_block    = each.value.dest_cidr
  vpc_peering_connection_id = aws_vpc_peering_connection.this[each.value.peering].id
}