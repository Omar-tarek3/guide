resource "aws_ec2_managed_prefix_list" "this" {
  for_each = var.prefix_lists

  name           = each.key
  address_family = each.value.address_family
  max_entries    = each.value.max_entries

  tags = merge(
    var.default_tags,
    each.value.tags,
    {
      Name = "${var.prefix_name}-${each.key}"
    }
  )
}

resource "aws_ec2_managed_prefix_list_entry" "this" {
  for_each = merge([
    for pl_name, pl_config in var.prefix_lists : {
      for entry_name, entry_config in pl_config.entries :
      "${pl_name}/${entry_name}" => {
        prefix_list_id = aws_ec2_managed_prefix_list.this[pl_name].id
        cidr           = entry_config.cidr
        description    = entry_config.description
      }
    }
  ]...)

  prefix_list_id = each.value.prefix_list_id
  cidr           = each.value.cidr
  description    = each.value.description
}
