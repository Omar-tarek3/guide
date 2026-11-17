variable "security_groups" {
  description = "Map of SGs to create. Key is your handle; name defaults to the key."
  type = map(object({
    name                        = optional(string)
    description                 = optional(string)
    vpc_id                      = string
    tags                        = optional(map(string), {})
    revoke_rules_on_delete      = optional(bool, true)
    allow_all_egress_when_empty = optional(bool, true)

    # Ingress rules
    ingress_rules = optional(list(object({
      description = optional(string)
      protocol    = string
      ports       = optional(list(number))
      from_port   = optional(number)
      to_port     = optional(number)

      cidr_blocks               = optional(list(string), [])
      ipv6_cidr_blocks          = optional(list(string), [])
      prefix_list_ids           = optional(list(string), [])
      source_security_group_ids = optional(list(string), [])
      source_sg_keys            = optional(list(string), [])
      self                      = optional(bool, false)
    })), [])

    # Egress rules
    egress_rules = optional(list(object({
      description = optional(string)
      protocol    = string
      ports       = optional(list(number))
      from_port   = optional(number)
      to_port     = optional(number)

      cidr_blocks                    = optional(list(string), [])
      ipv6_cidr_blocks               = optional(list(string), [])
      prefix_list_ids                = optional(list(string), [])
      destination_security_group_ids = optional(list(string), [])
      destination_sg_keys            = optional(list(string), [])
      self                           = optional(bool, false)
    })), [])
  }))
  default = {}
}

variable "default_tags" {
  type = map(string)
}
variable "prefix_name" {
  description = "Prefix for resource names"
  type        = string
}
