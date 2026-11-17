# Roles
resource "aws_iam_role" "this" {
  for_each             = local.role_defs
  name                 = "${var.prefix_name}-${each.value.name}"
  description          = try(each.value.description, null)
  path                 = try(each.value.path, null)
  max_session_duration = try(each.value.max_session_duration, null)
  permissions_boundary = try(each.value.permissions_boundary, null)
  tags = merge(
    var.default_tags,
    each.value.tags,
    {
      Name    = "${var.prefix_name}-${each.value.name}"
      Purpose = "This IAM role for ${each.value.name}"
    }
  )
  assume_role_policy = local.role_trust_policy[each.key]
}

# Instance profiles
resource "aws_iam_instance_profile" "this" {
  for_each = {
    for key, cfg in local.role_defs : key => cfg
    if try(cfg.instance_profile.create, false)
  }
  name = coalesce(try("${var.prefix_name}-${each.value.instance_profile.name}", null), "${aws_iam_role.this[each.key].name}-profile")
  role = aws_iam_role.this[each.key].name
  path = try(each.value.path, null)
  tags = merge(
    var.default_tags,
    each.value.tags,
    {
      Name    = "${var.prefix_name}-${each.value.name}"
      Purpose = "This instance profile for ${each.value.name}"
    }
  )
}

# Customer-managed policies
resource "aws_iam_policy" "custom" {
  for_each    = local.policy_defs
  name        = "${var.prefix_name}-${each.value.name}"
  description = try(each.value.description, null)
  path        = try(each.value.path, null)
  tags = merge(
    var.default_tags,
    each.value.tags,
    {
      Name    = "${var.prefix_name}-${each.value.name}"
      Purpose = "This Policy for ${each.value.name}"
    }
  )
  policy = coalesce(try(each.value.json, null), try(file(each.value.file), null))
}

# Inline role policies
resource "aws_iam_role_policy" "inline" {
  for_each = local.inline_role_policies
  name     = "${var.prefix_name}-${each.value.name}"
  role     = aws_iam_role.this[each.value.role_key].name
  policy   = each.value.policy
}

# Attachments: by policy key (created here)
resource "aws_iam_role_policy_attachment" "by_key" {
  for_each   = local.attachments_by_policy_key
  role       = each.value.role_name
  policy_arn = aws_iam_policy.custom[each.value.policy_key].arn
}

# Attachments: by policy ARN (preexisting)
resource "aws_iam_role_policy_attachment" "by_arn" {
  for_each   = local.attachments_by_policy_arn
  role       = each.value.role_name
  policy_arn = each.value.policy_arn
}
