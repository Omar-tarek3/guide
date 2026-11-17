//==============================================================================
// sg.tf — Security groups for EKS control plane & worker nodes
//==============================================================================

# Control plane SG (attached to EKS control plane ENIs)
resource "aws_security_group" "eks_cluster_control_plane_sg" {
  name                   = "${local.sanitized_cluster_name}-eks-control-plane-sg"
  description            = "EKS control plane"
  vpc_id                 = var.vpc_id
  revoke_rules_on_delete = true
  tags = merge(var.default_tags, {
    Name    = lower("${local.full_cluster_name}-ControlPlane-SG")
    Purpose = "EKS ${local.full_cluster_name} Control Plane SG"
  })
}

# Worker node SG (attached to EC2 instances in node groups)
resource "aws_security_group" "eks_cluster_worker_node_sg" {
  name                   = "${local.sanitized_cluster_name}-eks-worker-node-sg"
  description            = "EKS worker nodes"
  vpc_id                 = var.vpc_id
  revoke_rules_on_delete = true
  tags = merge(var.default_tags, {
    Name    = lower("${local.full_cluster_name}-WorkerNodes-SG")
    Purpose = "EKS ${local.full_cluster_name} Worker Nodes SG"
  })
}

#------------------------------------------------------------------------------
# Control plane <-> Worker rules
#------------------------------------------------------------------------------

# Control plane -> workers (kubelet on 10250-65535)
resource "aws_security_group_rule" "cp_to_workers_kubelet" {
  type                     = "egress"
  protocol                 = "tcp"
  from_port                = 10250
  to_port                  = 65535
  security_group_id        = aws_security_group.eks_cluster_control_plane_sg.id
  source_security_group_id = aws_security_group.eks_cluster_worker_node_sg.id
  description              = "Control plane to workers: kubelet (10250-65535)"
}

# Workers -> control plane (HTTPS 443) — workers call API server
resource "aws_security_group_rule" "cp_from_workers_https_inbound" {
  type                     = "ingress"
  protocol                 = "tcp"
  from_port                = 443
  to_port                  = 443
  security_group_id        = aws_security_group.eks_cluster_control_plane_sg.id
  source_security_group_id = aws_security_group.eks_cluster_worker_node_sg.id
  description              = "Control plane from workers: API server (443)"
}

# Workers -> control plane (HTTPS 443) — outbound from workers to API server
resource "aws_security_group_rule" "workers_to_cp_https_outbound" {
  type                     = "egress"
  protocol                 = "tcp"
  from_port                = 443
  to_port                  = 443
  security_group_id        = aws_security_group.eks_cluster_worker_node_sg.id
  source_security_group_id = aws_security_group.eks_cluster_control_plane_sg.id
  description              = "Workers to control plane: API server (443)"
}

# Control plane -> workers (kubelet 10250-65535) must be allowed INBOUND on workers too
resource "aws_security_group_rule" "workers_from_cp_kubelet_inbound" {
  type                     = "ingress"
  protocol                 = "tcp"
  from_port                = 10250
  to_port                  = 65535
  security_group_id        = aws_security_group.eks_cluster_worker_node_sg.id
  source_security_group_id = aws_security_group.eks_cluster_control_plane_sg.id
  description              = "Workers from control plane: kubelet (10250-65535)"
}

# Workers -> control plane (HTTPS 443) must be allowed INBOUND on workers too
resource "aws_security_group_rule" "workers_from_cp_https_inbound" {
  type                     = "ingress"
  protocol                 = "tcp"
  from_port                = 443
  to_port                  = 443
  security_group_id        = aws_security_group.eks_cluster_worker_node_sg.id
  source_security_group_id = aws_security_group.eks_cluster_control_plane_sg.id
  description              = "Workers from control plane: HTTPS (443)"
}

# ----------------------------------------------------------------------------------
# Additional rules for port 9443 (bidirectional between control plane and workers)
# Used by AWS Load Balancer Controller webhook and other components
# ----------------------------------------------------------------------------------

# Control plane -> workers (egress) on port 9443
resource "aws_security_group_rule" "cp_to_workers_9443_egress" {
  type                     = "egress"
  protocol                 = "tcp"
  from_port                = 9443
  to_port                  = 9443
  security_group_id        = aws_security_group.eks_cluster_control_plane_sg.id
  source_security_group_id = aws_security_group.eks_cluster_worker_node_sg.id
  description              = "Control plane to workers: webhook / custom services (9443)"
}

# Workers -> control plane (ingress) on port 9443
resource "aws_security_group_rule" "cp_from_workers_9443_ingress" {
  type                     = "ingress"
  protocol                 = "tcp"
  from_port                = 9443
  to_port                  = 9443
  security_group_id        = aws_security_group.eks_cluster_control_plane_sg.id
  source_security_group_id = aws_security_group.eks_cluster_worker_node_sg.id
  description              = "Control plane from workers: webhook / custom services (9443)"
}

# Workers -> control plane (egress) on port 9443
resource "aws_security_group_rule" "workers_to_cp_9443_egress" {
  type                     = "egress"
  protocol                 = "tcp"
  from_port                = 9443
  to_port                  = 9443
  security_group_id        = aws_security_group.eks_cluster_worker_node_sg.id
  source_security_group_id = aws_security_group.eks_cluster_control_plane_sg.id
  description              = "Workers to control plane: webhook / custom services (9443)"
}

# Control plane -> workers (ingress) on port 9443
resource "aws_security_group_rule" "workers_from_cp_9443_ingress" {
  type                     = "ingress"
  protocol                 = "tcp"
  from_port                = 9443
  to_port                  = 9443
  security_group_id        = aws_security_group.eks_cluster_worker_node_sg.id
  source_security_group_id = aws_security_group.eks_cluster_control_plane_sg.id
  description              = "Workers from control plane: webhook / custom services (9443)"
}


#------------------------------------------------------------------------------
# Worker node general rules
#------------------------------------------------------------------------------

# Node-to-node traffic within the worker SG (pods/nodes need to talk freely)
resource "aws_security_group_rule" "worker_intra_node_all" {
  type                     = "ingress"
  protocol                 = "-1"
  from_port                = 0
  to_port                  = 0
  security_group_id        = aws_security_group.eks_cluster_worker_node_sg.id
  source_security_group_id = aws_security_group.eks_cluster_worker_node_sg.id
  description              = "Workers: allow all intra-node/Pod traffic (self)"
}

# Worker egress — allow outbound (to NAT/ECR/S3/etc.)
resource "aws_security_group_rule" "worker_egress_all" {
  type              = "egress"
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.eks_cluster_worker_node_sg.id
  description       = "Workers: outbound to internet (via NAT or egress path)"
}

#------------------------------------------------------------------------------
# Optional extras (NodePorts, custom CIDRs, etc.) via variable hook
#------------------------------------------------------------------------------

resource "aws_security_group_rule" "extra_worker_rules" {
  for_each                 = { for i, r in var.extra_worker_sg_rules : i => r }
  type                     = each.value.type
  protocol                 = each.value.protocol
  from_port                = each.value.from_port
  to_port                  = each.value.to_port
  security_group_id        = aws_security_group.eks_cluster_worker_node_sg.id
  cidr_blocks              = try(each.value.cidr_blocks, null)
  ipv6_cidr_blocks         = try(each.value.ipv6_cidr_blocks, null)
  source_security_group_id = try(each.value.security_groups[0], null)
  description              = try(each.value.description, "extra rule")
}
