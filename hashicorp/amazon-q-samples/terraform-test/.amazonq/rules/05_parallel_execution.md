# Terraform Parallel Test Execution

## Terraform 1.12+ Parallel Features

### Version Check
Always check Terraform version before enabling parallel execution:
```bash
terraform version
# If >= 1.12.0, parallel execution is available
```

### Option 1: Test Block Configuration
```hcl
test {
  parallel = true  # Default for all run blocks in this file
}

run "test_vpc_creation" {
  command = plan
  # Inherits parallel = true from test block
  
  assert {
    condition = length(aws_vpc.this) == 1
    error_message = "Should create VPC"
  }
}

run "test_subnet_creation" {
  command = plan
  # Inherits parallel = true from test block
  
  variables {
    subnet_cidr_public = ["10.0.1.0/24"]
  }
  
  assert {
    condition = length(aws_subnet.public) == 1
    error_message = "Should create public subnet"
  }
}
```

### Option 2: Individual Run Block Configuration
```hcl
run "test_vpc_creation" {
  command = plan
  parallel = true  # Explicitly set on this run block
  
  assert {
    condition = length(aws_vpc.this) == 1
    error_message = "Should create VPC"
  }
}

run "test_security_groups" {
  command = plan
  parallel = true  # Explicitly set on this run block
  
  assert {
    condition = length(aws_security_group.default) >= 0
    error_message = "Security groups should be handled properly"
  }
}
```

### Sequential Execution for Dependencies
```hcl
run "setup_vpc" {
  command = apply
  parallel = false # Runs sequentially
}

run "test_with_vpc" {
  command = plan
  parallel = false # Cannot be parallel due to dependency
  
  variables {
    vpc_id = run.setup_vpc.vpc_id
  }
  
  assert {
    condition = var.vpc_id != null
    error_message = "Should use VPC from setup"
  }
}
```

## Requirements for Parallel Execution
- Requires Terraform >= 1.12.0
- Run blocks must NOT reference outputs from each other
- Run blocks must NOT share the same state file (use different state keys if needed)
- Both run blocks must have `parallel = true` (either inherited from test block or explicitly set)
- Significantly improves test execution time for large test suites

## Performance Benefits
- **Faster test execution** - Multiple tests run simultaneously
- **Better resource utilization** - Parallel processing of independent tests
- **Improved CI/CD pipeline speed** - Reduced overall test time
- **Scalable testing** - Handles large test suites efficiently

## When NOT to Use Parallel Execution
- Tests that depend on shared state
- Tests that reference outputs from other run blocks
- Tests that modify the same external resources
- Tests with complex interdependencies
- Apply-based tests that create real resources with conflicts