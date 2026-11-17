# Terraform AWS EKS Module

A production-grade, opinionated Terraform module for creating a fully functional
Amazon Elastic Kubernetes Service (EKS) cluster with managed node groups, IAM roles,
security groups, IRSA roles, and optional managed add-ons.

---

## Features

- Creates **EKS control plane** with logging and envelope encryption (KMS).
- creates **EKS access entry** for auth to the eks
- Configures **security groups** for cluster and workers with least-privilege rules.
- Creates **IAM roles** for:
  - EKS cluster control plane.
  - Worker nodes.
  - Optional IRSA bindings (e.g. EBS CSI driver, EFS CSI driver).
- Supports **managed node groups** with Launch Templates.
- Supports **addons** (VPC CNI, CoreDNS, Kube Proxy, EBS CSI).
- Flexible **API endpoint access**:
  - Private-only,
  - Public with specific CIDRs,
  - Public to the internet.
- Consistent tagging for all resources.
- Production-ready structure with separate files for `eks.tf`, `sg.tf`, `iam.tf`, `irsa.tf`, `lt.tf`, `nodegroups.tf`, `addons.tf`, `locals.tf`, `data.tf`.

---

## Module Structure

```
├── addons.tf
├── data.tf
├── eks.tf
├── iam.tf
├── irsa.tf
├── locals.tf
├── lt.tf
├── nodegroups.tf
├── outputs.tf
├── sg.tf
└── variables.tf
```

---

## Usage

### Minimal cluster

```hcl
module "eks" {
  source = "./modules/eks"

  cluster_name = "my-cluster"
  vpc_id       = "vpc-123456"
  private_subnets = ["subnet-aaa", "subnet-bbb"]
  public_subnets  = ["subnet-ccc", "subnet-ddd"]

  public_access_enabled = true
  public_access_cidrs   = ["0.0.0.0/0"]

  EKS_NODE_GROUP_DEFINITIONS = [
    {
      suffix          = "general"
      type            = "ON_DEMAND"
      fleet           = ["t3.medium"]
      desired_size    = 2
      min_size        = 2
      max_size        = 4
      root_volume_size = 20
      ami             = "ami-123456"
    }

  authentication_mode = "API" 

  eks_access_roles = {
    "access1" = { 
      principal_arn     = "role arn"
      kubernetes_groups = ["masters"]
      policy_arn        = "policy arn"
      access_scope_type = "cluster" #OR NAMESPACE
    }
    "access2" = { 
      principal_arn     = "role arn"
      type              = EC2_LINUX
      access_scope_type = "cluster" #OR NAMESPACE
    }
}
  ]
}
```

---

## Inputs

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cluster_name` | string | n/a | Cluster name (base for all resources). |
| `cluster_version` | string | `"1.30"` | EKS version. |
| `vpc_id` | string | n/a | VPC ID. |
| `private_subnets` | list(string) | `[]` | Private subnet IDs for node groups. |
| `public_subnets` | list(string) | `[]` | Public subnet IDs for control plane if enabled. |
| `public_access_enabled` | bool | `true` | Allow public API endpoint. |
| `public_access_cidrs` | list(string) | `["0.0.0.0/0"]` | Allowed CIDRs for public API. |
| `private_access_allowed` | bool | `true` | Enable private API endpoint. |
| `eks_kms_arn` | string | `null` | KMS key ARN for secret encryption. |
| `DEFAULT_TAGS` | map(string) | `{}` | Default tags applied to all resources. |
| `irsa_bindings` | list(object) | `[]` | List of IRSA roles (see below). |
| `EKS_NODE_GROUP_DEFINITIONS` | list(object) | n/a | Node group definitions (suffix, type, fleet, scaling, AMI, root volume). |
| `enable_vpc_cni` | bool | `true` | Install VPC CNI add-on. |
| `enable_coredns` | bool | `true` | Install CoreDNS add-on. |
| `enable_kube_proxy` | bool | `true` | Install Kube Proxy add-on. |
| `enable_ebs_csi` | bool | `false` | Install EBS CSI driver add-on. |
| `ebs_csi_irsa_role_arn` | string | `null` | Pre-created IRSA role ARN for EBS CSI driver. |
| `authentication_mode` | string | `CONFIG_MAP` | auth mode for eks it could be api or configmap |
| `eks_access_roles` | string | `` | eks acces entry to authinticate with the eks|


---

## IRSA Bindings

```hcl
irsa_bindings = [
  {
    create           = true
    role_suffix      = "ebs-csi"
    namespace        = "kube-system"
    name             = "ebs-csi-controller-sa"
    policy_arns      = ["arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"]
    custom_policy_file = "" # optional
  },
  {
    create           = true
    role_suffix      = "efs-csi"
    namespace        = "kube-system"
    name             = "efs-csi-controller-sa"
    policy_arns      = ["arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy"]
    custom_policy_file = "" # optional
  }
]
```

---

## Outputs

| Name | Description |
|------|-------------|
| `cluster_id` | EKS cluster ID |
| `cluster_name` | EKS cluster name |
| `cluster_endpoint` | Cluster API server endpoint |
| `cluster_ca` | Base64 cluster CA |
| `cluster_iam_role_arn` | IAM role ARN for cluster |
| `node_iam_role_arn` | IAM role ARN for worker nodes |
| `oidc_provider_arn` | OIDC provider ARN |
| `worker_security_group_id` | Security group ID for workers |
| `control_plane_security_group_id` | Security group ID for control plane |

---

## Notes

- This module **does not** create Kubernetes ServiceAccounts for IRSA. You must create them inside the cluster and annotate with the role ARN.
- CNI policy should be attached via IRSA on `aws-node` SA.
- `aws-auth` ConfigMap is not managed here; you must map IAM roles to Kubernetes RBAC separately.
- EBS and EFS CSI drivers require IRSA roles (see examples).
