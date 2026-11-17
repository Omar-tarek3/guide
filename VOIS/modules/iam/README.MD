# IAM One‑Call Module — Production Example

This example shows a single module call that creates **multiple IAM roles** with different **trust policies** (file-based and generated), **customer-managed policies**, and **AWS-managed policy** attachments. It also demonstrates **inline role policies** and **instance profiles**.

> Module files expected at: `modules/iam-onecall/{main.tf, variables.tf, locals.tf, data.tf, outputs.tf}` (as provided earlier).

---

## Folder Structure (suggested)

```
root/
├─ provider.tf
├─ main.tf                 # your root stack (this example)
├─ policies/
│  ├─ trust/
│  │  ├─ web.json
│  │  ├─ ingestion.json
│  │  └─ analytics.json
│  ├─ s3_rw_app.json
│  └─ inline/
│     ├─ cw_logs_basic.json
│     └─ readonly_extra.json
└─ modules/
   └─ iam-onecall/
      ├─ variables.tf
      ├─ locals.tf
      ├─ data.tf
      ├─ main.tf
      └─ outputs.tf
```

---

## provider.tf (root)

```hcl
terraform {
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = "us-east-1"
}
```

---

## Trust Policy JSONs (examples)

`policies/trust/web.json` (EC2 assumes role; restrict by ExternalId)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowAssumeRole",
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Principal": { "Service": ["ec2.amazonaws.com"] },
    "Condition": {
      "StringEquals": { "sts:ExternalId": "web-prod" }
    }
  }]
}
```

`policies/trust/ingestion.json` (Lambda + EventBridge)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowAssumeRole",
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Principal": { "Service": ["lambda.amazonaws.com", "events.amazonaws.com"] }
  }]
}
```

`policies/trust/analytics.json` (Federated principals via trusted AWS accounts; example condition)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowAssumeRole",
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Principal": { "AWS": ["arn:aws:iam::111122223333:role/analyst"] },
    "Condition": {
      "StringEquals": { "aws:PrincipalOrgID": "o-exampleorgid" }
    }
  }]
}
```

---

## Customer-Managed Policy JSON (example)

`policies/s3_rw_app.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::my-app-bucket"] },
    { "Effect": "Allow", "Action": ["s3:GetObject","s3:PutObject"], "Resource": ["arn:aws:s3:::my-app-bucket/*"] }
  ]
}
```

`policies/inline/cw_logs_basic.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
    "Resource": "*"
  }]
}
```

`policies/inline/readonly_extra.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["ec2:Describe*","s3:List*"],
    "Resource": "*"
  }]
}
```

---

## main.tf (root) — Production Example

```hcl
module "iam" {
  source = "./modules/iam-onecall"

  # --- Roles (mix of trust_file and generated trust)
  roles = {
    # 1) Web app role — trust from file; instance profile; inline policies
    web = {
      name        = "app-web-role"
      description = "EC2 role for web app"
      tags        = { Project = "prod-app", Env = "prod", Owner = "platform" }
      trust_file  = "${path.root}/policies/trust/web.json"

      instance_profile = { create = true }

      inline_policies = {
        deny_dangerous = jsonencode({
          Version = "2012-10-17",
          Statement = [{
            Effect   = "Deny",
            Action   = ["iam:DeleteRole","iam:DeletePolicy","iam:PutRolePolicy"],
            Resource = "*"
          }]
        })
      }
      inline_policy_files = {
        cw_logs_basic = "${path.root}/policies/inline/cw_logs_basic.json"
      }
    }

    # 2) Ingestion role — trust from file; inline from file only
    ingestion = {
      name        = "data-ingestion-role"
      description = "Lambda/EventBridge role for ingestion"
      tags        = { Project = "prod-app", Env = "prod", Owner = "data" }
      trust_file  = "${path.root}/policies/trust/ingestion.json"

      inline_policy_files = {
        readonly_extra = "${path.root}/policies/inline/readonly_extra.json"
      }
    }

    # 3) Analytics role — generated trust (no file), with conditions
    analytics = {
      name                     = "analytics-consumer-role"
      description              = "Analyst access via trusted principals"
      tags                     = { Project = "analytics", Env = "prod", Owner = "bi" }
      trusted_services         = [] # none
      trusted_aws_principals   = ["arn:aws:iam::111122223333:role/analyst"]
      trust_conditions         = { StringEquals = { "aws:PrincipalOrgID" = "o-exampleorgid" } }
    }
  }

  # --- Customer managed policies
  policies = {
    s3_rw_app = {
      description = "App S3 read/write for main bucket"
      file        = "${path.root}/policies/s3_rw_app.json"
      tags        = { Project = "prod-app", Tier = "data" }
    }

    metrics_write = {
      description = "CloudWatch PutMetricData"
      json = jsonencode({
        Version = "2012-10-17",
        Statement = [{
          Effect   = "Allow",
          Action   = ["cloudwatch:PutMetricData"],
          Resource = "*"
        }]
      })
    }
  }

  # --- Attachments (mix of policy_key and policy_arn, created+existing roles)
  attachments = [
    # Attach created policies to created roles (by policy_key)
    { role_key = "web",       policy_key = "s3_rw_app"   },
    { role_key = "ingestion", policy_key = "metrics_write" },

    # Attach AWS-managed policies (by ARN) to created roles
    { role_key  = "web",       policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" },
    { role_key  = "ingestion", policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" },

    # Attach an existing policy ARN to an existing role by name
    { role_name = "central-observability-role", policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy" }
  ]
}
```

---

## Useful Outputs

In your root, you can reference:

```hcl
# Roles
module.iam.role_arns_by_key["web"]
module.iam.role_names_by_key["analytics"]
module.iam.role_trust_sources_by_key["ingestion"]   # "file" or "generated"
module.iam.instance_profile_names_by_key["web"]

# Policies
module.iam.policy_arns_by_key["s3_rw_app"]

# Attachments (debug/visibility)
module.iam.attachments_by_policy_key
module.iam.attachments_by_policy_arn
```

---

## Plan/Apply

```bash
terraform init
terraform fmt -recursive && terraform validate
terraform plan
terraform apply
```

This module is plan-safe: `for_each` keys are static (role/policy keys, literal ARNs). Trust can be file-based or generated using `trusted_services`, `trusted_aws_principals`, and `trust_conditions`.
