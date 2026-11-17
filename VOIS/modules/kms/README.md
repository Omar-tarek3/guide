# 🚀 Terraform AWS KMS Module

This module manages **AWS KMS Keys, Aliases, Policies, and Grants** in a flexible way.  
It allows you to define multiple keys with per-key configuration, either **fully managed** by Terraform or as **references to external keys**.

---

## 📦 Features

- Create **symmetric or asymmetric KMS keys**
- Multi-Region key support
- Automatic **annual rotation** for symmetric keys
- Flexible **policy management**:
  - Provide a full custom JSON policy (`policy_json`)
  - OR use high-level builders (`admins`, `users_encrypt_decrypt`, `users_read_only`)
- Optional **KMS Grants** for fine-grained app/service usage
- Convenience helpers for common AWS services:
  - EKS control plane
  - S3, RDS, EBS, and CloudWatch Logs
- Outputs expose ARNs, IDs, and aliases for easy integration

---

## ⚙️ Module Inputs

### Shared Inputs

| Name           | Type        | Description |
|----------------|-------------|-------------|
| `default_tags` | map(string) | Tags applied to all created resources |
| `prefix_name`  | string      | Prefix to add to resource names (for uniqueness/consistency) |

---

### `keys_config` (map of objects)

Map of logical key name → configuration. Each entry defines one KMS key.  

#### Per-key configuration options:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `create` | bool | `true` | If `false`, treat as **external key** (do not create). |
| `description` | string | `null` | Description of the key. |
| `multi_region` | bool | `false` | Create a multi-region primary key. |
| `enable_key_rotation` | bool | `true` | Enable annual rotation (symmetric keys only). |
| `deletion_window_days` | number | `30` | Pending deletion window (7–30 days). |
| `policy_json` | string | `null` | Full JSON key policy (overrides builder). |
| `alias_suffix` | string | `null` | Alias for the key (e.g., `alias/app/prod`). |
| `admins` | list(string) | `[]` | Principals with full admin (`kms:*`) permissions. |
| `users_encrypt_decrypt` | list(string) | `[]` | Principals allowed to Encrypt/Decrypt/DataKey. |
| `users_read_only` | list(string) | `[]` | Principals with Describe/List/Get. |
| `grants` | list(object) | `[]` | Optional KMS Grants (fine-grained, revocable permissions). |
| `helpers` | object | `{}` | Convenience flags for common AWS services (see below). |
| `tags` | map(string) | `{}` | Extra tags merged onto the key and alias. |

---

### 🛠️ Helpers (optional)

These allow quick integration with AWS services without manually writing key policies:

- `eks_cluster_iam_role_arn` → allow EKS control plane to use this key  
- `allow_s3_via_service` → allow S3 to use the key via KMS  
- `allow_rds_via_service` → allow RDS to use the key via KMS  
- `allow_ebs_via_service` → allow EBS (EC2) to use the key  
- `allow_logs_via_service` → allow CloudWatch Logs to use the key  

---

## ✅ Validations

The module enforces:

- `deletion_window_days` must be **7–30** inclusive.  
- If `create = false` (external key), `policy_json` must be `null`.  
- `grants[].operations` must be valid KMS grant operations:  
    ```
    Encrypt, Decrypt, ReEncryptFrom, ReEncryptTo,
    GenerateDataKey, GenerateDataKeyWithoutPlaintext,
    DescribeKey, Sign, Verify, GetPublicKey,
    CreateGrant, RetireGrant, ListGrants, RevokeGrant
    ```

---

## 🚀 Usage Examples

### Example 1: Simple symmetric key with alias

```hcl
module "kms" {
    source = "./modules/kms"

    prefix_name  = "demo"
    default_tags = { Environment = "dev" }

    keys_config = {
        app_key = {
            description = "Key for application data"
            alias_suffix = "alias/app/demo"
            admins = ["arn:aws:iam::111122223333:role/kms-admin"]
            users_encrypt_decrypt = [
            "arn:aws:iam::111122223333:role/app-role"
            ]
        }
    }
}
```


---

Example 2: Multi-Region key with EKS helper
```hcl
keys_config = {
  eks_key = {
    description   = "EKS Secrets Encryption Key"
    multi_region  = true
    alias_suffix  = "alias/eks/cluster-a"
    helpers = {
      eks_cluster_iam_role_arn = "arn:aws:iam::111122223333:role/eks-cluster-role"
    }
  }
}
```

---

Example 3: External key reference

```hcl
keys_config = {
  external_key = {
    create     = false
    alias_suffix = "alias/shared/external"
    # no policy_json, module won’t try to manage it
  }
}
```


---

📤 Outputs

| Output | Description |
|--------|-------------|
| key_arns | Map of logical names → Key ARNs |
| key_ids	| Map of logical names → Key IDs |
| alias_arns |	Map of logical names → Alias ARNs |

Example:
```hcl
output "key_arns" {
  value = module.kms.key_arns
}
```

---

📖 Notes

	•	For DNSSEC in Route 53, use an asymmetric SIGN_VERIFY key.
	•	For EBS/S3/RDS/Logs encryption, symmetric CMKs are recommended.
	•	Multi-Region keys replicate automatically across regions.

