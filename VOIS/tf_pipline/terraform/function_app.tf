resource "azapi_resource" "linux_function_app" {
  type      = "Microsoft.Web/sites@2025-03-01"
  parent_id = data.azurerm_resource_group.main.id
  name      = local.function_app_name
  location  = local.resource_location
  tags      = local.common_tags

  schema_validation_enabled = false
  ignore_null_property      = true

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.function.id]
  }

  body = {
    kind = "functionapp,linux"
    properties = {
      serverFarmId           = local.service_plan_id
      httpsOnly              = true
      enabled                = true
      reserved               = true
      virtualNetworkSubnetId = local.function_subnet_id
      publicNetworkAccess    = "Disabled"

      functionAppConfig = {
        runtime = {
          name    = var.function_runtime
          version = var.function_runtime == "python" ? var.python_version : var.node_version
        }
        scaleAndConcurrency = {
          instanceMemoryMB     = var.memory_mb
          maximumInstanceCount = var.reserved_instances
        }
        deployment = {
          storage = {
            type  = "BlobContainer"
            value = local.deployment_storage_container_endpoint
            authentication = {
              type                           = "UserAssignedIdentity"
              userAssignedIdentityResourceId = azurerm_user_assigned_identity.function.id
            }
          }
        }
      }

      siteConfig = {
        ftpsState                           = "FtpsOnly"
        http20Enabled                       = false
        minTlsVersion                       = "1.3"
        use32BitWorkerProcess               = false
        webSocketsEnabled                   = false
        managedPipelineMode                 = "Integrated"
        remoteDebuggingEnabled              = false
        vnetRouteAllEnabled                 = true
        loadBalancing                       = "LeastRequests"
        scmIpSecurityRestrictionsUseMain    = false
        ipSecurityRestrictionsDefaultAction = "Deny"
        ipSecurityRestrictions = [
          {
            ipAddress = "85.115.49.2/32"
            action    = "Allow"
            priority  = 100
            name      = "AllowVodafoneIP1"
          },
          {
            ipAddress = "85.115.50.2/32"
            action    = "Allow"
            priority  = 110
            name      = "AllowVodafoneIP2"
          },
          {
            ipAddress = "185.69.146.0/24"
            action    = "Allow"
            priority  = 120
            name      = "AllowVodafoneSubnet"
          }
        ]
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.function_webjobs_storage_blob_owner,
    azurerm_role_assignment.function_webjobs_storage_queue_contributor,
    azurerm_role_assignment.function_process_storage_blob_contributor
  ]
}

resource "azapi_update_resource" "function_app_settings" {
  type        = "Microsoft.Web/sites/config@2025-03-01"
  resource_id = "${azapi_resource.linux_function_app.id}/config/appSettings"

  body = {
    properties = merge(
      {
        FUNCTIONS_EXTENSION_VERSION            = "~4"
        WEBSITE_MEMORY_LIMIT_MB                = tostring(var.memory_mb)
        AZURE_CLIENT_ID                        = azurerm_user_assigned_identity.function.client_id
        APPINSIGHTS_INSTRUMENTATIONKEY         = data.azurerm_application_insights.main.instrumentation_key
        APPLICATIONINSIGHTS_CONNECTION_STRING  = data.azurerm_application_insights.main.connection_string
        AzureWebJobsStorage__accountName       = var.webjobs_storage_account_name
        AzureWebJobsStorage__blobServiceUri    = local.webjobs_storage_blob_service_uri
        AzureWebJobsStorage__clientId          = azurerm_user_assigned_identity.function.client_id
        AzureWebJobsStorage__credential        = "managedidentity"
        FUNCTION_SCHEDULE                      = var.schedule_cron
        SERVICE_NAME                           = var.service_name
        PROCESS_NAME                           = var.process_name
        PROCESS_FUNCTION                       = var.process_function
        CASE_LIMIT                             = var.case_limit
        PROCESS_IDENTIFIER                     = var.process_identifier
        PROJECT_NAME                           = var.project_name
        PROCESS_STAGE                          = var.process_stage
        QUEUE_NAME                             = var.queue_name
        SHORT_DESCRIPTION                      = var.short_description
        LOCAL_MARKET                           = var.local_market
        BUSINESS_VERTICAL                      = var.business_vertical
        ENVIRONMENT                            = var.environment
        SHORTCODE                              = var.shortcode
        DEBUG                                  = "disable"
        GLOBAL_KEY_VAULT_NAME                  = data.azurerm_key_vault.global.name
        LOCAL_KEY_VAULT_NAME                   = data.azurerm_key_vault.local.name
        AzureFunctionsJobHost__functionTimeout = format("%02d:%02d:00", floor(var.timeout_seconds / 3600), floor((var.timeout_seconds % 3600) / 60))
      },
      var.custom_app_settings
    )
  }

  depends_on = [azapi_resource.linux_function_app]
}
