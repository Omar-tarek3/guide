data "azurerm_storage_account" "webjobs" {
  name                = var.webjobs_storage_account_name
  resource_group_name = var.webjobs_storage_account_resource_group
}

locals {
  process_storage_enabled = var.process_storage_account_name != "" ? { process = true } : {}
}

resource "azurerm_storage_container" "webjobs_container" {
  name                  = lower(replace("azure-webjobs-${var.process_name}", "_", "-"))
  storage_account_id    = data.azurerm_storage_account.webjobs.id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "function_webjobs_storage_queue_contributor" {
  scope                = data.azurerm_storage_account.webjobs.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_user_assigned_identity.function.principal_id
}

resource "azurerm_role_assignment" "function_webjobs_storage_blob_owner" {
  scope                = data.azurerm_storage_account.webjobs.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = azurerm_user_assigned_identity.function.principal_id
}

data "azurerm_storage_account" "process" {
  for_each            = local.process_storage_enabled
  name                = var.process_storage_account_name
  resource_group_name = var.process_storage_account_resource_group
}

resource "azurerm_role_assignment" "function_process_storage_blob_contributor" {
  for_each             = local.process_storage_enabled
  scope                = data.azurerm_storage_account.process[each.key].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.function.principal_id
}

locals {
  webjobs_storage_blob_service_uri      = data.azurerm_storage_account.webjobs.primary_blob_endpoint
  webjobs_storage_container_endpoint    = azurerm_storage_container.webjobs_container.url
  deployment_storage_container_endpoint = local.webjobs_storage_container_endpoint
}
