//==============================================================================
// eks.tf — Control plane
//==============================================================================

#Create access entries for each role (auth method to the cluster)
resource "aws_eks_access_entry" "roles" {
  for_each = var.eks_access_roles

  cluster_name      = aws_eks_cluster.cluster.name
  principal_arn     = each.value.principal_arn
  kubernetes_groups = each.value.type == "STANDARD" ? each.value.kubernetes_groups : null
  type              = each.value.type
  user_name         = each.value.user_name
}

# Attach policies to each role ONLY for STANDARD type entries that have policy_arn defined
resource "aws_eks_access_policy_association" "role_policies" {
  for_each = {
    for key, value in var.eks_access_roles : key => value
    if value.type == "STANDARD" && value.policy_arn != null
  }

  cluster_name  = aws_eks_cluster.cluster.name
  principal_arn = each.value.principal_arn
  policy_arn    = each.value.policy_arn

  access_scope {
    type = each.value.access_scope_type
  }

  depends_on = [aws_eks_access_entry.roles]
}


resource "aws_cloudwatch_log_group" "eks_cluster" {
  name              = "/aws/eks/${local.full_cluster_name}"
  retention_in_days = var.cloudwatch_log_retention_in_days
  tags              = var.default_tags
}

resource "aws_eks_cluster" "cluster" {
  name     = local.full_cluster_name
  version  = var.cluster_version
  role_arn = aws_iam_role.aws_eks_cluster_role.arn

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  vpc_config {
    subnet_ids              = var.private_subnets
    security_group_ids      = [aws_security_group.eks_cluster_control_plane_sg.id]
    endpoint_private_access = var.private_access_allowed
    endpoint_public_access  = var.public_access_enabled
    public_access_cidrs     = local.effective_public_cidrs
  }

  access_config {
    authentication_mode                         = var.authentication_mode
    bootstrap_cluster_creator_admin_permissions = var.bootstrap_cluster_creator_admin_permissions
  }

  encryption_config {
    provider { key_arn = var.eks_kms_arn }
    resources = ["secrets"]
  }

  depends_on = [
    aws_iam_role.aws_eks_cluster_role,
    aws_iam_role_policy_attachment.eks_cluster_policies,
    aws_cloudwatch_log_group.eks_cluster
  ]

  tags = merge(var.default_tags,
    {
      Name    = local.full_cluster_name
      Purpose = "EKS Cluster:${local.full_cluster_name}"
    }
  )
}
