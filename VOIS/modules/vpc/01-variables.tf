
variable "cidr_block" {
  description = "VPC CIDR, e.g., 10.0.0.0/16"
  type        = string
}

variable "az_count" {
  description = "How many Availability Zones to span (for validation/reference)"
  type        = number
}


variable "prefix_name" {
  description = "Prefix that will be prepended to most resource names"
  type        = string
}

# -------------------------------------------------------------------------
# NAT strategy
# -------------------------------------------------------------------------
variable "enable_nat_gateway" {
  description = "Whether to enable NAT Gateway for the VPCs"
  type        = bool
}

variable "single_nat_gateway" {
  description = "Whether to use a single NAT Gateway instead of one per AZ"
  type        = bool
}

# =============================================================================
# AWS Network Firewall - Enable Configuration
# =============================================================================
variable "enable_network_firewall" {
  description = "Enable AWS Network Firewall for VPCs"
  type        = bool
  default     = false
}

variable "firewall_name" {
  description = "AWS Network Firewall name"
  type        = string
  default     = ""
}

variable "firewall_policy_arn" {
  description = "AWS Network Firewall policy ARN"
  type        = string
  default     = ""
}
# =============================================================================
# Karpenter Configuration Variable
# =============================================================================
variable "karpenter_config" {
  description = "Karpenter hints configuration for EKS node provisioning"
  type = object({
    cluster_name    = optional(string)
    karpenter_zones = optional(list(string))
  })
  default = null
}


# =============================================================================
# VPC Flow Log Configuration Variable
# =============================================================================
variable "flow_log" {
  description = "VPC Flow Log configuration"
  type = object({
    log_destination               = optional(string)
    log_destination_type          = optional(string, "s3")
    traffic_type                  = optional(string, "ALL")
    eni_id                        = optional(string)
    iam_role_arn                  = optional(string)
    subnet_id                     = optional(string)
    transit_gateway_id            = optional(string)
    transit_gateway_attachment_id = optional(string)
    log_format                    = optional(string)
    max_aggregation_interval      = optional(number, 600)
    tags                          = optional(map(string))
  })
}

# =============================================================================
# VPC Peering Configuration Variable
# =============================================================================
variable "peerings" {
  description = "VPC Peering connections configuration"
  type = map(object({
    # ---- Peering connection details ----
    name          = string                 # Logical key for this peering
    peer_vpc_id   = string                 # Target peer VPC ID
    peer_owner_id = optional(string, null) # Cross-account owner (required if different account)
    peer_region   = optional(string, null) # Cross-region peering
    auto_accept   = optional(bool, false)  # Only possible same-account/region
    tags          = optional(map(string), {})

    # ---- Optional routing instructions (for THIS VPC side) ----
    routes = optional(list(object({
      route_table_identifier = list(string) # Which local RTBs to update (logical keys)
      destination_cidr_block = string       # Peer VPC or subnet CIDR
    })), [])
  }))
  default = {}
}

# =============================================================================
# VPC Endpoints Configuration Variable
# =============================================================================
variable "endpoints" {
  description = "VPC Endpoints configuration (Interface / Gateway / GWLB / Resource / ServiceNetwork)"
  type = map(object({
    type = string
    tags = optional(map(string), {})

    # ---- Interface / Gateway / GWLB ----
    service        = optional(string, null) # e.g., "com.amazonaws.us-east-1.ecr.api" or "s3"/"dynamodb"
    service_region = optional(string, null) # For cross-region endpoint services

    # ---- Resource endpoint ----
    resource_configuration_arn = optional(string, null)

    # ---- ServiceNetwork (VPC Lattice) ----
    service_network_arn = optional(string, null)

    # ---- Network placement ----
    subnet_identifiers      = optional(list(string), []) # Interface/GWLB/Resource/ServiceNetwork
    route_table_identifiers = optional(list(string), []) # Gateway (logical: "private", "public", "firewall")

    # ---- Security / DNS / Policy ----
    security_group_ids    = optional(list(string), [])
    create_security_group = optional(bool, false)
    private_dns_enabled   = optional(bool, true)
    policy                = optional(string, null)

    # ---- Optional SG rules for auto-created SG ----
    sg_rules = optional(list(object({
      type                      = string
      from_port                 = number
      to_port                   = number
      protocol                  = string
      description               = optional(string, "")
      cidr_blocks               = optional(list(string), [])
      source_security_group_ids = optional(list(string), [])
    })), [])
  }))
  default = {}
}

# =============================================================================
# Variable: custom_subnet_config
# -----------------------------------------------------------------------------
variable "custom_subnet_config" {
  description = "Map of subnet definitions with explicit CIDR blocks and AZ placement"
  type = map(object({
    cidr_block = string                    # Exact subnet CIDR, e.g., "10.0.1.0/24"
    az         = string                    # AZ identifier, e.g., "eu-west-1a"
    zone       = string                    # Logical zone/tier (e.g., "public" | "private" | "db" | "firewall")
    tags       = optional(map(string), {}) # tag to add to each subnet zone
  }))

}

variable "default_tags" {
  type = map(string)
}


variable "first_run" {
  type = bool
}

###############################################################################
# managed-prefix-list
###############################################################################
variable "prefix_lists" {
  description = "Map of prefix lists to create. Key is the prefix list name."
  type = map(object({
    address_family = string
    max_entries    = optional(number)
    description    = optional(string, "")
    entries = map(object({
      cidr        = string
      description = optional(string, "")
    }))
    tags = optional(map(string), {})
  }))
  default = {}
}