# Normalize SG defs
locals {
  sg_defs = {
    for key, cfg in var.security_groups :
    key => {
      name                        = coalesce(try(cfg.name, null), key)
      description                 = coalesce(try(cfg.description, null), "Managed by Terraform")
      vpc_id                      = cfg.vpc_id
      tags                        = try(cfg.tags, {})
      revoke_rules_on_delete      = try(cfg.revoke_rules_on_delete, true)
      allow_all_egress_when_empty = try(cfg.allow_all_egress_when_empty, true)
      ingress_rules               = try(cfg.ingress_rules, [])
      egress_rules                = try(cfg.egress_rules, [])
    }
  }
}

# Ingress: ports fan-out per SG
locals {
  ingress_by_port = flatten([
    for sgk, sg in local.sg_defs : [
      for idx, r in sg.ingress_rules : (
        length(coalesce(r.ports, [])) > 0
        ? [for p in coalesce(r.ports, []) : merge(r, {
          from_port   = p,
          to_port     = p,
          _port_key   = tostring(p),
          _sg_key     = sgk,
          _rule_index = idx
        })]
        : [merge(r, {
          _port_key   = format("%d-%d", try(r.from_port, 0), try(r.to_port, 0)),
          _sg_key     = sgk,
          _rule_index = idx
        })]
      )
    ]
  ])
}

# Ingress: expand source SGs (by key or id) with stable keys
locals {
  ingress_expanded = flatten([
    for _, r in local.ingress_by_port : (
      length(coalesce(r.source_sg_keys, [])) > 0
      ? [for j, key in r.source_sg_keys : merge(r, {
        _key    = format("ing-%s-%03d-%s-%s-k%03d", r._sg_key, r._rule_index, r.protocol, r._port_key, j),
        _src_sg = aws_security_group.this[key].id
      })]
      : length(coalesce(r.source_security_group_ids, [])) > 0
      ? [for j, sgid in r.source_security_group_ids : merge(r, {
        _key    = format("ing-%s-%03d-%s-%s-i%03d", r._sg_key, r._rule_index, r.protocol, r._port_key, j),
        _src_sg = sgid
      })]
      : [merge(r, {
        _key    = format("ing-%s-%03d-%s-%s-none", r._sg_key, r._rule_index, r.protocol, r._port_key),
        _src_sg = null
      })]
    )
  ])
}

# Egress: ports fan-out per SG
locals {
  egress_by_port = flatten([
    for sgk, sg in local.sg_defs : [
      for idx, r in sg.egress_rules : (
        length(coalesce(r.ports, [])) > 0
        ? [for p in coalesce(r.ports, []) : merge(r, {
          from_port   = p,
          to_port     = p,
          _port_key   = tostring(p),
          _sg_key     = sgk,
          _rule_index = idx
        })]
        : [merge(r, {
          _port_key   = format("%d-%d", try(r.from_port, 0), try(r.to_port, 0)),
          _sg_key     = sgk,
          _rule_index = idx
        })]
      )
    ]
  ])
}

# Egress: expand destination SGs (by key or id) with stable keys
locals {
  egress_expanded = flatten([
    for _, r in local.egress_by_port : (
      length(coalesce(r.destination_sg_keys, [])) > 0
      ? [for j, key in r.destination_sg_keys : merge(r, {
        _key    = format("eg-%s-%03d-%s-%s-k%03d", r._sg_key, r._rule_index, r.protocol, r._port_key, j),
        _dst_sg = aws_security_group.this[key].id
      })]
      : length(coalesce(r.destination_security_group_ids, [])) > 0
      ? [for j, sgid in r.destination_security_group_ids : merge(r, {
        _key    = format("eg-%s-%03d-%s-%s-i%03d", r._sg_key, r._rule_index, r.protocol, r._port_key, j),
        _dst_sg = sgid
      })]
      : [merge(r, {
        _key    = format("eg-%s-%03d-%s-%s-none", r._sg_key, r._rule_index, r.protocol, r._port_key),
        _dst_sg = null
      })]
    )
  ])
}

# Default allow-all egress flags per SG
locals {
  egress_all_when_empty = {
    for sgk, sg in local.sg_defs :
    sgk => true if sg.allow_all_egress_when_empty && length(sg.egress_rules) == 0
  }
}
