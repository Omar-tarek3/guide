/*resource "aws_flow_log" "this" {
  count = lookup(var.flow_log, "traffic_type", null) != null ? 1 : 0
  log_destination               = var.flow_log.log_destination
  log_destination_type          = var.flow_log.log_destination_type
  traffic_type                  = var.flow_log.traffic_type
  eni_id                        = var.flow_log.eni_id
  iam_role_arn                  = var.flow_log.iam_role_arn
  vpc_id                        = aws_vpc.this.id
  subnet_id                     = var.flow_log.subnet_id
  transit_gateway_id            = var.flow_log.transit_gateway_id
  transit_gateway_attachment_id = var.flow_log.transit_gateway_attachment_id
  log_format                    = var.flow_log.log_format
  max_aggregation_interval      = var.flow_log.max_aggregation_interval

  tags = merge(
    var.default_tags,
    {
      Name    = var.prefix_name
      Purpose = "AWS Flow Log for ${var.prefix_name}"
    },
    var.flow_log.tags,
  )
}
*/