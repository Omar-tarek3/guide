resource "aws_subnet" "subnets" {
  for_each = {
    for s in local.subnet_definitions :
    "${s.zone}-${s.az}" => s
  }

  vpc_id = aws_vpc.this.id

  availability_zone = each.value.az

  cidr_block = each.value.cidr_block

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${each.value.zone}-${each.value.az}"
      Purpose = "${var.prefix_name}-${each.value.zone}-${each.value.az} Subnet"
      Zone    = each.value.zone
    },
    contains(
      lookup(var.karpenter_config, "karpenter_zones", []),
      each.value.zone
    )
    ? {
      # Advertise subnets to Karpenter by cluster name (if configured)
      "karpenter.sh/discovery" = lookup(var.karpenter_config, "cluster_name", "")
    }
    : {},
    each.value.tags
  )
}
