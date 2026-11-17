# =============================================================================
# Default Key Policy (builder mode)
# - Built per key (for_each over keys_config where create=true)
# - If a key has policy_json set, this document is ignored by the resource.
# - Uses helpers.* toggles to add ViaService permissions for common services.
# =============================================================================
data "aws_iam_policy_document" "default_key_policy" {
  # NOTE: ensure these data sources exist in the module:
  #   data "aws_partition" "current" {}
  #   data "aws_caller_identity" "current" {}
  #   data "aws_region" "current" {}
  for_each = { for k, v in var.keys_config : k => v if try(v.create, true) }

  # --------------------------------------------------------------------------
  # AWS-required root statement: full admin to the account root
  # Keep this; it prevents lockout scenarios.
  # --------------------------------------------------------------------------
  statement {
    sid    = "EnableRootAccountAdmin"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  # --------------------------------------------------------------------------
  # Admins: callers you want to administer the key (rotate, attach policy, etc.)
  # --------------------------------------------------------------------------
  dynamic "statement" {
    for_each = length(try(each.value.admins, [])) > 0 ? [1] : []
    content {
      sid    = "KeyAdmins"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = each.value.admins
      }
      actions = [
        "kms:Create*", "kms:Describe*", "kms:Enable*", "kms:List*", "kms:Put*", "kms:Update*",
        "kms:Revoke*", "kms:Disable*", "kms:Get*", "kms:Delete*", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion"
      ]
      resources = ["*"]
    }
  }

  # --------------------------------------------------------------------------
  # Application principals allowed to *use* the key (Encrypt/Decrypt/DataKey)
  # --------------------------------------------------------------------------
  dynamic "statement" {
    for_each = length(try(each.value.users_encrypt_decrypt, [])) > 0 ? [1] : []
    content {
      sid    = "AppUsersEncryptDecrypt"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = each.value.users_encrypt_decrypt
      }
      actions   = ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"]
      resources = ["*"]
    }
  }

  # --------------------------------------------------------------------------
  # Read-only principals (typical for audit/ops tooling)
  # --------------------------------------------------------------------------
  dynamic "statement" {
    for_each = length(try(each.value.users_read_only, [])) > 0 ? [1] : []
    content {
      sid    = "ReadOnlyUsers"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = each.value.users_read_only
      }
      actions   = ["kms:DescribeKey", "kms:GetKeyPolicy", "kms:List*"]
      resources = ["*"]
    }
  }

  # --------------------------------------------------------------------------
  # Opinionated helpers — allow use *via specific AWS services*.
  # NOTE: These use principals=["*"] but restrict usage with the kms:ViaService
  # condition. If you want stricter scoping, see the hardening tip below.
  # --------------------------------------------------------------------------

  # S3 objects with SSE-KMS (service must call KMS on your behalf)
  dynamic "statement" {
    for_each = try(each.value.helpers.allow_s3_via_service, false) ? [1] : []
    content {
      sid    = "AllowUseViaS3"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = ["*"]
      }
      actions   = ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"]
      resources = ["*"]
      condition {
        test     = "StringEquals"
        variable = "kms:ViaService"
        values   = ["s3.${data.aws_region.current.name}.amazonaws.com"]
      }
    }
  }

  # RDS storage encryption (transparent to you; service uses the key)
  dynamic "statement" {
    for_each = try(each.value.helpers.allow_rds_via_service, false) ? [1] : []
    content {
      sid    = "AllowUseViaRDS"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = ["*"]
      }
      actions   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey*", "kms:DescribeKey"]
      resources = ["*"]
      condition {
        test     = "StringEquals"
        variable = "kms:ViaService"
        values   = ["rds.${data.aws_region.current.name}.amazonaws.com"]
      }
    }
  }

  # EBS (EC2) volume encryption — used by the service
  dynamic "statement" {
    for_each = try(each.value.helpers.allow_ebs_via_service, false) ? [1] : []
    content {
      sid    = "AllowUseViaEC2EBS"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = ["*"]
      }
      actions   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey*", "kms:DescribeKey"]
      resources = ["*"]
      condition {
        test     = "StringEquals"
        variable = "kms:ViaService"
        values   = ["ec2.${data.aws_region.current.name}.amazonaws.com"]
      }
    }
  }

  # CloudWatch Logs (encryption at rest for log groups)
  dynamic "statement" {
    for_each = try(each.value.helpers.allow_logs_via_service, false) ? [1] : []
    content {
      sid    = "AllowUseViaCloudWatchLogs"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = ["*"]
      }
      actions   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey*", "kms:DescribeKey"]
      resources = ["*"]
      condition {
        test     = "StringEquals"
        variable = "kms:ViaService"
        values   = ["logs.${data.aws_region.current.name}.amazonaws.com"]
      }
    }
  }

  # --------------------------------------------------------------------------
  # EKS helper: let the cluster control plane create KMS grants for AWS services
  # (required by some add-ons / data-plane features).
  # --------------------------------------------------------------------------
  dynamic "statement" {
    for_each = try(each.value.helpers.eks_cluster_iam_role_arn, null) != null ? [1] : []
    content {
      sid    = "AllowEKSControllerToCreateGrant"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = [each.value.helpers.eks_cluster_iam_role_arn]
      }
      actions   = ["kms:CreateGrant", "kms:DescribeKey"]
      resources = ["*"]
      condition {
        test     = "Bool"
        variable = "kms:GrantIsForAWSResource"
        values   = ["true"]
      }
    }
  }
}
