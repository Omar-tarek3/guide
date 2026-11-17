//==============================================================================
// lt.tf — Launch templates (one per node-group)
//==============================================================================

resource "aws_launch_template" "node_group_launch_template" {
  for_each = {
    for ng in var.EKS_NODE_GROUP_DEFINITIONS :
    lower("${ng.type}-${ng.suffix}") => ng
  }

  name_prefix            = replace("${local.full_cluster_name}-eks-${each.value.suffix}-lt-", ".", "-")
  image_id               = each.value.ami
  update_default_version = true



  # Use the worker node security group
  vpc_security_group_ids = [aws_security_group.eks_cluster_worker_node_sg.id]

  metadata_options {
    http_tokens                 = "required"
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 2
  }

  user_data = base64encode(
    templatefile("${path.module}/templates/wn-userdata.tpl", {
      CLUSTER_NAME    = aws_eks_cluster.cluster.name
      B64_CLUSTER_CA  = aws_eks_cluster.cluster.certificate_authority[0].data
      API_SERVER_URL  = aws_eks_cluster.cluster.endpoint
      NODE_GROUP_NAME = lower("${local.full_cluster_name}-${each.key}-eks-NodeGroup")
      CAPACITY        = each.value.type
      EC2_AMI         = each.value.ami
    })
  )

  block_device_mappings {
    device_name = try(each.value.device_name, "/dev/xvda")
    ebs {
      volume_size           = try(each.value.root_volume_size, 40)
      encrypted             = try(each.value.encrypted, true)
      delete_on_termination = try(each.value.delete_on_termination, true)
      volume_type           = try(each.value.volume_type, "gp3")
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name    = lower("${local.full_cluster_name}-${each.value.type}-${each.value.suffix}-worker-node")
      Purpose = "launch template for cluster ${local.full_cluster_name}"
    })
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(local.common_tags, {
      Name    = lower("${local.full_cluster_name}-${each.value.type}-${each.value.suffix}-worker-node-volume")
      Purpose = "launch template for cluster ${local.full_cluster_name}"

    })
  }

  tags = merge(local.common_tags, {
    Name    = lower("${local.full_cluster_name}-eks-${each.value.suffix}-lt")
    Purpose = "launch template for cluster ${local.full_cluster_name}"
  })

  depends_on = [aws_eks_cluster.cluster]
}
