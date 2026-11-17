
# Dynamic Security Group Module — Production Ready

This module allows you to **create multiple AWS Security Groups** in a single Terraform module call, along with their ingress and egress rules.

---

## Folder Structure

```
root/
├─ main.tf                # calls the module
├─ variables.tf           # optional root-level vars
└─ modules/
   └─ sg/
      ├─ variables.tf
      ├─ locals.tf
      ├─ main.tf
      ├─ outputs.tf
      └─ data.tf
```

---

## Provider Configuration (root/provider.tf)
```hcl
provider "aws" {
  region = "us-east-1"
}
```

---

## Example Usage (root/main.tf)

```hcl
module "network_sg" {
  source = "./modules/sg"

  security_groups = {
    web_sg = {
      name   = "web-sg"
      vpc_id = var.vpc_id
      tags   = { Project = "demo", Env = "dev" }

      ingress_rules = [
        # 1) HTTP + HTTPS from Internet (discrete ports)
        {
          description      = "Web from Internet"
          protocol         = "tcp"
          ports            = [80, 443]
          cidr_blocks      = ["0.0.0.0/0"]
          ipv6_cidr_blocks = ["::/0"]
        },

        # 2) SSH from office CIDR using port range
        {
          description = "SSH range from office"
          protocol    = "tcp"
          from_port   = 2200
          to_port     = 2205
          cidr_blocks = ["203.0.113.0/24"]
        },

        # 3) Application traffic from specific source SGs
        {
          description               = "App to Web SGs"
          protocol                  = "tcp"
          from_port                 = 7000
          to_port                   = 7005
          source_security_group_ids = [aws_security_group.app.id, aws_security_group.batch.id]
        }
      ]

      egress_rules = [
        {
          description      = "HTTPS out"
          protocol         = "tcp"
          ports            = [443]
          cidr_blocks      = ["0.0.0.0/0"]
          ipv6_cidr_blocks = ["::/0"]
        }
      ]

      allow_all_egress_when_empty = false
    }

    db_sg = {
      name   = "db-sg"
      vpc_id = var.vpc_id
      tags   = { Project = "demo", Env = "prod" }

      ingress_rules = [
        {
          description = "PostgreSQL access from web_sg"
          protocol    = "tcp"
          ports       = [5432]
          source_security_group_ids = [aws_security_group.web.id]
        }
      ]

      egress_rules = []
      allow_all_egress_when_empty = true
    }
  }
}
```

---

## Outputs

```hcl
output "web_sg_id" {
  value = module.network_sg.security_group_ids["web_sg"]
}

output "db_sg_id" {
  value = module.network_sg.security_group_ids["db_sg"]
}
```

---

## Key Features

- **One module call** for all SGs, ingress, and egress rules.
- Supports:
  - Single ports (`ports = [80,443]`)
  - Port ranges (`from_port = 10256, to_port = 11000`)
  - Self-referencing rules (`self = true`)
  - Source and destination security groups.
  - Prefix lists and dual-stack IPv4/IPv6 rules.
- Default allow-all egress if you leave `egress_rules = []` and `allow_all_egress_when_empty = true`.

---

## Debugging

To inspect expanded rules during development:

```hcl
output "debug_ingress" {
  value     = module.network_sg.debug_ingress
  sensitive = true
}

output "debug_egress" {
  value     = module.network_sg.debug_egress
  sensitive = true
}
```

---

## Commands

```bash
terraform init
terraform plan
terraform apply
```

---

## Notes

- All `for_each` keys are pre-computed to avoid "unknown at plan time" issues.
- Efficient handling of port ranges ensures minimal AWS rules.
- Ideal for production environments with complex networking requirements.
