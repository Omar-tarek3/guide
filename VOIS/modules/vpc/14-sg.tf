# =============================================================================
# Security Groups for VPC Endpoints
# =============================================================================

resource "aws_security_group" "vpce_interface" {
  for_each    = { for k, v in local.endpoints_interface : k => v if try(v.create_security_group, false) }
  name        = "${var.prefix_name}-vpce-intf-${each.key}"
  description = "SG for Interface VPC Endpoint ${each.key}"
  vpc_id      = aws_vpc.this.id

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-vpce-intf-${each.key}"
      Purpose = "AWS Security Group for VPC Endpoint; Type:Interface ${each.key}"
    },
    try(each.value.tags, {})
  )
}

# ----------------------------------
# SG for Resource endpoints (ARN-based PrivateLink)
# ----------------------------------
resource "aws_security_group" "vpce_resource" {
  for_each    = { for k, v in local.endpoints_resource : k => v if try(v.create_security_group, false) }
  name        = "${var.prefix_name}-vpce-res-${each.key}"
  description = "SG for Resource VPC Endpoint ${each.key}"
  vpc_id      = aws_vpc.this.id

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-vpce-res-${each.key}"
      Purpose = "AWS Security Group for VPC Endpoint; Type:Resource ${each.key}"
    },
    try(each.value.tags, {}
    )
  )
}

# ----------------------------------
# SG for ServiceNetwork endpoints (VPC Lattice)
# ----------------------------------
resource "aws_security_group" "vpce_sn" {
  for_each    = { for k, v in local.endpoints_sn : k => v if try(v.create_security_group, false) }
  name        = "${var.prefix_name}-vpce-sn-${each.key}"
  description = "SG for Service Network VPC Endpoint ${each.key}"
  vpc_id      = aws_vpc.this.id

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-vpce-sn-${each.key}"
      Purpose = "AWS Security Group for VPC Endpoint; Type:ServiceNetwork ${each.key}"
    },
    try(each.value.tags, {})
  )
}

# =============================================================================
# Locals: Collect final SG IDs per endpoint
# =============================================================================
locals {
  vpce_interface_sg_ids = {
    for k, v in local.endpoints_interface :
    k => concat(
      try(v.security_group_ids, []),
      try([aws_security_group.vpce_interface[k].id], [])
    )
  }

  vpce_resource_sg_ids = {
    for k, v in local.endpoints_resource :
    k => concat(
      try(v.security_group_ids, []),
      try([aws_security_group.vpce_resource[k].id], [])
    )
  }

  vpce_sn_sg_ids = {
    for k, v in local.endpoints_sn :
    k => concat(
      try(v.security_group_ids, []),
      try([aws_security_group.vpce_sn[k].id], [])
    )
  }
}
