# VPC Terraform Module

This module creates an AWS VPC and all associated networking components, including subnets, route tables, NAT gateways, optional Network Firewall, VPC Endpoints, and VPC peering connections.  

It is designed for **multi-environment deployments** (dev/stage/prod) and supports advanced scenarios such as Network Firewall, Karpenter zone hints, and Service Network (VPC Lattice) endpoints.

---

## 📦 Features
- Creates a VPC with configurable CIDR and number of AZs
- Supports **subnet strategies**:
  - Explicit subnet definitions with custom CIDRs
- NAT gateway strategy:
  - One NAT per AZ or a single shared NAT
- Optional **AWS Network Firewall** with per-AZ firewall subnets
- VPC Endpoints (Interface, Gateway, Gateway Load Balancer, Resource, ServiceNetwork)
- Optional Karpenter hints (allowed AZs, cluster name)
- VPC Peering support with automatic route propagation
- First-run toggle for bootstrapping scenarios
- Rich tagging support

---

## 🚀 Usage

```hcl
module "vpc" {
  source = "./modules/vpc"

    custom_subnet_config=   "app-eu-central-1a" = { cidr_block = "10.81.0.0/18",   az = "eu-central-1a", zone = "app" }


    enable_nat_gateway = true
    single_nat_gateway = false

    enable_network_firewall = true
    firewall_name           = "dev-fw"
    firewall_policy_arn     = "arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/dev-fw-policy"

    karpenter_config = {
      cluster_name    = "dev-eks"
      karpenter_zones = ["us-east-1a", "us-east-1b"]
    }

    peerings = {
      {account_service = {
        name        = "shared-services"
        peer_vpc_id = "vpc-abcdef123"
        auto_accept = true
        routes = [
          {
            route_table_identifier = ["private"]
            destination_cidr_block = "172.16.0.0/16"
          }
        ]
      }
   }
    }

    endpoints = {
      s3 = {
        type                    = "Gateway"
        service                 = "s3"
        route_table_identifiers = ["private"]
      }
      ecr_api = {
        type                 = "Interface"
        service              = "com.amazonaws.us-east-1.ecr.api"
        subnet_identifiers   = ["private"]
        create_security_group = true
      }
    }

    first_run = true
  }

  default_tags = {
    Environment = "dev"
    Owner       = "platform-team"
  }

```

---

⚙️ Input Variables

vpc_config (object, required)

Main configuration object for the VPC.
  - Core
    - cidr_block (string) – VPC CIDR, e.g., 10.0.0.0/16
    - az_count (number) – How many AZs to span
    - prefix_name (string) – Prefix applied to resource names
  - Subnet Strategy
    - custom_subnet_config (map) – Explicit CIDR/zone definitions
  - NAT
    - enable_nat_gateway (bool) – Enable NAT gateways
    - single_nat_gateway (bool) – Use one NAT per VPC (true) or per-AZ (false)
  - Network Firewall
    - enable_network_firewall (bool) – Enable firewall resources
    - firewall_name (string) – Firewall name
    - firewall_policy_arn (string) – ARN of a pre-created firewall policy
  - Karpenter Hints (optional)
    - cluster_name (string) – EKS cluster name
    - karpenter_zones (list) – Allowed zones for provisioners
  - VPC Peerings (optional)
    - name (string) – Logical name
    - peer_vpc_id (string) – Target peer VPC
    - routes (list) – Optional route updates
  - Endpoints (optional)
    - Supports Interface, Gateway, GatewayLoadBalancer, Resource, ServiceNetwork
    - Placement via subnet_identifiers (for Interface/GWLB/etc.) or route_table_identifiers (for Gateway)
    - Security and DNS options available per endpoint
  - Flow Log
    - Dynamic flow log configuration supporting multiple logging configurations
  - Misc
    - first_run (bool) – Toggle for bootstrap conditions

default_tags (map, required)

Key-value map of tags applied to all resources.

---

📤 Outputs
- Core
  - vpc_id – ID of the created VPC
  - availability_zones – AZs used in this VPC
  - subnet_ids_by_zone – Map of zone → list of subnet IDs
- NAT & Firewall
  - nat_gateway_ids_by_az – Map of AZ → NAT Gateway IDs
  - firewall_arn – ARN of the Network Firewall (if enabled)
  - firewall_endpoints – Map of AZ → firewall endpoint ENIs
- Route Tables
  - private_route_table_ids_by_az – Map of AZ → Private RTB IDs
  - public_route_table_ids_by_az – Map of AZ → Public RTB IDs
  - firewall_route_table_ids_by_az – Map of AZ → Firewall RTB IDs
  - all_route_table_ids_by_az – Nested map of all RTBs { private, public, firewall }


---

🛠 Example

Provision a 3-AZ VPC with NAT, public/private subnets, firewall, and S3 gateway endpoint:

```hcl
module "vpc" {
  source = "./modules/vpc"

    cidr_block          = "10.10.0.0/16"
    az_count            = 3
    prefix_name         = "prod"
    custom_subnet_config=   "app-eu-central-1a" = { cidr_block = "10.81.0.0/18",   az = "eu-central-1a", zone = "app" }
    enable_nat_gateway  = true
    single_nat_gateway  = false
    enable_network_firewall = false
    firewall_name           = ""
    firewall_policy_arn     = ""
    endpoints = {
      s3 = {
        type                    = "Gateway"
        service                 = "s3"
        route_table_identifiers = ["private"]
      }
    }
    first_run = true
  }

  default_tags = {
    Environment = "prod"
    Owner       = "network-team"
  }
}
```

---

🔒 Notes
- For firewall: You must supply a pre-existing firewall_policy_arn.
- For cross-account/region peerings, specify peer_owner_id and/or peer_region.
- For Karpenter: This module doesn’t deploy Karpenter itself, it only narrows allowed zones.

---


