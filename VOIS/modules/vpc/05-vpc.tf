resource "aws_vpc" "this" {
  cidr_block = var.cidr_block

  enable_dns_support = true

  enable_dns_hostnames = true

  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-vpc"
      Purpose = "VPC for ${var.prefix_name}"
    }
  )
}
