resource "azurerm_user_assigned_identity" "function" {
  name                = local.identity_name
  location            = local.resource_location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = local.common_tags
}