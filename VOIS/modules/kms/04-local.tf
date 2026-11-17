locals {
  # Grants
  kms_grant_pairs = flatten([
    for k, v in var.keys_config : [
      for idx, g in try(v.grants, []) : {
        map_key = "${k}:${idx}"
        key     = k
        grant   = g
        create  = try(v.create, true)
      }
    ]
  ])

}
