# Roles
output "role_names_by_key" {
  value       = { for k, r in aws_iam_role.this : k => r.name }
  description = "Role keys -> names."
}

output "role_arns_by_key" {
  value       = { for k, r in aws_iam_role.this : k => r.arn }
  description = "Role keys -> ARNs."
}

output "role_unique_ids_by_key" {
  value       = { for k, r in aws_iam_role.this : k => r.unique_id }
  description = "Role keys -> unique IDs."
}

output "role_name_to_arn" {
  value       = { for _, r in aws_iam_role.this : r.name => r.arn }
  description = "Role name -> ARN."
}

output "role_trust_sources_by_key" {
  value       = local.role_trust_sources_by_key
  description = "Role keys -> trust source (file/generated)."
}

output "role_trust_files_by_key" {
  value       = local.role_trust_files_by_key
  description = "Role keys -> trust file path (null if generated)."
}

# Instance profiles
output "instance_profile_names_by_key" {
  value       = { for k, ip in aws_iam_instance_profile.this : k => ip.name }
  description = "Role keys -> instance profile names."
}

output "instance_profile_arns_by_key" {
  value       = { for k, ip in aws_iam_instance_profile.this : k => ip.arn }
  description = "Role keys -> instance profile ARNs."
}

output "instance_profile_name_to_role_name" {
  value       = { for k, ip in aws_iam_instance_profile.this : ip.name => aws_iam_role.this[k].name }
  description = "Instance profile name -> role name."
}

# Policies
output "policy_arns_by_key" {
  value       = { for k, p in aws_iam_policy.custom : k => p.arn }
  description = "Policy keys -> ARNs."
}

output "policy_names_by_key" {
  value       = { for k, p in aws_iam_policy.custom : k => p.name }
  description = "Policy keys -> names."
}

output "policy_name_to_arn" {
  value       = { for _, p in aws_iam_policy.custom : p.name => p.arn }
  description = "Policy name -> ARN."
}

# Inline role policies
output "inline_role_policy_names_by_role_key" {
  value = {
    for rk, _ in local.role_defs :
    rk => [
      for _, spec in local.inline_role_policies : spec.name if spec.role_key == rk
    ]
  }
  description = "Role keys -> list of inline policy names."
}

# Attachments (plan-safe)
output "attachments_by_policy_key" {
  value       = local.attachments_by_policy_key
  description = "Map 'role||policyKey' -> { role_name, policy_key }."
}

output "attachments_by_policy_arn" {
  value       = local.attachments_by_policy_arn
  description = "Map 'role||policyArn' -> { role_name, policy_arn }."
}
