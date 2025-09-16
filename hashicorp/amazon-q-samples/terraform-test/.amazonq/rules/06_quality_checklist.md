# Terraform Test Quality Checklist

## Before Submitting Tests
- [ ] All tests pass with `terraform test`
- [ ] **Every resource in the module is tested** (use `grep -r "^resource " *.tf` to verify)
- [ ] **Terraform version checked and parallel execution enabled for 1.12+ when run blocks are independent**
- [ ] Mock providers for external dependencies
- [ ] Clear, descriptive error messages
- [ ] Tests cover default behavior accurately
- [ ] Complex validation issues are worked around
- [ ] Valuable tests (prefix, tags, configurations) are preserved

## Advanced Validation Requirements
- [ ] Critical resource attributes are validated
- [ ] Security configurations are tested
- [ ] Resource dependencies are verified
- [ ] Naming conventions are validated
- [ ] Data formats are tested with `can()` functions
- [ ] Documentation explains test purpose and coverage

## Test Coverage Categories

### 1. Resource Existence Testing
- [ ] Every resource type is tested for existence
- [ ] Conditional resource creation is validated
- [ ] Array resources have correct counts
- [ ] Default vs. explicit creation behavior is tested

### 2. Resource Attribute Testing
- [ ] Critical configuration values are validated
- [ ] Security-related attributes are tested
- [ ] Performance-related settings are verified
- [ ] Naming patterns are validated

### 3. Resource Dependency Testing
- [ ] ARN references between resources are correct
- [ ] Resource interdependencies are validated
- [ ] Data source dependencies are mocked properly
- [ ] Cross-resource configuration is tested

### 4. Security Configuration Testing
- [ ] Security group rules are validated
- [ ] IAM policy permissions are tested
- [ ] Encryption settings are verified
- [ ] Access control configurations are tested

### 5. Data Format Validation
- [ ] CIDR blocks are valid format
- [ ] JSON policies are valid
- [ ] ARN formats are correct
- [ ] Naming conventions are followed

### 6. Edge Cases and Error Handling
- [ ] Invalid inputs are handled gracefully
- [ ] Complex validation scenarios are tested
- [ ] File dependency workarounds are implemented
- [ ] External resource references are mocked

## Expected Deliverables
1. **Working test file** with `.tftest.hcl` extension covering ALL module resources
2. **Proof of successful execution** via `terraform test` command output using the `terraform` tool
3. **Complete resource coverage** - every resource defined in the module must be tested
4. **Default behavior validation** - accurate testing of what gets created by default
5. **Documentation** explaining complete resource coverage and any workarounds used

## Critical Success Factors
1. **Complete Resource Inventory** - Must identify and test every single resource
2. **Default Behavior Accuracy** - Tests must reflect actual module defaults, not assumptions
3. **Validation Workarounds** - Handle complex module validation without compromising coverage
4. **Preserve Working Tests** - Don't remove valuable tests for features like prefixes, tags, configurations
5. **Iterative Improvement** - Fix issues while maintaining existing working tests

## Test Maintenance Guidelines
- Use descriptive test names
- Clear error messages
- Consistent mock values
- Document complex scenarios
- Regular test execution validation
- Keep tests up-to-date with module changes
