# =============================================================================
# KMS Grants
# - One grant per entry in keys_config[*].grants (only when that key is created).
# - Grants are precise, revocable permissions for principals to use a KMS key.
# - Use for app-level access; keep broad/admin permissions in the key policy.
# =============================================================================
resource "aws_kms_grant" "this" {
  # Build a stable, unique map: "<keyName>:<idx>" => { key, grant }
  # Only create grants for keys that this module actually creates.
  for_each = {
    for p in local.kms_grant_pairs :
    p.map_key => { key = p.key, grant = p.grant }
    if p.create
  }

  # Human-friendly name (idempotency token). Optional to sanitize if you dislike ":".
  name = "${var.prefix_name}-${each.key}" # e.g., "grant-payments:0"

  # Target KMS key & grantee
  key_id            = aws_kms_key.this[each.value.key].key_id
  grantee_principal = each.value.grant.grantee_principal

  # Allowed operations for this grant, e.g. ["Encrypt","Decrypt","GenerateDataKey"]
  operations = each.value.grant.operations

  # Optional: who can retire the grant (often same as the grantee principal)
  retiring_principal = try(each.value.grant.retiring_principal, null)

  # Optional constraints — add only what’s provided
  dynamic "constraints" {
    for_each = try(each.value.grant.constraints, null) == null ? [] : [each.value.grant.constraints]
    content {
      encryption_context_equals = try(constraints.value.encryption_context_equals, null)
      encryption_context_subset = try(constraints.value.encryption_context_subset, null)
    }
  }
}