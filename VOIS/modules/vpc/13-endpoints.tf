# ================================================
# Interface Endpoints (AWS PrivateLink: ENI-based)
# ================================================
resource "aws_vpc_endpoint" "interface" {
  for_each = local.endpoints_interface

  vpc_id            = aws_vpc.this.id
  vpc_endpoint_type = "Interface"

  service_name        = each.value.service
  service_region      = try(each.value.service_region, null) # for cross‑region endpoint services
  subnet_ids          = local.endpoint_subnet_ids_interface[each.key]
  security_group_ids  = local.vpce_interface_sg_ids[each.key] # per-endpoint SGs (created/collected in locals)
  private_dns_enabled = try(each.value.private_dns_enabled, true)

  policy = try(each.value.policy, null) # optional IAM policy JSON to restrict access

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${each.key}"
      Purpose = "AWS VPC Endpoint: Interface, for ${each.value.service}"
    },
    try(each.value.tags, {})
  )
}

# ================================================
# Gateway Endpoints (S3 / DynamoDB)
# ================================================
resource "aws_vpc_endpoint" "gateway" {
  for_each = local.endpoints_gateway

  vpc_id            = aws_vpc.this.id
  vpc_endpoint_type = "Gateway"

  # Shorthand → full service name
  service_name = contains(["s3", "dynamodb"], lower(each.value.service)) ? "com.amazonaws.${data.aws_region.current.id}.${lower(each.value.service)}" : each.value.service

  route_table_ids = local.endpoint_route_table_ids[each.key] # RTBs to attach (public/private/etc.)
  policy          = try(each.value.policy, null)             # optional policy to restrict access
  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${each.key}"
      Purpose = "AWS VPC Endpoint: Endpoint, for ${each.value.service}"
    },
    try(each.value.tags, {})
  )
}

# ================================================
# Gateway Load Balancer Endpoints (GWLB)
# ================================================
resource "aws_vpc_endpoint" "gwlb" {
  for_each = local.endpoints_gwlb

  vpc_id            = aws_vpc.this.id
  vpc_endpoint_type = "GatewayLoadBalancer"

  service_name   = each.value.service
  service_region = try(each.value.service_region, null) # for cross‑region GWLB services
  subnet_ids     = local.endpoint_subnet_ids_gwlb[each.key]

  # No SGs / policy / private DNS for GWLB endpoints
  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${each.key}"
      Purpose = "AWS VPC Endpoint: GatewayLoadBalancer, for ${each.value.service}"
    },
    try(each.value.tags, {})
  )
}

# ================================================
# Resource Endpoints (PrivateLink: ARN-based)
# ================================================
resource "aws_vpc_endpoint" "resource" {
  for_each = local.endpoints_resource

  vpc_id            = aws_vpc.this.id
  vpc_endpoint_type = "Resource"

  resource_configuration_arn = each.value.resource_configuration_arn

  subnet_ids          = local.endpoint_subnet_ids_resource[each.key]
  security_group_ids  = local.vpce_resource_sg_ids[each.key]
  private_dns_enabled = try(each.value.private_dns_enabled, false)

  # No 'policy' block for Resource endpoints
  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${each.key}"
      Purpose = "AWS VPC Endpoint: Resource, for ${each.value.service}"
    },
    try(each.value.tags, {})
  )
}

# ================================================
# Service Network Endpoints (VPC Lattice)
# ================================================
resource "aws_vpc_endpoint" "service_network" {
  for_each = local.endpoints_sn

  vpc_id            = aws_vpc.this.id
  vpc_endpoint_type = "ServiceNetwork"

  service_network_arn = each.value.service_network_arn

  subnet_ids         = local.endpoint_subnet_ids_sn[each.key]
  security_group_ids = local.vpce_sn_sg_ids[each.key]

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${each.key}"
      Purpose = "AWS VPC Endpoint: ServiceNetwork, for ${each.value.service}"
    },
    try(each.value.tags, {}
    )
  )
}
