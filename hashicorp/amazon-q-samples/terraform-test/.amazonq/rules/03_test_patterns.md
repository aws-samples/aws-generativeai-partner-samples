# Terraform Test Patterns

## Single Resource Testing
```hcl
run "test_single_resource" {
  command = plan
  
  assert {
    condition     = aws_vpc.this != null
    error_message = "VPC should be created"
  }
}
```

## Array Resource Testing
```hcl
run "test_array_resources" {
  command = plan
  
  variables {
    subnet_cidr_public = ["10.0.1.0/24", "10.0.2.0/24"]
  }
  
  assert {
    condition     = length(aws_subnet.public) == 2
    error_message = "Should create 2 public subnets"
  }
}
```

## Complete Resource Coverage
```hcl
run "test_all_resources_default" {
  command = plan
  
  # Test EVERY resource - use actual resource names from module
  assert {
    condition     = length(resource_type_1.resource_name) == 0
    error_message = "resource_type_1 should not be created by default"
  }
  
  assert {
    condition     = length(resource_type_2.resource_name) == 1  # May be created by default!
    error_message = "resource_type_2 is created by default (create_flag defaults to true)"
  }
}
```

## Individual Resource Tests
```hcl
run "test_specific_resource" {
  command = plan
  
  variables {
    create_resource = true
    resource_name   = "test_name"
  }
  
  assert {
    condition     = length(resource_type.resource_name) == 1
    error_message = "Should create resource"
  }
  
  assert {
    condition     = resource_type.resource_name[0].name == "test_name"
    error_message = "Resource name should match input"
  }
}
```

## Resource Attribute Testing
```hcl
run "test_resource_attributes" {
  command = plan
  
  variables {
    subnet_cidr_public = ["10.0.1.0/24"]
  }
  
  assert {
    condition     = aws_subnet.public[0].map_public_ip_on_launch == true
    error_message = "Public subnets should auto-assign public IPs"
  }
  
  assert {
    condition     = can(cidrhost(aws_vpc.this.cidr_block, 0))
    error_message = "VPC CIDR should be valid format"
  }
}
```

## Security Configuration Testing
```hcl
run "test_security_config" {
  command = plan
  
  assert {
    condition     = length(aws_default_security_group.default.ingress) == 0
    error_message = "Default security group should have no ingress rules"
  }
  
  assert {
    condition     = length(aws_default_security_group.default.egress) == 0
    error_message = "Default security group should have no egress rules"
  }
}
```

## Resource Dependency Testing
```hcl
run "test_dependencies" {
  command = plan
  
  variables {
    enable_flow_log = true
  }
  
  assert {
    condition     = aws_flow_log.network_flow_logging[0].log_destination == aws_cloudwatch_log_group.network_flow_logging[0].arn
    error_message = "Flow log should reference correct CloudWatch log group"
  }
  
  assert {
    condition     = aws_cloudwatch_log_group.network_flow_logging[0].kms_key_id == aws_kms_key.custom_kms_key[0].arn
    error_message = "CloudWatch log group should use custom KMS key"
  }
}
```

## Data Format Validation Testing
```hcl
run "test_data_formats" {
  command = plan
  
  variables {
    vpc_cidr = "10.0.0.0/16"
    subnet_cidr_public = ["10.0.1.0/24"]
  }
  
  assert {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR should be valid format"
  }
  
  assert {
    condition     = can(regex("^10\\.", var.vpc_cidr))
    error_message = "VPC CIDR should be in private range"
  }
  
  assert {
    condition     = can(jsondecode(data.aws_iam_policy_document.example.json))
    error_message = "IAM policy should be valid JSON"
  }
}
```

## Naming Convention Testing
```hcl
run "test_naming_conventions" {
  command = plan
  
  variables {
    prefix = "test-"
    tags = {
      Environment = "test"
      Project     = "example"
    }
  }
  
  assert {
    condition     = startswith(aws_vpc.this.tags["Name"], var.prefix)
    error_message = "VPC name should start with prefix"
  }
  
  assert {
    condition     = aws_vpc.this.tags["Environment"] == var.tags["Environment"]
    error_message = "VPC should inherit environment tag"
  }
  
  assert {
    condition     = can(regex("^[a-z0-9-]+$", aws_vpc.this.tags["Name"]))
    error_message = "Resource names should follow naming convention"
  }
}
```

## Performance and Optimization Testing
```hcl
run "test_performance_config" {
  command = plan
  
  variables {
    instance_tenancy = "default"
    enable_dns_hostnames = true
    enable_dns_support = true
  }
  
  assert {
    condition     = aws_vpc.this.instance_tenancy == "default"
    error_message = "VPC should use default tenancy for cost optimization"
  }
  
  assert {
    condition     = aws_vpc.this.enable_dns_hostnames == true
    error_message = "DNS hostnames should be enabled for performance"
  }
}
```
