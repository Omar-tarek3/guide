//==============================================================================
// irsa.tf — OIDC provider + IRSA roles (AWS-side only; no K8s SAs created)
//==============================================================================

resource "aws_iam_openid_connect_provider" "eks" {
  count           = local.create_oidc ? 1 : 0
  url             = local.oidc_issuer_url
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [local.oidc_thumbprint]
  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-eks-oidc"
      Purpose = "OIDC for cluster ${local.full_cluster_name}"
    }
  )
}

resource "aws_iam_role" "irsa_roles" {
  for_each = { for b in var.irsa_bindings : b.role_suffix => b if b.create }

  name = replace("${local.full_cluster_name}-${each.value.role_suffix}", ".", "-")

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.eks[0].arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(local.oidc_issuer_url, "https://", "")}:aud" = "sts.amazonaws.com",
          "${replace(local.oidc_issuer_url, "https://", "")}:sub" = "system:serviceaccount:${each.value.namespace}:${each.value.name}"
        }
      }
    }]
  })

  tags = merge(var.default_tags,
    {
      Purpose = "IRSA role for cluster ${local.full_cluster_name}"
    }
  )
}

# Attach AWS-managed policies when provided (policy_arns may be omitted/empty)
resource "aws_iam_role_policy_attachment" "irsa_managed_attach" {
  for_each = {
    for pair in flatten([
      for b in var.irsa_bindings : (
        b.create && length(try(b.policy_arns, [])) > 0
        ? [for idx, arn in try(b.policy_arns, []) : {
          key         = "${b.role_suffix}_${idx}"
          role_suffix = b.role_suffix
          policy_arn  = arn
        }]
        : []
      )
      ]) : pair.key => {
      role_suffix = pair.role_suffix
      policy_arn  = pair.policy_arn
    }
  }

  role       = aws_iam_role.irsa_roles[each.value.role_suffix].name
  policy_arn = each.value.policy_arn
}

# Create & attach a custom inline policy only when a non-empty path is supplied
resource "aws_iam_policy" "irsa_custom_policy" {
  for_each = {
    for b in var.irsa_bindings : b.role_suffix => b
    # try(...) returns false when custom_policy_file is null/invalid, so it's safely ignored
    if b.create && try(trimspace(b.custom_policy_file) != "", false)
  }

  name   = "${local.full_cluster_name}-${each.value.role_suffix}-custom-policy"
  policy = file("./files/irsa/${each.value.custom_policy_file}")
  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-${each.value.role_suffix}-custom-policy"
      Purpose = "IRSA policy for cluster ${local.full_cluster_name}"
    }
  )
}

resource "aws_iam_role_policy_attachment" "irsa_custom_attach" {
  for_each   = aws_iam_policy.irsa_custom_policy
  role       = aws_iam_role.irsa_roles[each.key].name
  policy_arn = each.value.arn
}
