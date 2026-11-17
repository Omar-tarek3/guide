//--------------------------------------------------------------------------------
// variables.tf — Inputs for the EKS module
//--------------------------------------------------------------------------------

#-----------------------------------------------------------
# Core cluster inputs
#-----------------------------------------------------------

variable "prefix_name" {
  description = "Prefix for the EKS cluster name (prepended to sanitized cluster_name)"
  type        = string
}
variable "cluster_name" {
  description = "Base name for the EKS cluster; sanitized to letters/numbers/dashes for AWS"
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS control plane (e.g., 1.29)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the control plane ENIs and worker nodes live"
  type        = string
}


variable "private_subnets" {
  description = "List of private subnet IDs where worker node groups will be created"
  type        = list(string)
}

variable "authentication_mode" {
  description = "Authentication mode to use with the cluster"
  default     = "CONFIG_MAP"
  type        = string
}

variable "bootstrap_cluster_creator_admin_permissions" {
  description = "Should cluster creator be granted Admin? "
  default     = true
  type        = bool
}


variable "eks_access_roles" {
  description = "Map of EKS access roles configuration"
  type = map(object({
    principal_arn     = string
    kubernetes_groups = optional(list(string), [])
    policy_arn        = optional(string, "")
    access_scope_type = optional(string, "cluster")
    type              = optional(string, "STANDARD")
    user_name         = optional(string)
  }))
  default = {}
}

#-----------------------------------------------------------
# API endpoint exposure (private/public)
#-----------------------------------------------------------

variable "private_access_allowed" {
  description = "Allow private access to the EKS API endpoint (from within the VPC)"
  type        = bool
  default     = true
}

variable "public_access_enabled" {
  description = "Enable public (internet) access to the EKS API endpoint"
  type        = bool
  default     = false # safer default for production
}

variable "public_access_cidrs" {
  description = <<EOF
CIDR blocks allowed to reach the EKS API endpoint when public access is enabled.
Ignored if public_access_enabled = false. Use restricted office/VPN CIDRs in prod.
EOF
  type        = list(string)
  default     = ["0.0.0.0/32"] # effectively blocks access unless overridden

  validation {
    condition     = length(var.public_access_cidrs) > 0
    error_message = "public_access_cidrs must contain at least one CIDR (use a specific range, not empty)."
  }
}

#-----------------------------------------------------------
# Logging & encryption
#-----------------------------------------------------------

variable "cloudwatch_log_retention_in_days" {
  description = "Retention (days) for the control plane CloudWatch log group"
  type        = number
  default     = 30
}

variable "eks_kms_arn" {
  description = "KMS key ARN used to encrypt Kubernetes secrets at rest"
  type        = string
}

#-----------------------------------------------------------
# Global tagging
#-----------------------------------------------------------

variable "default_tags" {
  description = "Default tags applied to all resources in this module"
  type        = map(string)
  default     = {}
}

#-----------------------------------------------------------
# Security group extras (optional)
#-----------------------------------------------------------

variable "SSM_SG_ID" {
  description = "Optional Security Group ID that enables SSM Session Manager on worker nodes"
  type        = string
  default     = ""
}

variable "SG_LIST" {
  description = "Additional Security Group IDs to attach to worker nodes (in addition to the worker SG + optional SSM SG)"
  type        = list(string)
  default     = []
}

# Extra, user-defined worker SG rules hook
variable "extra_worker_sg_rules" {
  description = <<EOF
Optional list of extra SG rules for worker nodes. Each item can specify either cidr_blocks or source SGs.
Example:
extra_worker_sg_rules = [
  { type = "ingress", from_port = 31000, to_port = 31000, protocol = "tcp", cidr_blocks = ["10.0.0.0/8"], description = "allow nodeport 31000 from corp" }
]
EOF
  type = list(object({
    type             = string # "ingress" | "egress"
    from_port        = number
    to_port          = number
    protocol         = string # "tcp" | "udp" | "-1"
    cidr_blocks      = optional(list(string))
    ipv6_cidr_blocks = optional(list(string))
    security_groups  = optional(list(string)) # source SGs (first one used)
    description      = optional(string)
  }))
  default = []
}

#-----------------------------------------------------------
# IRSA (AWS-side only; you create the K8s ServiceAccounts yourself)
#-----------------------------------------------------------

