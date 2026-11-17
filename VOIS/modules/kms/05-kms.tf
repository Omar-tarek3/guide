# =============================================================================
# KMS Keys (created when keys_config[*].create = true or unset)
# - Uses caller-provided key policy when policy_json is set; otherwise falls
#   back to a generated default policy from data.aws_iam_policy_document.default_key_policy[*].
# - Supports Multi-Region keys and rotation, with a configurable deletion window.
# =============================================================================
resource "aws_kms_key" "this" {
  # Create a key per entry whose "create" is true (default) in keys_config
  for_each = {
    for k, v in var.keys_config : k => v
    if try(v.create, true)
  }

  # Descriptive metadata
  description = try(each.value.description, null)

  # Key type/feature flags
  multi_region            = try(each.value.multi_region, false)       # MRK primary when true
  enable_key_rotation     = try(each.value.enable_key_rotation, true) # annual rotation for symmetric keys
  deletion_window_in_days = try(each.value.deletion_window_days, 30)  # must be 7..30

  # Key policy selection
  # - If caller supplied a full policy_json, use it verbatim (advanced mode).
  # - Else, use the module's constructed default policy doc.
  policy = try(each.value.policy_json, null) != null ? each.value.policy_json : data.aws_iam_policy_document.default_key_policy[each.key].json

  # Tagging
  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${each.key}"
      Purpose = "AWS KMS Key:${var.prefix_name}-${each.key}"
    },
    each.value.tags
  )
}
