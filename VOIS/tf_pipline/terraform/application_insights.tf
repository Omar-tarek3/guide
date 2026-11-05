data "azurerm_log_analytics_workspace" "central" {
  name                = var.log_analytics_workspace_name
  resource_group_name = var.log_analytics_workspace_resource_group
}

data "azurerm_application_insights" "main" {
  name                = var.application_insights_name
  resource_group_name = var.application_insights_resource_group
}
