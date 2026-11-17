# =============================================================================
# Module Outputs - AWS KMS
# These outputs expose ARNs and IDs for created keys and their aliases.
# Only keys with create=true in keys_config will appear.
# =============================================================================

# Map of logical key name -> KMS Key ARN
output "key_arns" {
  description = "Map of key logical names to their AWS KMS key ARNs."
  value       = { for k, _ in aws_kms_key.this : k => aws_kms_key.this[k].arn }
}

# Map of logical key name -> KMS Key ID
output "key_ids" {
  description = "Map of key logical names to their AWS KMS key IDs."
  value       = { for k, _ in aws_kms_key.this : k => aws_kms_key.this[k].key_id }
}

# Map of logical key name -> KMS Alias ARN
output "alias_arns" {
  description = "Map of key logical names to their AWS KMS alias ARNs."
  value       = { for k, _ in aws_kms_alias.this : k => aws_kms_alias.this[k].arn }
}