variable "irsa_bindings" {
  description = <<EOF
List of IRSA bindings to create on AWS side:
- name:          Kubernetes ServiceAccount name (cluster-side; not created here)
- namespace:     K8s namespace of the ServiceAccount
- role_suffix:   Suffix appended to sanitized cluster_name to form IAM role name
- policy_arns:   AWS-managed policy ARNs to attach to the role
- custom_policy_file: (optional) JSON file under ./policies to create & attach a custom policy
- create:        Whether to create this binding
EOF
  type = list(object({
    name               = string
    namespace          = string
    role_suffix        = string
    policy_arns        = optional(list(string), [])
    custom_policy_file = optional(string)
    create             = bool
  }))

  # Pre-provision EBS & EFS CSI controller IRSA roles by default (you will create the SAs in the cluster)
  default = [
    {
      name               = "ebs-csi-controller"
      namespace          = "kube-system"
      role_suffix        = "ebs-csi-controller"
      policy_arns        = ["arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"]
      custom_policy_file = null
      create             = true
    },
    {
      name               = "efs-csi-controller-sa"
      namespace          = "kube-system"
      role_suffix        = "efs-csi-controller"
      policy_arns        = ["arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy"]
      custom_policy_file = null
      create             = true
    }
  ]
}

#-----------------------------------------------------------
# Managed add-ons (enable toggles + optional version pins)
#-----------------------------------------------------------

variable "enable_vpc_cni" {
  description = "Install/Manage the Amazon VPC CNI plugin as an EKS managed add-on"
  type        = bool
  default     = true
}

variable "vpc_cni_version" {
  description = "Version to install for the VPC CNI add-on (e.g., v1.16.4-eksbuild.1). Use null to let AWS choose a compatible version."
  type        = string
  default     = null
}

variable "enable_coredns" {
  description = "Install/Manage CoreDNS as an EKS managed add-on"
  type        = bool
  default     = true
}

variable "coredns_version" {
  description = "Version to install for CoreDNS add-on (e.g., v1.11.1-eksbuild.2). Use null to let AWS choose."
  type        = string
  default     = null
}

variable "enable_kube_proxy" {
  description = "Install/Manage kube-proxy as an EKS managed add-on"
  type        = bool
  default     = true
}

variable "kube_proxy_version" {
  description = "Version to install for kube-proxy add-on (e.g., v1.29.3-eksbuild.2). Use null to let AWS choose."
  type        = string
  default     = null
}

variable "enable_ebs_csi" {
  description = "Install/Manage the AWS EBS CSI driver as an EKS managed add-on"
  type        = bool
  default     = true
}

variable "ebs_csi_version" {
  description = "Version to install for the EBS CSI add-on (e.g., v1.30.0-eksbuild.1). Use null to let AWS choose."
  type        = string
  default     = null
}


variable "ebs_csi_irsa_role_arn" {
  description = <<EOF
Optional IRSA role ARN to attach to the EBS CSI controller ServiceAccount via the managed add-on.
If null, the add-on installs without IRSA attached (controller will use node role or you can annotate SA manually).
EOF
  type        = string
  default     = null
}

#-----------------------------------------------------------
# Node group definitions
#-----------------------------------------------------------

variable "EKS_NODE_GROUP_DEFINITIONS" {
  description = <<EOF
List of node-group specs. Each object defines:
- type             = string (capacity type: 'ON_DEMAND' | 'SPOT')
- suffix           = string (e.g., 'app', 'batch')
- fleet            = list(string) (instance types)
- ami              = string (AMI ID to use; ensure it's compatible with your EKS version/region)
- root_volume_size =  optional(number, 50)
-  encrypted        = optional(bool, true)
-  delete_on_termination = optional(bool, true) 
-  volume_type =  optional(string, "gp3")
- desired_size     = number
- max_size         = number
- min_size         = number
- is_taint         = bool
- taint            = optional({ key, value, effect })
EOF
  type = list(object({
    type                  = string
    suffix                = string
    fleet                 = list(string)
    ami                   = string
    root_volume_size      = optional(number, 40)
    encrypted             = optional(bool, true)
    delete_on_termination = optional(bool, true)
    volume_type           = optional(string, "gp3")
    device_name           = optional(string, "/dev/xvda")
    desired_size          = number
    max_size              = number
    min_size              = number
    is_taint              = bool
    taint = optional(object({
      key    = string
      value  = string
      effect = string # "NO_SCHEDULE" | "NO_EXECUTE" | "PREFER_NO_SCHEDULE"
    }))
  }))

  default = []
}
