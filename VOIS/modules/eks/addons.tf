//==============================================================================
// addons.tf — EKS Managed Add-ons (version-safe, idempotent)
//==============================================================================

resource "aws_eks_addon" "vpc_cni" {
  count                       = var.enable_vpc_cni ? 1 : 0
  cluster_name                = aws_eks_cluster.cluster.name
  addon_name                  = "vpc-cni"
  addon_version               = coalesce(var.vpc_cni_version, data.aws_eks_addon_version.vpc_cni.version)
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-vpc-cni"
      Purpose = "EKS Addon vpc_cni for Cluster:${local.full_cluster_name}"
    }
  )
  depends_on = [aws_eks_cluster.cluster]
}


resource "aws_eks_addon" "coredns" {
  count                       = var.enable_coredns ? 1 : 0
  cluster_name                = aws_eks_cluster.cluster.name
  addon_name                  = "coredns"
  addon_version               = coalesce(var.coredns_version, data.aws_eks_addon_version.coredns.version)
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-coredns"
      Purpose = "EKS Addon coredns for Cluster:${local.full_cluster_name}"
    }
  )
  depends_on = [aws_eks_cluster.cluster]
}

resource "aws_eks_addon" "kube_proxy" {
  count                       = var.enable_kube_proxy ? 1 : 0
  cluster_name                = aws_eks_cluster.cluster.name
  addon_name                  = "kube-proxy"
  addon_version               = coalesce(var.kube_proxy_version, data.aws_eks_addon_version.kube_proxy.version)
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-kube_proxy"
      Purpose = "EKS Addon kube_proxy for Cluster:${local.full_cluster_name}"
    }
  )
  depends_on = [aws_eks_cluster.cluster]
}

resource "aws_eks_addon" "ebs_csi_driver" {
  count         = var.enable_ebs_csi ? 1 : 0
  cluster_name  = aws_eks_cluster.cluster.name
  addon_name    = "aws-ebs-csi-driver"
  addon_version = coalesce(var.ebs_csi_version, data.aws_eks_addon_version.ebs_csi.version)

  # Optional: if provided, AWS will wire the SA to this role automatically
  service_account_role_arn = try(var.ebs_csi_irsa_role_arn, null)

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-ebs_csi_driver"
      Purpose = "EKS Addon ebs_csi_driver for Cluster:${local.full_cluster_name}"
    }
  )
  depends_on = [aws_eks_cluster.cluster]
}

