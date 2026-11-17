# Normalize roles & policies
locals {
  role_defs = {
    for key, cfg in var.roles :
    key => merge(cfg, { name = coalesce(try(cfg.name, null), key) })
  }

  # Create a mapping from role name to role key for lookup
  role_name_to_key = {
    for key, cfg in local.role_defs :
    cfg.name => key
  }

  policy_defs = {
    for key, cfg in var.policies :
    key => merge(cfg, { name = coalesce(try(cfg.name, null), key) })
  }
}

# Trust policy resolution (file > generated)
locals {
  role_trust_policy = {
    for key, r in local.role_defs :
    key => (
      try(r.trust_file, null) != null
      ? file(r.trust_file)
      : jsonencode({
        Version = "2012-10-17"
        Statement = [
          merge(
            {
              Sid    = "AllowAssumeRole"
              Effect = "Allow"
              Action = "sts:${r.trust_action}"
              Principal = merge(
                length(try(r.trusted_services, [])) > 0 ? { Service = r.trusted_services } : {},
                length(try(r.trusted_aws_principals, [])) > 0 ? { AWS = r.trusted_aws_principals } : {},
                length(try(r.trusted_aws_federated, [])) > 0 ? { Federated = r.trusted_aws_federated } : {}
              )
            },
            length(try(r.trust_conditions, {})) > 0 ? { Condition = r.trust_conditions } : {}
          )
        ]
      })
    )
  }

  role_trust_sources_by_key = {
    for key, r in local.role_defs :
    key => (try(r.trust_file, null) != null ? "file" : "generated")
  }

  role_trust_files_by_key = {
    for key, r in local.role_defs : key => try(r.trust_file, null)
  }
}

# Inline role policies (flattened)
locals {
  inline_role_policies = {
    for item in flatten([
      for rk, r in local.role_defs : [
        for name, json in merge(
          try(r.inline_policies, {}),
          { for n, p in try(r.inline_policy_files, {}) : n => file(p) }
          ) : {
          key      = "${rk}::${name}"
          role_key = rk
          name     = name
          policy   = json
        }
      ]
    ]) : item.key => item
  }
}

# Plan-safe attachments (split buckets) - UPDATED TO SUPPORT LIST OF POLICY ARNS
locals {
  # Flatten policy_arn lists into individual attachment items
  attachments_iterable = flatten([
    for a in(var.attachments != null ? var.attachments : []) : [
      for arn in coalesce(try(a.policy_arn, null), []) : {
        role_name = coalesce(
          try(a.role_name, null),
          try(local.role_defs[a.role_key].name, null),
          try(local.role_defs[local.role_name_to_key[a.role_name]].name, null)
        )
        policy_arn = arn
        policy_key = try(a.policy_key, null)
      }
      if coalesce(
        try(a.role_name, null),
        try(local.role_defs[a.role_key].name, null),
        try(local.role_defs[local.role_name_to_key[a.role_name]].name, null)
      ) != null && length(coalesce(try(a.policy_arn, null), [])) > 0
    ]
  ])

  # Separate list for policy_key attachments (unchanged)
  attachments_iterable_by_key = [
    for a in(var.attachments != null ? var.attachments : []) : {
      role_name = coalesce(
        try(a.role_name, null),
        try(local.role_defs[a.role_key].name, null),
        try(local.role_defs[local.role_name_to_key[a.role_name]].name, null)
      )
      policy_key = try(a.policy_key, null)
    }
    if coalesce(
      try(a.role_name, null),
      try(local.role_defs[a.role_key].name, null),
      try(local.role_defs[local.role_name_to_key[a.role_name]].name, null)
    ) != null && try(a.policy_key, null) != null
  ]

  attachments_by_policy_key = {
    for a in local.attachments_iterable_by_key :
    "${a.role_name}||${a.policy_key}" => { role_name = a.role_name, policy_key = a.policy_key }
  }

  attachments_by_policy_arn = {
    for a in local.attachments_iterable :
    "${a.role_name}||${a.policy_arn}" => { role_name = a.role_name, policy_arn = a.policy_arn }
  }
}
