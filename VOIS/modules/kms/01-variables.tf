# =============================================================================
# Shared / core inputs
# =============================================================================

variable "default_tags" {
  type = map(string)
}

variable "prefix_name" {
  type        = string
  description = "Prefix Name To Add To All Resources Names"
}

# =============================================================================
# KMS module variables
# - keys_config: a map of logical key names -> per-key configuration.
# - Use either `policy_json` (full custom policy) OR the high-level policy
#   builder fields (`admins`, `users_*`, `helpers`) below—if policy_json is
#   set, the builder inputs are ignored.
# =============================================================================
variable "keys_config" {
  description = "KMS keys to manage. Key = logical name."
  type = map(object({
    # Creation mode
    create               = optional(bool, true)   # false => treat as external key (do not create)
    description          = optional(string, null) # KMS key description
    multi_region         = optional(bool, false)  # Create Multi-Region primary key
    enable_key_rotation  = optional(bool, true)   # Annual rotation for symmetric keys
    deletion_window_days = optional(number, 30)   # Pending deletion window (7..30 days)
    policy_json          = optional(string, null) # Full IAM key policy JSON (overrides builder)

    # Alias
    alias_suffix = optional(string, null) # Full alias name (e.g., "alias/app/prod", "alias/eks/cluster-a")

    # ---------------------------
    # High-level policy builder
    # ---------------------------
    # Use these when you don't provide policy_json. The module can generate
    # a sensible key policy that:
    #   - grants full admin to `admins` (kms:* on key)
    #   - grants Encrypt/Decrypt/DataKey to `users_encrypt_decrypt`
    #   - grants read-only (Describe/Get*) to `users_read_only`
    admins                = optional(list(string), []) # Principals with full KMS admin
    users_encrypt_decrypt = optional(list(string), []) # Principals allowed to use the key for crypto
    users_read_only       = optional(list(string), []) # Principals with describe/list/get permissions

    # ---------------------------
    # Optional KMS Grants
    # ---------------------------
    # Fine-grained, revocable permissions issued as KMS grants (good for apps).
    grants = optional(list(object({
      grantee_principal  = string                 # IAM principal to receive the grant
      operations         = list(string)           # e.g., ["Encrypt","Decrypt","GenerateDataKey"]
      retiring_principal = optional(string, null) # Who can retire the grant (often same as grantee/app)
      constraints = optional(object({
        # Constrain grant usage (optional)
        encryption_context_equals = optional(map(string), null) # Require exact context key/values
        via_service               = optional(string, null)      # e.g., "s3.us-east-1.amazonaws.com"
      }), {})
    })), [])

    # ---------------------------
    # Opinionated helpers
    # ---------------------------
    # Convenience switches the module can translate into key-policy statements.
    # Use these to allow common AWS services to use the key with kms:ViaService
    # or to allow EKS control plane to read/write encrypted data (e.g., secrets).
    helpers = optional(object({
      eks_cluster_iam_role_arn = optional(string, null) # Let EKS control plane use this key
      allow_s3_via_service     = optional(bool, false)  # Allow S3 to use key via kms:ViaService
      allow_rds_via_service    = optional(bool, false)  # Allow RDS to use key via kms:ViaService
      allow_ebs_via_service    = optional(bool, false)  # Allow EBS (EC2) via kms:ViaService
      allow_logs_via_service   = optional(bool, false)  # Allow CloudWatch Logs via kms:ViaService
    }), {})

    # Extra tags merged onto the key/alias
    tags = optional(map(string), {})
  }))

  validation {
    condition = alltrue([
      for v in values(var.keys_config) :
      (try(v.create, true) == true) || (try(v.policy_json, null) == null)
    ])
    error_message = "When create=false (external key), policy_json must be null because this module shouldn't manage its policy."
  }

  validation {
    condition = alltrue([
      for v in values(var.keys_config) :
      (
        try(v.deletion_window_days, 30) >= 7 &&
        try(v.deletion_window_days, 30) <= 30
      )
    ])
    error_message = "deletion_window_days must be between 7 and 30 (inclusive)."
  }

  validation {
    condition = alltrue([
      for v in values(var.keys_config) : alltrue([
        for g in try(v.grants, []) : alltrue([
          for op in g.operations :
          contains([
            "Encrypt", "Decrypt", "ReEncryptFrom", "ReEncryptTo",
            "GenerateDataKey", "GenerateDataKeyWithoutPlaintext",
            "DescribeKey", "Sign", "Verify", "GetPublicKey", "CreateGrant", "RetireGrant", "ListGrants", "RevokeGrant"
          ], op)
        ])
      ])
    ])
    error_message = "Each grant.operations item must be a valid KMS grant operation."
  }
}

