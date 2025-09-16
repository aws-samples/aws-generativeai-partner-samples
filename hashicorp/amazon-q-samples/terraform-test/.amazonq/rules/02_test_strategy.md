# Terraform Test Development Strategy & Requirements

## MUST Requirements
- **MUST create `tests/` directory structure** - Required directory layout for test organization
- **MUST run `terraform init` before executing any tests**
- **MUST use the `terraform` tool to execute `terraform test` command**
- **MUST check Terraform version and enable parallel execution for version 1.12+**
- **MUST fix any test failures and re-run `terraform test` until all tests pass**
- **MUST provide test execution output as proof of successful validation**
- **MUST start with plan-based tests only unless user specifically requests apply tests**
- **MUST test every single resource defined in the module** - Use `grep -r "^resource " *.tf`
- **MUST validate default behavior** - Test what gets created by default vs. explicit enablement
- **MUST test critical resource attributes** - Not just existence but key configuration values
- **MUST validate security configurations** - Test security group rules, IAM policies, encryption
- **MUST test resource interdependencies** - Verify resources reference each other correctly
- **MUST document any skipped tests with detailed analysis** - Include technical reasons and resolution recommendations

## ⚠️ SKIPPED TESTS DOCUMENTATION REQUIREMENTS
When a test cannot be implemented due to complexity:

### Required Documentation Elements:
1. **Resource Name**: Exact resource identifier
2. **Status**: SKIPPED with reason
3. **Problem Details**: Technical explanation of the issue
4. **Error Messages**: Exact error text encountered
5. **Attempted Solutions**: All approaches tried with results
6. **Impact Assessment**: Coverage percentage impact
7. **Resolution Recommendations**: Steps for manual review/fix
8. **Workaround Used**: How the issue was handled

### Documentation Template:
```markdown
## ⚠️ **SKIPPED TESTS - REQUIRES REVIEW**

### [resource_name] - [ISSUE_TYPE]
**Status**: SKIPPED - Needs manual review and resolution

**Problem Details**: [Technical explanation]

**Failed Test Attempts**: [Code examples with results]

**Impact**: [Coverage impact]

**Recommendation**: [Resolution steps]
```

## Test Development Phases

### Phase 0: Environment Setup (CRITICAL)
1. **Check Terraform version** - `terraform version`
2. **Enable parallel execution** - Add `parallel = true` if Terraform >= 1.12.0 and run blocks are independent
3. **Initialize providers** - `terraform init`

### Phase 1: Complete Resource Inventory (CRITICAL)
1. **Identify ALL resources** - `grep -r "^resource " *.tf`
2. **Test default behavior** - What gets created without any variables
3. **Test resource existence** - `length(resource) == expected_count`
4. **Document actual vs. expected defaults** - Some resources may be created by default

### Phase 2: Individual Resource Tests
1. **One test per resource type** - Focused validation
2. **Basic attribute validation** - Names, types, required fields
3. **Conditional creation** - Test `create_*` flags
4. **Handle complex validation** - Use workarounds for file dependencies

### Phase 3: Integration and Edge Cases
1. **Prefix application** - Test naming patterns
2. **Tags propagation** - Test tag application across resources
3. **Resource configurations** - Test different configuration options
4. **Multi-resource scenarios** - Complex relationships

### Phase 4: Advanced Validation
1. **Attribute validation** - Test critical resource configuration values
2. **Security validation** - Test security group rules, IAM policies, encryption
3. **Data format validation** - Test CIDR blocks, JSON policies using `can()` functions
4. **Naming convention validation** - Test resource naming patterns and tag consistency
5. **Resource dependency validation** - Test ARN references and resource relationships

## Test File Organization
**MUST create `tests/` directory structure:**
```
tests/
├── module_name.tftest.hcl     # Basic tests (start here)
├── module_advanced.tftest.hcl # Advanced tests with mocking
└── README.md                  # Test documentation
```

## Test Structure
See `03_test_patterns.md` for complete test patterns and `04_mock_patterns.md` for provider mocking examples.

## Quality Checklist
See `06_quality_checklist.md` for complete quality requirements and validation criteria.

## Success Criteria
- All tests pass with `terraform test`
- **100% resource coverage** - every resource in the module is tested
- Tests accurately reflect module's default behavior
- Test output shows: `Success! X passed, 0 failed.`

## Troubleshooting
See `07_troubleshooting.md` for common failures, solutions, and key learnings from practice.
