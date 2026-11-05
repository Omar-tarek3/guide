data "azurerm_client_config" "current" {}

data "azurerm_key_vault" "global" {
  name                = var.global_key_vault_name
  resource_group_name = var.global_key_vault_resource_group
}

data "azurerm_key_vault" "local" {
  name                = var.local_key_vault_name
  resource_group_name = var.local_key_vault_resource_group
}

locals {
  local_secret_access = merge(
    { for name in var.local_key_vault_secret_names : name => "read" },
    { for name, access in var.local_key_vault_secret_access : name => lower(access) }
  )
}

data "azurerm_key_vault_secret" "global" {
  for_each     = toset(var.global_key_vault_secret_names)
  name         = each.value
  key_vault_id = data.azurerm_key_vault.global.id
}

data "azurerm_key_vault_secret" "local" {
  for_each     = toset(keys(local.local_secret_access))
  name         = each.value
  key_vault_id = data.azurerm_key_vault.local.id
}

# RBAC: Function UAI gets read access to each configured global secret.
resource "azurerm_role_assignment" "function_global_secret_reader" {
  for_each             = data.azurerm_key_vault_secret.global
  scope                = each.value.resource_versionless_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.function.principal_id
}

# RBAC: Function UAI gets read access to each configured local secret.
resource "azurerm_role_assignment" "function_local_secret_reader" {
  for_each = {
    for secret_name, secret in data.azurerm_key_vault_secret.local :
    secret_name => secret
    if lookup(local.local_secret_access, secret_name, "read") == "read"
  }
  scope                = each.value.resource_versionless_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.function.principal_id
}

# RBAC: Function UAI gets write access to each configured local secret.
resource "azurerm_role_assignment" "function_local_secret_writer" {
  for_each = {
    for secret_name, secret in data.azurerm_key_vault_secret.local :
    secret_name => secret
    if lookup(local.local_secret_access, secret_name, "read") == "write"
  }
  scope                = each.value.resource_versionless_id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = azurerm_user_assigned_identity.function.principal_id
}
