resource "aws_networkfirewall_firewall" "this" {
  count = var.enable_network_firewall ? 1 : 0

  name                = "${var.prefix_name}-${var.firewall_name}"
  firewall_policy_arn = var.firewall_policy_arn
  vpc_id              = aws_vpc.this.id

  # One endpoint per dedicated firewall subnet (Zone="firewall")
  dynamic "subnet_mapping" {
    for_each = toset([
      for s in aws_subnet.subnets : s.id
      if s.tags["Zone"] == "firewall"
    ])
    content {
      subnet_id = subnet_mapping.value
    }
  }
  tags = merge(
    var.default_tags,
    {
      Name    = "${var.prefix_name}-${var.firewall_name}"
      Purpose = "Network Firewall ${var.prefix_name}-${var.firewall_name}"
    }
  )
}
