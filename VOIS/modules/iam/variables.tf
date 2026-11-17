# Roles input
variable "roles" {
  type = map(object({
    name                 = optional(string)
    description          = optional(string)
    tags                 = optional(map(string), {})
    path                 = optional(string)
    max_session_duration = optional(number)
    permissions_boundary = optional(string)

    # Trust: file or generated
    trust_file             = optional(string)
    trusted_services       = optional(list(string), [])
    trusted_aws_principals = optional(list(string), [])
    trusted_aws_federated  = optional(list(string), [])
    trust_action           = optional(string, "AssumeRole")
    trust_conditions       = optional(map(any), {})

    # Inline policies per role
    inline_policies     = optional(map(string), {})
    inline_policy_files = optional(map(string), {})

    # Instance profile
    instance_profile = optional(object({
      create = optional(bool, false)
      name   = optional(string)
    }), { create = false })
  }))
  default     = {}
  description = "Roles to create. Use trust_file or trusted_*."
}

# Policies input
variable "policies" {
  type = map(object({
    name        = optional(string)
    description = optional(string)
    path        = optional(string)
    tags        = optional(map(string), {})
    json        = optional(string)
    file        = optional(string)
  }))
  default     = {}
  description = "Customer-managed policies to create."
}

# Attachments input
variable "attachments" {
  type = list(object({
    role_name  = optional(string)
    role_key   = optional(string)
    policy_arn = optional(list(string))
    policy_key = optional(string)
  }))
  default     = []
  description = "Role-to-policy attachments."
}

variable "default_tags" {
  type = map(string)
}

variable "prefix_name" {
  description = "Prefix for resource names"
  type        = string
}
