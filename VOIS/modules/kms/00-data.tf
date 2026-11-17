# Retrieves details about the AWS account making the Terraform calls
# Useful for getting the account_id, ARN, or user_id dynamically
data "aws_caller_identity" "current" {}

# Retrieves the AWS region configured for the current provider
# Often used to avoid hardcoding the region in resources/modules
data "aws_region" "current" {}

# Lists all availability zones in the current region that are in the "available" state
# Helps ensure resources are provisioned only in healthy AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Retrieves information about the current AWS partition (e.g., aws, aws-cn, aws-us-gov)
# Useful when writing cross-partition Terraform code or referencing ARNs dynamically
data "aws_partition" "current" {}
