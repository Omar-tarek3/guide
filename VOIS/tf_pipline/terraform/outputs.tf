output "function_app_name" {
  description = "The name of the deployed Azure Function App"
  value       = local.function_app_name
}

output "function_app_url" {
  description = "The default URL of the Function App"
  value       = "https://${local.function_app_name}.azurewebsites.net"
}

output "resource_group_name" {
  description = "Resource group name"
  value       = data.azurerm_resource_group.main.name
}


output "global_key_vault_name" {
  description = "Global Key Vault name"
  value       = data.azurerm_key_vault.global.name
}

output "local_key_vault_name" {
  description = "Local Key Vault name"
  value       = data.azurerm_key_vault.local.name
}

output "application_insights_name" {
  description = "Application Insights resource name"
  value       = data.azurerm_application_insights.main.name
}

output "managed_identity_principal_id" {
  description = "The principal ID of the Function App's managed identity"
  value       = azurerm_user_assigned_identity.function.principal_id
}

output "user_assigned_identity_id" {
  description = "User-assigned identity resource ID"
  value       = azurerm_user_assigned_identity.function.id
}

output "private_endpoint_id" {
  description = "Private endpoint ID for function app"
  value       = azurerm_private_endpoint.function_app.id
}

