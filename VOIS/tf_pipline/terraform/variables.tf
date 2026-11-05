# ===== General =====
variable "environment" {
  description = "Deployment environment: development, hypercare, production"
  type        = string
  validation {
    condition     = contains(["development", "hypercare", "production"], var.environment)
    error_message = "Environment must be development, hypercare, or production."
  }
}

variable "product" {
  description = "Product/project prefix identifier"
  type        = string
  default     = "vdf"
}

variable "azure_region" {
  description = "Azure region for deployment"
  type        = string
  default     = "westeurope"
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

# ===== Application Identity =====
variable "process_name" {
  description = "Automation/process name"
  type        = string
}

variable "shortcode" {
  description = "3-4 character application shortcode"
  type        = string
}

variable "local_market" {
  description = "Country/market code"
  type        = string
}

variable "business_vertical" {
  description = "Business unit identifier"
  type        = string
}

# ===== Function App Configuration =====
variable "function_app_name" {
  description = "Function App name to deploy. Provided via terraform.tfvars."
  type        = string
}

variable "function_runtime" {
  description = "Azure Function language runtime"
  type        = string
  default     = "node"

  validation {
    condition     = contains(["node", "python"], var.function_runtime)
    error_message = "function_runtime must be either node or python."
  }
}

variable "zone_redundancy_enabled" {
  description = "Enable zone redundancy where supported"
  type        = bool
  default     = true
}

variable "node_version" {
  description = "Node.js runtime version"
  type        = string
  default     = "22"
}

variable "python_version" {
  description = "Python runtime version"
  type        = string
  default     = "3.13"
}

variable "memory_mb" {
  description = "Function memory allocation setting"
  type        = number
  default     = 512
  validation {
    condition     = contains([512, 2048, 4096], var.memory_mb)
    error_message = "For Flex Consumption, memory_mb must be one of: 512, 2048, 4096."
  }
}

variable "timeout_seconds" {
  description = "Function timeout in seconds"
  type        = number
  default     = 900
}

variable "schedule_cron" {
  description = "Timer trigger NCRONTAB schedule expression"
  type        = string
  default     = "0 */15 * * * *"
}

variable "reserved_instances" {
  description = "Maximum concurrent function instances (0 = unlimited)"
  type        = number
  default     = 1
}

# ===== Networking =====
variable "vnet_name" {
  description = "Existing VNet name"
  type        = string
}

variable "vnet_resource_group" {
  description = "Resource group containing the existing VNet"
  type        = string
}

variable "vnet_integration_subnet_name" {
  description = "Existing subnet name for function outbound VNet integration"
  type        = string
}

variable "private_endpoint_subnet_name" {
  description = "Existing subnet name for private endpoint"
  type        = string
}

variable "private_dns_zone_name" {
  description = "Existing private DNS zone for Function Apps (for example privatelink.azurewebsites.net)"
  type        = string
}

variable "private_dns_zone_resource_group" {
  description = "Resource group containing existing private DNS zone"
  type        = string
}

variable "webjobs_storage_account_name" {
  description = "Existing shared storage account name used for AzureWebJobs storage"
  type        = string
  default     = ""
}

variable "webjobs_storage_account_resource_group" {
  description = "Resource group containing existing shared webjobs storage account"
  type        = string
  default     = ""
}

variable "process_storage_account_name" {
  description = "Existing process-specific storage account name to grant the function app Blob Data Contributor access"
  type        = string
  default     = ""
}

variable "process_storage_account_resource_group" {
  description = "Resource group containing the existing process-specific storage account"
  type        = string
  default     = ""
}

variable "log_analytics_workspace_name" {
  description = "Existing centralized Log Analytics workspace name"
  type        = string
}

variable "log_analytics_workspace_resource_group" {
  description = "Resource group containing centralized Log Analytics workspace"
  type        = string
}

variable "application_insights_name" {
  description = "Existing Application Insights resource name"
  type        = string
}

variable "application_insights_resource_group" {
  description = "Resource group containing existing Application Insights"
  type        = string
}

variable "global_key_vault_name" {
  description = "Existing global Key Vault name"
  type        = string
}

variable "global_key_vault_resource_group" {
  description = "Resource group containing global Key Vault"
  type        = string
}

variable "local_key_vault_name" {
  description = "Existing local Key Vault name"
  type        = string
}

variable "local_key_vault_resource_group" {
  description = "Resource group containing local Key Vault"
  type        = string
}

variable "global_key_vault_secret_names" {
  description = "List of global Key Vault secret names the function app can read"
  type        = list(string)
  default     = []
}

variable "local_key_vault_secret_names" {
  description = "List of local Key Vault secret names the function app can read"
  type        = list(string)
  default     = []
}

variable "local_key_vault_secret_access" {
  description = "Per-local-secret Function App identity access map (read/write)."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for access in values(var.local_key_vault_secret_access) : contains(["read", "write"], lower(access))])
    error_message = "local_key_vault_secret_access values must be read or write."
  }
}

# ===== Process Configuration =====
variable "service_name" {
  description = "Service identifier"
  type        = string
  default     = ""
}

variable "process_function" {
  description = "Function type"
  type        = string
  default     = ""
}

variable "case_limit" {
  description = "Max cases per execution"
  type        = string
  default     = "5"
}

variable "queue_name" {
  description = "UiPath work queue name"
  type        = string
  default     = ""
}

variable "short_description" {
  description = "Process short description"
  type        = string
  default     = ""
}

variable "orchestrator_environment" {
  description = "UiPath orchestrator environment"
  type        = string
  default     = "hypercare"
}

variable "process_identifier" {
  description = "Process identifier for UiPath"
  type        = string
  default     = ""
}

variable "project_name" {
  description = "Project name for UiPath"
  type        = string
  default     = ""
}

variable "process_stage" {
  description = "Process stage (loader/dispatcher/performer)"
  type        = string
  default     = "loader"
}

variable "custom_app_settings" {
  description = "Additional custom environment variables for the Function App (from FunctionAppEnvVars sheet)"
  type        = map(string)
  default     = {}
}

# ===== Tags =====
variable "confidentiality" {
  description = "Data classification tag"
  type        = string
  default     = "C3"
}

variable "managed_by" {
  description = "Owner email"
  type        = string
}

variable "project" {
  description = "Project tag"
  type        = string
  default     = "Robotics and Automation Programme"
}

variable "tagging_version" {
  description = "Tagging version"
  type        = string
  default     = "V2.4"
}
