resource "azurerm_service_plan" "flex" {
  name                = local.app_service_plan_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.resource_location
  os_type             = "Linux"
  sku_name            = "FC1"
  zone_balancing_enabled = var.zone_redundancy_enabled
  tags                = local.common_tags
}

locals {
  service_plan_id = azurerm_service_plan.flex.id
}
