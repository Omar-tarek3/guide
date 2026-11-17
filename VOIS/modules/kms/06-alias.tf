# =============================================================================
# KMS Aliases
# - Creates one alias per managed key (create=true).
# - Current convention: alias/<Project>/<logical-key>
#   e.g., alias/myproj/payments
# =============================================================================
resource "aws_kms_alias" "this" {
  # Only alias keys this module actually created
  for_each = {
    for k, v in var.keys_config : k => v
    if try(v.create, true)
  }

  # Alias naming convention. Uses module-wide Project tag + logical key.
  # Example result: alias/prefix_name/alias_suffix/${each.key}
  name = "alias/${var.prefix_name}/kms/${each.value.alias_suffix}/${each.key}"

  # Point alias at the created CMK
  target_key_id = aws_kms_key.this[each.key].key_id
}
