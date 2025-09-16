# Using Amazon Q for Terraform Module Testing

This directory contains specialized rules for Amazon Q to generate comprehensive unit tests for Terraform modules.

## Quick Start

1. **Navigate to your Terraform module directory**
   ```bash
   cd /path/to/your/terraform-module
   ```

2. **Ask Q to generate tests**
   ```
   Create comprehensive unit tests for this Terraform module
   ```

3. **Q will automatically:**
   - Check Terraform version and enable parallel execution (1.12+)
   - Inventory all resources in the module
   - Generate complete `.tftest.hcl` files
   - Run `terraform test` to validate

## What Q Will Create

- `tests/` directory with organized test files
- Complete resource coverage (100% of module resources)
- Mock providers for external dependencies
- Plan-based tests (fast, no real resources)
- Parallel execution for Terraform 1.12+

## Rules Overview

The `.amazonq/rules/` directory contains:

- **01_testing_master.md** - Main coordination and workflow
- **02_test_strategy.md** - Development phases and requirements
- **03_test_patterns.md** - Test code patterns and examples
- **04_mock_patterns.md** - Provider mocking strategies
- **05_parallel_execution.md** - Performance optimization
- **06_quality_checklist.md** - Validation requirements
- **07_troubleshooting.md** - Common issues and solutions

## Key Features

✅ **100% Resource Coverage** - Every resource in your module gets tested  
✅ **Default Behavior Testing** - Validates actual module defaults  
✅ **Security Validation** - Tests IAM policies, encryption, security groups  
✅ **Dependency Testing** - Validates resource relationships  
✅ **Performance Optimized** - Parallel execution and plan-based tests  

## Example Usage

```
# Generate tests for AWS VPC module
"Create unit tests for this VPC module with complete resource coverage"

# Generate tests with specific focus
"Create Terraform tests focusing on security configurations and IAM policies"

# Troubleshoot existing tests
"Fix the failing Terraform tests and ensure 100% resource coverage"
```

## Expected Output

Q will deliver:
1. Working `.tftest.hcl` files in `tests/` directory
2. Successful `terraform test` execution proof
3. Documentation of coverage and any workarounds used
4. All tests passing with complete resource validation

## Requirements

- Terraform >= 1.0.7 (1.12+ recommended for parallel execution)
- AWS provider >= 5.0.0
- Module must be in current working directory

Start by simply asking Q to create tests for your module - the rules handle the rest automatically.
