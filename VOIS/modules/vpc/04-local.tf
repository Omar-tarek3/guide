locals {
  # ---------------------------------------------------------------------------
  # Active Availability Zones (trimmed to az_count)
  # ---------------------------------------------------------------------------
  azs = slice(
    data.aws_availability_zones.available.names,
    0,
    var.az_count
  )

  # ---------------------------------------------------------------------------
  # Network Firewall endpoint IDs per AZ (only after first run + when enabled)
  # Produces: { "eu-west-1a" = "vpce-..." , "eu-west-1b" = "vpce-..." , ... }
  # ---------------------------------------------------------------------------
  firewall_endpoints_by_az = var.enable_network_firewall ? {
    for s in aws_networkfirewall_firewall.this[0].firewall_status[0].sync_states :
    s.availability_zone => s.attachment[0].endpoint_id
  } : {}

  # ---------------------------------------------------------------------------
  # Private AZ set: AZs that have non-public subnets (excludes "public" zone)
  # ---------------------------------------------------------------------------
  private_azs = toset([
    for s in local.subnet_definitions : s.az
    if s.zone != "public"
  ])

  # ---------------------------------------------------------------------------
  # Subnet definitions: Resolve AZ indices to actual AZ names
  # ---------------------------------------------------------------------------
  subnet_definitions = [
    for key, def in var.custom_subnet_config : {
      key        = key
      zone       = def.zone
      az         = def.az
      cidr_block = def.cidr_block
      prefix     = tonumber(split("/", def.cidr_block)[1])
      tags       = def.tags
    }
  ]

  # ---------------------------------------------------------------------------
  # Logical route-table sets → actual route table IDs created in this module
  # ---------------------------------------------------------------------------
  route_table_sets = {
    private  = try(values(aws_route_table.private)[*].id, [])
    public   = try(values(aws_route_table.public)[*].id, [])
    firewall = try(values(aws_route_table.firewall)[*].id, [])
  }

  # ---------------------------------------------------------------------------
  # Partition VPC endpoints by type for targeted handling
  # ---------------------------------------------------------------------------
  endpoints_interface = { for k, v in var.endpoints : k => v if lower(v.type) == "interface" }
  endpoints_gateway   = { for k, v in var.endpoints : k => v if lower(v.type) == "gateway" }
  endpoints_gwlb      = { for k, v in var.endpoints : k => v if lower(v.type) == "gatewayloadbalancer" }
  endpoints_resource  = { for k, v in var.endpoints : k => v if lower(v.type) == "resource" }
  endpoints_sn        = { for k, v in var.endpoints : k => v if lower(v.type) == "servicenetwork" }

  # ---------------------------------------------------------------------------
  # Resolve identifiers -> Subnet IDs for each endpoint type
  # ---------------------------------------------------------------------------
  endpoint_subnet_ids_interface = {
    for k, v in local.endpoints_interface :
    k => [for ident in toset(try(v.subnet_identifiers, [])) : aws_subnet.subnets[ident].id if contains(keys(aws_subnet.subnets), ident)]
  }
  endpoint_subnet_ids_gwlb = {
    for k, v in local.endpoints_gwlb :
    k => [for ident in toset(try(v.subnet_identifiers, [])) : aws_subnet.subnets[ident].id if contains(keys(aws_subnet.subnets), ident)]
  }
  endpoint_subnet_ids_resource = {
    for k, v in local.endpoints_resource :
    k => [for ident in toset(try(v.subnet_identifiers, [])) : aws_subnet.subnets[ident].id if contains(keys(aws_subnet.subnets), ident)]
  }
  endpoint_subnet_ids_sn = {
    for k, v in local.endpoints_sn :
    k => [for ident in toset(try(v.subnet_identifiers, [])) : aws_subnet.subnets[ident].id if contains(keys(aws_subnet.subnets), ident)]
  }

  # ---------------------------------------------------------------------------
  # (Legacy helper) Route tables for gateway endpoints by subnet identifiers
  # NOTE: Kept for backward-compat; superseded by endpoint_route_table_ids below
  # ---------------------------------------------------------------------------
  endpoint_route_table_ids_gateway = {
    for k, v in local.endpoints_gateway :
    k => [for ident in toset(try(v.subnet_identifiers, [])) : aws_subnet.subnets[ident].id if contains(keys(aws_subnet.subnets), ident)]
  }

  # ---------------------------------------------------------------------------
  # Consolidated resolvers used by endpoint resources
  # - Interface endpoints: resolve subnet IDs from logical identifiers
  # - Gateway endpoints : resolve route table IDs from logical identifiers
  # ---------------------------------------------------------------------------
  endpoint_subnet_ids = {
    for k, v in local.endpoints_interface :
    k => distinct(flatten([
      for ident in try(v.subnet_identifiers, []) :
      try([aws_subnet.subnets[ident]], [])
    ]))
  }

  endpoint_route_table_ids = {
    for k, v in local.endpoints_gateway :
    k => distinct(flatten([
      for ident in try(v.route_table_identifiers, []) :
      lookup(local.route_table_sets, ident, [])
    ]))
  }

  # ---------------------------------------------------------------------------
  # Security groups created per endpoint (Interface/Resource/ServiceNetwork)
  # Map: endpoint logical name -> created SG ID
  # ---------------------------------------------------------------------------
  endpoints_with_created_sg = merge(
    { for k, _ in aws_security_group.vpce_interface : k => aws_security_group.vpce_interface[k].id },
    { for k, _ in aws_security_group.vpce_resource : k => aws_security_group.vpce_resource[k].id },
    { for k, _ in aws_security_group.vpce_sn : k => aws_security_group.vpce_sn[k].id }
  )

  # ---------------------------------------------------------------------------
  # Flattened SG rule specs (CIDR sources) for auto-created endpoint SGs
  # ---------------------------------------------------------------------------
  sg_rule_specs_cidr = flatten([
    for name, cfg in var.endpoints : [
      for r in try(cfg.sg_rules, []) : [
        for cidr in try(r.cidr_blocks, []) :
        {
          key         = "cidr::${name}::${lower(r.type)}::${r.protocol}::${r.from_port}::${r.to_port}::${cidr}"
          sg_id       = lookup(local.endpoints_with_created_sg, name, null)
          type        = lower(r.type)
          protocol    = r.protocol
          from_port   = r.from_port
          to_port     = r.to_port
          cidr_block  = cidr
          description = try(r.description, "")
        }
        if contains(keys(local.endpoints_with_created_sg), name)
      ]
    ]
  ])

  # ---------------------------------------------------------------------------
  # Flattened SG rule specs (SG sources) for auto-created endpoint SGs
  # ---------------------------------------------------------------------------
  sg_rule_specs_sg = flatten([
    for name, cfg in var.endpoints : [
      for r in try(cfg.sg_rules, []) : [
        for ssg in try(r.source_security_group_ids, []) :
        {
          key         = "sgsrc::${name}::${lower(r.type)}::${r.protocol}::${r.from_port}::${r.to_port}::${ssg}"
          sg_id       = lookup(local.endpoints_with_created_sg, name, null)
          type        = lower(r.type)
          protocol    = r.protocol
          from_port   = r.from_port
          to_port     = r.to_port
          source_sg   = ssg
          description = try(r.description, "")
        }
        if contains(keys(local.endpoints_with_created_sg), name)
      ]
    ]
  ])

  # ---------------------------------------------------------------------------
  # Peering helpers
  # ---------------------------------------------------------------------------
  peerings_by_name = { for p in var.peerings : p.name => p }

  # Flatten: peering × route (if any) × identifier × actual RT IDs
  peering_route_specs = flatten([
    for p in var.peerings : [
      for r in try(p.routes, []) : [
        for ident in r.route_table_identifier : [
          for rt_id in lookup(local.route_table_sets, ident, []) : {
            key       = "${p.name}::${ident}::${rt_id}::${r.destination_cidr_block}"
            peering   = p.name
            rt_id     = rt_id
            dest_cidr = r.destination_cidr_block
          }
        ]
      ]
    ]
  ])

  # ---------------------------------------------------------------------------
  # AZs that contain firewall subnets (when firewall is enabled)
  # ---------------------------------------------------------------------------
  firewall_azs = var.enable_network_firewall ? toset([
    for s in aws_subnet.subnets : s.availability_zone
    if s.tags["Zone"] == "firewall"
  ]) : toset([])

  # Expose per-AZ endpoint IDs like { "eu-central-1a" = "vpce-0abc...", ... }
  nfw_endpoints_by_az = var.enable_network_firewall ? {
    for s in aws_networkfirewall_firewall.this[0].firewall_status[0].sync_states :
    s.availability_zone => s.attachment[0].endpoint_id
  } : {}

  # Collects Public RTBs as { "eu-central-1a" = "rtb-...", ... }
  public_rtb_by_az = try({
    for az, rt in aws_route_table.public : az => rt.id
  }, {})

}
