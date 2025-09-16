# Terraform Testing Troubleshooting

## Common Failures & Solutions

### Template and Validation Errors
1. **"Invalid template interpolation"** → Add required variables or mock dependencies
2. **"Missing required argument"** → Check module variable requirements and dependencies
3. **"Invalid function argument" (tobool)** → Module has complex validation - use workarounds
4. **"No such file or directory"** → Avoid local file paths, use external locations instead
5. **"Invalid index"** → Verify resource exists before accessing attributes

### Complex Module Validation Issues
1. **File dependency errors** → Use external locations with predefined paths
2. **Type validation errors** → Simplify complex variable structures
3. **Default resource creation** → Some resources may be created by default - adjust tests accordingly

## Performance Optimization

### Test Execution Speed
- Use `command = plan` (not apply)
- Mock external data sources
- Minimize variable complexity
- Group related assertions

### Test Maintenance
- Use descriptive test names
- Clear error messages
- Consistent mock values
- Document complex scenarios

## Key Learnings from Practice
- **Focus on plan-based tests first** - They're faster and don't require real resources
- **Avoid complex dependency chains** - Test individual components in isolation
- **Mock external dependencies** - Use mock providers for predictable test data
- **Handle module validation logic carefully** - Some modules have complex validation that can cause test failures
- **Override blocks work for simple attributes** - Complex computed values may not override properly
- **Mock providers provide defaults** - Input variables still control resource configuration
- **Module defaults matter** - Some resources may be created by default
- **Complex validation requires workarounds** - Use existing resources or external locations to avoid file system dependencies
- **Preserve valuable tests** - Don't remove working tests for prefix, tags, or configuration validation
