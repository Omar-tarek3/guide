//==============================================================================
// iam.tf — Core IAM (control plane & nodes)
//==============================================================================

resource "aws_iam_role" "aws_eks_cluster_role" {
  name = "${local.full_cluster_name}-eks-clusterRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "eks.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-eks-clusterRole"
      Purpose = "Cluster IAM role for ${local.full_cluster_name}"
    }
  )
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policies" {
  for_each = {
    eks_cluster    = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
    vpc_controller = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  }
  role       = aws_iam_role.aws_eks_cluster_role.name
  policy_arn = each.value
}

resource "aws_iam_role" "aws_eks_node_role" {
  name = "${local.full_cluster_name}-eks-nodeRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "ec2.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-eks-nodeRole"
      Purpose = "IAM role for worker nodes in cluster ${local.full_cluster_name}"
    }
  )
}

# Create custom SSM policy
resource "aws_iam_policy" "ssm_custom_policy" {
  name        = "${local.full_cluster_name}-ssm-custom-policy"
  description = "Custom SSM policy for ${local.full_cluster_name} worker nodes"
  policy      = file("${path.module}/ssm-policy/ssm-policy.json")

  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-ssm-custom-policy"
      Purpose = "Custom SSM policy for worker nodes"
    }
  )
}

# Create custom policies for worker nodes

resource "aws_iam_policy" "custom_policy" {
  name        = "${local.full_cluster_name}-custom-policy"
  description = "Custom  policy for ${local.full_cluster_name} worker nodes"
  policy      = file("${path.module}/custom-policy/custom-policy.json")

  tags = merge(var.default_tags,
    {
      Name    = "${local.full_cluster_name}-custom-policy"
      Purpose = "Custom policies for worker nodes"
    }
  )
}


resource "aws_iam_role_policy_attachment" "node_policies" {
  for_each = {
    worker_node     = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
    ecr_pull        = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
    ssm             = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
    cloudwatch      = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
    cni_policy      = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
    ssm_custom      = aws_iam_policy.ssm_custom_policy.arn
    custom_policies = aws_iam_policy.custom_policy.arn
  }
  role       = aws_iam_role.aws_eks_node_role.name
  policy_arn = each.value
}
