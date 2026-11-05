data "azurerm_virtual_network" "existing" {
  name                = var.vnet_name
  resource_group_name = var.vnet_resource_group != "" ? var.vnet_resource_group : data.azurerm_resource_group.main.name
}

data "azurerm_subnet" "outbound_integration" {
  name                 = var.vnet_integration_subnet_name
  virtual_network_name = var.vnet_name
  resource_group_name  = var.vnet_resource_group != "" ? var.vnet_resource_group : data.azurerm_resource_group.main.name
}

data "azurerm_subnet" "private_endpoint" {
  name                 = var.private_endpoint_subnet_name
  virtual_network_name = var.vnet_name
  resource_group_name  = var.vnet_resource_group != "" ? var.vnet_resource_group : data.azurerm_resource_group.main.name
}

data "azurerm_private_dns_zone" "functions" {
  name                = var.private_dns_zone_name
  resource_group_name = var.private_dns_zone_resource_group
}

resource "azurerm_private_endpoint" "function_app" {
  name                = local.private_endpoint_name
  location            = local.resource_location
  resource_group_name = data.azurerm_resource_group.main.name
  subnet_id           = data.azurerm_subnet.private_endpoint.id

  private_service_connection {
    name                           = "${local.function_app_name}-psc"
    private_connection_resource_id = azapi_resource.linux_function_app.id
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.functions.id]
  }

  tags = local.common_tags
}

locals {
  function_subnet_id = data.azurerm_subnet.outbound_integration.id
}
