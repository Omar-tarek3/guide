terraform {
  required_version = ">= 1.5.0"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}

resource "aws_security_group" "this" {
  for_each               = local.sg_defs
  name                   = "${var.prefix_name}-${each.value.name}"
  description            = each.value.description
  vpc_id                 = each.value.vpc_id
  revoke_rules_on_delete = each.value.revoke_rules_on_delete
  tags = merge(
    var.default_tags,
    each.value.tags,
    {
      Name    = "${var.prefix_name}-${each.value.name}"
      Purpose = "This security group for ${each.value.name}"
    }
  )
}

resource "aws_security_group_rule" "ingress" {
  for_each          = { for r in local.ingress_expanded : r._key => r }
  type              = "ingress"
  security_group_id = aws_security_group.this[each.value._sg_key].id

  description = try(each.value.description, null)
  protocol    = each.value.protocol
  from_port   = each.value.from_port
  to_port     = each.value.to_port

  cidr_blocks      = length(try(each.value.cidr_blocks, [])) > 0 ? each.value.cidr_blocks : null
  ipv6_cidr_blocks = length(try(each.value.ipv6_cidr_blocks, [])) > 0 ? each.value.ipv6_cidr_blocks : null
  prefix_list_ids  = length(try(each.value.prefix_list_ids, [])) > 0 ? each.value.prefix_list_ids : null
  self             = try(each.value.self, false) ? true : null

  source_security_group_id = each.value._src_sg
}

resource "aws_security_group_rule" "egress" {
  for_each          = { for r in local.egress_expanded : r._key => r }
  type              = "egress"
  security_group_id = aws_security_group.this[each.value._sg_key].id

  description = try(each.value.description, null)
  protocol    = each.value.protocol
  from_port   = each.value.from_port
  to_port     = each.value.to_port

  cidr_blocks      = length(try(each.value.cidr_blocks, [])) > 0 ? each.value.cidr_blocks : null
  ipv6_cidr_blocks = length(try(each.value.ipv6_cidr_blocks, [])) > 0 ? each.value.ipv6_cidr_blocks : null
  prefix_list_ids  = length(try(each.value.prefix_list_ids, [])) > 0 ? each.value.prefix_list_ids : null
  self             = try(each.value.self, false) ? true : null

  source_security_group_id = each.value._dst_sg
}

resource "aws_security_group_rule" "egress_all_when_empty" {
  for_each          = local.egress_all_when_empty
  type              = "egress"
  security_group_id = aws_security_group.this[each.key].id
  description       = "Allow all egress"
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
}
