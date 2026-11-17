// =============================================================================
// PRIVATE Route Tables & Associations
// -----------------------------------------------------------------------------
resource "aws_route_table" "private" {
  for_each = var.enable_nat_gateway ? {
    for az in local.azs : az => az
  } : {}

  vpc_id = aws_vpc.this.id

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-private-${each.key}"
      Purpose = "Route Table ${var.prefix_name}-private-${each.key} For Private Subnets"
      Type    = "private"
      AZ      = each.key
    }
  )
}

resource "aws_route_table_association" "private" {
  for_each = {
    for k, s in aws_subnet.subnets :
    k => s if s.tags["Zone"] != "public" && s.tags["Zone"] != "firewall"
  }

  subnet_id = each.value.id

  # Match private subnets to their AZ-specific private route table
  route_table_id = aws_route_table.private[
    each.value.availability_zone
  ].id
}

// =============================================================================
// PUBLIC Route Tables & Associations
// -----------------------------------------------------------------------------
resource "aws_route_table" "public" {
  for_each = {
    for az in local.azs : az => az
  }

  vpc_id = aws_vpc.this.id

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-public-${each.key}"
      Purpose = "Route Table ${var.prefix_name}-public-${each.key} For Public Subnets"
      Type    = "public"
      AZ      = each.key
    }
  )
}

resource "aws_route_table_association" "public" {
  for_each = {
    for k, s in aws_subnet.subnets :
    k => s if s.tags["Zone"] == "public"
  }

  subnet_id = each.value.id

  # Match public subnets to their AZ-specific public route table
  route_table_id = aws_route_table.public[
    each.value.availability_zone
  ].id
}

// =============================================================================
// FIREWALL Route Tables & Associations
// -----------------------------------------------------------------------------
resource "aws_route_table" "firewall" {
  for_each = { for az in local.firewall_azs : az => az }

  vpc_id = aws_vpc.this.id

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-firewall-${each.key}"
      Purpose = "Route Table ${var.prefix_name}-firewall-${each.key} For Firewall Subnets"
      AZ      = each.key
      Type    = "firewall"
    }
  )

  depends_on = [aws_subnet.subnets]
}

resource "aws_route_table_association" "firewall" {
  for_each = var.enable_network_firewall ? {
    for k, s in aws_subnet.subnets : k => s if s.tags["Zone"] == "firewall"
  } : {}

  subnet_id      = each.value.id
  route_table_id = aws_route_table.firewall[each.value.availability_zone].id
}
