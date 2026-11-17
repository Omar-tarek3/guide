
output "vpc_id" {
  value = aws_vpc.this.id
}

output "subnet_ids_by_zone" {
  value = {
    for zone in distinct([for s in aws_subnet.subnets : lookup(s.tags, "Zone", "")]) :
    zone => [
      for s in aws_subnet.subnets :
      s.id if lookup(s.tags, "Zone", "") == zone
    ]
  }
}

output "availability_zones" {
  value = local.azs
}

output "nat_gateway_ids_by_az" {
  value = { for k, gw in aws_nat_gateway.this : k => gw.id }
}

output "firewall_arn" {
  value = one(aws_networkfirewall_firewall.this[*].arn)
}


output "firewall_endpoints" {
  value = one(aws_networkfirewall_firewall.this[*].firewall_status[0].sync_states)
}


# =============================================================================
# Route Table IDs by AZ
# =============================================================================

# Private RTBs (may be empty if enable_nat_gateway = false)
output "private_route_table_ids_by_az" {
  description = "Map: <az> => Private Route Table ID"
  value       = { for az, rt in aws_route_table.private : az => rt.id }
}

output "private_route_table_arns_by_az" {
  description = "Map: <az> => Private Route Table ARN"
  value       = { for az, rt in aws_route_table.private : az => rt.arn }
}

# Public RTBs
output "public_route_table_ids_by_az" {
  description = "Map: <az> => Public Route Table ID"
  value       = { for az, rt in aws_route_table.public : az => rt.id }
}

output "public_route_table_arns_by_az" {
  description = "Map: <az> => Public Route Table ARN"
  value       = { for az, rt in aws_route_table.public : az => rt.arn }
}

# Firewall RTBs (exists only for AZs with firewall subnets)
output "firewall_route_table_ids_by_az" {
  description = "Map: <az> => Firewall Route Table ID"
  value       = { for az, rt in aws_route_table.firewall : az => rt.id }
}

output "firewall_route_table_arns_by_az" {
  description = "Map: <az> => Firewall Route Table ARN"
  value       = { for az, rt in aws_route_table.firewall : az => rt.arn }
}

# Combined convenience (by AZ)
output "all_route_table_ids_by_az" {
  description = "Nested map of all RTB IDs by AZ: { private={}, public={}, firewall={} }"
  value = {
    private  = { for az, rt in aws_route_table.private : az => rt.id }
    public   = { for az, rt in aws_route_table.public : az => rt.id }
    firewall = { for az, rt in aws_route_table.firewall : az => rt.id }
  }
}

# =============================================================================
# ENDPOINT OUTPUTS
# =============================================================================
# DNS entries (zonal + regional) per endpoint key
output "interface_endpoint_dns_entries" {
  description = "Map: <endpoint_key> => list of {dns_name, hosted_zone_id}"
  value       = { for k, v in aws_vpc_endpoint.interface : k => try(v.dns_entry, []) }
}

###############################################################################
# mmanaged-prefix-list
###############################################################################
output "prefix_list_ids" {
  description = "Map of prefix list names to their IDs"
  value = {
    for k, v in aws_ec2_managed_prefix_list.this : k => v.id
  }
}

output "prefix_list_arns" {
  description = "Map of prefix list names to their ARNs"
  value = {
    for k, v in aws_ec2_managed_prefix_list.this : k => v.arn
  }
}

output "prefix_lists" {
  description = "Complete prefix list objects"
  value       = aws_ec2_managed_prefix_list.this
}
