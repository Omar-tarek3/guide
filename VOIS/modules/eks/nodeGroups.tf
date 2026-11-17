//==============================================================================
// nodegroups.tf — Managed node groups
//==============================================================================

resource "aws_eks_node_group" "node_group" {
  for_each = {
    for ng in var.EKS_NODE_GROUP_DEFINITIONS :
    lower("${ng.type}-${ng.suffix}") => ng
  }

  cluster_name    = aws_eks_cluster.cluster.name
  node_group_name = lower("${local.full_cluster_name}-${each.key}-eks-NodeGroup")
  node_role_arn   = aws_iam_role.aws_eks_node_role.arn

  subnet_ids     = var.private_subnets
  capacity_type  = each.value.type
  instance_types = each.value.fleet


  scaling_config {
    desired_size = each.value.desired_size
    max_size     = each.value.max_size
    min_size     = each.value.min_size
  }

  launch_template {
    id      = aws_launch_template.node_group_launch_template[lower("${each.value.type}-${each.value.suffix}")].id
    version = aws_launch_template.node_group_launch_template[lower("${each.value.type}-${each.value.suffix}")].latest_version
  }

  dynamic "taint" {
    for_each = (try(each.value.is_taint, false) && contains(keys(each.value), "taint") && each.value.taint != null) ? [each.value.taint] : []
    content {
      key    = taint.value.key
      value  = taint.value.value
      effect = taint.value.effect
    }
  }

  tags = merge(var.default_tags, {
    Name    = lower("${local.full_cluster_name}-NodeGroup")
    Purpose = "EKS ${local.full_cluster_name} ${each.value.type} Node Group"
  })

  depends_on = [
    aws_iam_role_policy_attachment.node_policies
  ]
}
