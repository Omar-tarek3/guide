output "sg_ids_by_key" { value = { for k, sg in aws_security_group.this : k => sg.id } }
output "sg_arns_by_key" { value = { for k, sg in aws_security_group.this : k => sg.arn } }
output "sg_names_by_key" { value = { for k, sg in aws_security_group.this : k => sg.name } }

output "ingress_rule_ids_by_key" { value = { for k, r in aws_security_group_rule.ingress : k => r.id } }
output "egress_rule_ids_by_key" { value = { for k, r in aws_security_group_rule.egress : k => r.id } }
