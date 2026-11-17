resource "aws_security_group_rule" "vpce_interface_sg_rule" {
  for_each = { for k, v in local.endpoints_interface : k => v if try(v.create_security_group, false) }

  type              = "egress"
  security_group_id = aws_security_group.vpce_interface[each.key].id
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow all egress from the endpoint ENIs"
}

resource "aws_security_group_rule" "vpce_resource_sg_rule" {
  for_each = { for k, v in local.endpoints_resource : k => v if try(v.create_security_group, false) }

  type              = "egress"
  security_group_id = aws_security_group.vpce_resource[each.key].id
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow all egress from the endpoint ENIs"
}

resource "aws_security_group_rule" "vpce_sn_sg_rule" {
  for_each = { for k, v in local.endpoints_sn : k => v if try(v.create_security_group, false) }

  type              = "egress"
  security_group_id = aws_security_group.vpce_resource[each.key].id
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow all egress from the endpoint ENIs"
}

# =============================================================================
# Security Group Rules for VPC Endpoints
# =============================================================================

# ----------------------------------
# CIDR-based rules
# One resource per rule spec with a single CIDR source.
# ----------------------------------
resource "aws_security_group_rule" "vpce_rules_cidr" {
  for_each = { for s in local.sg_rule_specs_cidr : s.key => s }

  type              = each.value.type # "ingress" | "egress"
  security_group_id = each.value.sg_id
  protocol          = each.value.protocol # "tcp" | "udp" | "icmp" | "-1"
  from_port         = each.value.from_port
  to_port           = each.value.to_port
  cidr_blocks       = [each.value.cidr_block] # single CIDR per rule spec
  description       = each.value.description
}

# ----------------------------------
# Source-SG-based rules
# One resource per rule spec with a single source SG.
# ----------------------------------
resource "aws_security_group_rule" "vpce_rules_sg" {
  for_each = { for s in local.sg_rule_specs_sg : s.key => s }

  type                     = each.value.type
  security_group_id        = each.value.sg_id
  protocol                 = each.value.protocol
  from_port                = each.value.from_port
  to_port                  = each.value.to_port
  source_security_group_id = each.value.source_sg
  description              = each.value.description
}
