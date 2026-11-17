//==============================================================================
// locals.tf — Derived values
//==============================================================================

locals {
  # names
  sanitized_cluster_name = replace(var.cluster_name, ".", "-")
  full_cluster_name      = "${local.sanitized_cluster_name}"

  # oidc (irsa)
  oidc_issuer_url = data.aws_eks_cluster.this.identity[0].oidc[0].issuer
  oidc_thumbprint = data.tls_certificate.oidc.certificates[0].sha1_fingerprint
  create_oidc     = length([for b in var.irsa_bindings : b if b.create]) > 0

  # tags
  common_tags = var.default_tags

  # networking
  worker_sg_ids = distinct(compact(concat(
    [aws_security_group.eks_cluster_worker_node_sg.id],
    var.SSM_SG_ID != "" ? [var.SSM_SG_ID] : [],
    var.SG_LIST
  )))

  # node groups / launch template keys
  lt_keys = { for ng in var.EKS_NODE_GROUP_DEFINITIONS :
    lower("${ng.type}-${ng.suffix}") => lower("${ng.type}-${ng.suffix}-lt")
  }

  # api exposure
  effective_public_cidrs = var.public_access_enabled ? var.public_access_cidrs : null

  # autoscaler discovery (opt-in downstream)
  autoscaler_tags = {
    "k8s.io/cluster-autoscaler/enabled"                    = "true"
    "k8s.io/cluster-autoscaler/${local.full_cluster_name}" = "owned"
  }
}
