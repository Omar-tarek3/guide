terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.0"
    }

    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }

  # Uncomment for remote state (recommended for prod)
backend "azurerm" {
    #resource_group_name  = "robotics-test"
    #storage_account_name = "tfstatemcsmigration"
    #container_name       = "tfstate"
    #key                  = "azurefunctions/cdk/terraform.tfstate"
    #use_azuread_auth     = true  # Use Azure AD authentication instead of storage keys
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}
