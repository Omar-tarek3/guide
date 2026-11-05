locals {
  env_suffix            = var.environment == "development" ? "dev" : "prod"
  prefix                = "${var.product}-${local.env_suffix}"
  resource_location     = var.azure_region
  process_name_slug     = lower(replace(replace(var.process_name, "_", "-"), " ", "-"))
  naming_environment    = local.env_suffix
  naming_sequence       = "001"
  naming_suffix         = "azugwc-${local.process_name_slug}-${local.naming_environment}-${local.naming_sequence}"
  function_app_name     = var.function_app_name
  app_service_plan_name = "asp-${local.naming_suffix}"
  private_endpoint_name = "pep-${local.naming_suffix}"
  identity_name         = "id-${local.naming_suffix}"

  common_tags = {
    Application              = var.process_name
    Environment              = var.environment
    Confidentiality          = var.confidentiality
    ManagedBy                = var.managed_by
    Project                  = var.project
    TaggingVersion           = var.tagging_version
    OrchestratorEnvironment  = var.orchestrator_environment
    Shortcode                = var.shortcode
    LocalMarket              = var.local_market
    BusinessVertical         = var.business_vertical
  }
}
