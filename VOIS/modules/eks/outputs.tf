//--------------------------------------------------------------------------------
// outputs.tf — Exported values from the EKS module
//--------------------------------------------------------------------------------

#-----------------------------------------------------------
# Cluster basics
#-----------------------------------------------------------
output "cluster_name" {
  description = "EKS cluster name (sanitized)"
  value       = aws_eks_cluster.cluster.name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint URL"
  value       = aws_eks_cluster.cluster.endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64-encoded cluster CA data (use for kubernetes provider/kubeconfig)"
  value       = aws_eks_cluster.cluster.certificate_authority[0].data
}

#-----------------------------------------------------------
# Security groups
#-----------------------------------------------------------
output "control_plane_sg_id" {
  description = "Security Group ID attached to the EKS control plane ENIs"
  value       = aws_security_group.eks_cluster_control_plane_sg.id
}

output "worker_node_sg_id" {
  description = "Security Group ID used by EKS worker nodes"
  value       = aws_security_group.eks_cluster_worker_node_sg.id
}

#-----------------------------------------------------------
# Core IAM roles (cluster & node)
#-----------------------------------------------------------
output "cluster_iam_role_arn" {
  description = "IAM Role ARN used by the EKS control plane"
  value       = aws_iam_role.aws_eks_cluster_role.arn
}

output "node_iam_role_arn" {
  description = "IAM Role ARN used by the EKS worker nodes (map this in aws-auth)"
  value       = aws_iam_role.aws_eks_node_role.arn
}

#-----------------------------------------------------------
# OIDC / IRSA
#-----------------------------------------------------------
output "oidc_provider_arn" {
  description = "ARN of the cluster OIDC provider (null if no IRSA bindings were created)"
  value       = try(aws_iam_openid_connect_provider.eks[0].arn, null)
}

output "irsa_role_arns" {
  description = "Map of IRSA role ARNs keyed by role_suffix (e.g., { ebs-csi-controller = arn:..., efs-csi-controller = arn:... })"
  value       = { for k, r in aws_iam_role.irsa_roles : k => r.arn }
}

output "irsa_custom_policy_arns" {
  description = "Map of custom IRSA policy ARNs keyed by role_suffix (only where custom policies were created)"
  value       = { for k, p in aws_iam_policy.irsa_custom_policy : k => p.arn }
}

#-----------------------------------------------------------
# Launch templates & node groups
#-----------------------------------------------------------
output "launch_template_ids" {
  description = "Map of Launch Template IDs keyed by <type>-<suffix>-lt"
  value       = { for k, lt in aws_launch_template.node_group_launch_template : k => lt.id }
}

output "node_group_names" {
  description = "Map of EKS Managed Node Group names keyed by <type>-<suffix>"
  value       = { for k, ng in aws_eks_node_group.node_group : k => ng.node_group_name }
}

output "node_group_arns" {
  description = "Map of EKS Managed Node Group ARNs keyed by <type>-<suffix>"
  value       = { for k, ng in aws_eks_node_group.node_group : k => ng.arn }
}

#-----------------------------------------------------------
# Managed add-ons (versions/ARNs are optional depending on enable flags)
#-----------------------------------------------------------
output "addon_vpc_cni_version" {
  description = "Installed version of the VPC CNI add-on (null if disabled)"
  value       = try(aws_eks_addon.vpc_cni[0].addon_version, null)
}

output "addon_coredns_version" {
  description = "Installed version of the CoreDNS add-on (null if disabled)"
  value       = try(aws_eks_addon.coredns[0].addon_version, null)
}

output "addon_kube_proxy_version" {
  description = "Installed version of the kube-proxy add-on (null if disabled)"
  value       = try(aws_eks_addon.kube_proxy[0].addon_version, null)
}

output "addon_ebs_csi_version" {
  description = "Installed version of the EBS CSI add-on (null if disabled)"
  value       = try(aws_eks_addon.ebs_csi_driver[0].addon_version, null)
}

output "addon_ebs_csi_service_account_role_arn" {
  description = "IRSA role ARN attached to the EBS CSI controller ServiceAccount (null if not configured)"
  value       = try(aws_eks_addon.ebs_csi_driver[0].service_account_role_arn, null)
}

# Output ASG attachments 
output "asg_attachments" {
  description = "ASG output"
  value = [
    for ng_key, ng in aws_eks_node_group.node_group :
    {
      autoscaling_group_name = try(ng.resources[0].autoscaling_groups[0].name, null)
    }
    if length(ng.resources) > 0
  ]
}

