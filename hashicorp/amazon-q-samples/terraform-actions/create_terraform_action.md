# Terraform AWS Provider: Actions Implementation Context

## Core Concept

Terraform Actions enable imperative Day-2 operations within Terraform's declarative model. Actions complement CRUD operations by handling side-effects like cache invalidation, failover, and provisioning tasks. Actions are a new feature so documentation and examples are very limited.

## Key Implementation Requirements

### Action Interface & Naming
- Implement `action.ActionWithConfigure` (or `action.Action` if no configuration).
- Use naming convention: `aws_<service>_<action>` (e.g., `aws_ses_send_email`).
- Annotate with `@Action(aws_service_action, name="Display Name")`.

### Framework Integration
- Extend `framework.ActionWithModel[ModelType]`.
- Actions are built on the Plugin Framework (not plugin SDK).  
  ↳ Look to framework-based resources for examples of schemas, models, and types.
  - Example: internal/service/cloudfront/vpc_origin.go
  - Example: internal/service/ec2/vpc_route_server_peer.go
- Region is automatically injected — include `Region types.String` in the model; `region` injection can be disabled in service package registration only when action is global.

### Schema & Types
- Use `schema.UnlinkedSchema` for action schemas.
- Keep schemas flat (no nested objects). Protocol v5 does not support nested `SingleNestedAttribute`.
- For lists of strings:  
  - Schema: `fwtypes.ListOfStringType`  
  - Model: `fwtypes.ListValueOf[types.String]`

### Data Handling
- Convert framework lists to Go slices with:  
  `fwflex.ExpandFrameworkStringValueList(ctx, field)`
- If possible use AutoFlex to transfer data to/from models and AWS types:

Example of using Autoflex in a resource (adjust for action):
```go
	var data vpcRouteServerPeerResourceModel
	response.Diagnostics.Append(request.Plan.Get(ctx, &data)...)
	if response.Diagnostics.HasError() {
		return
	}

	var input ec2.CreateRouteServerPeerInput
	response.Diagnostics.Append(fwflex.Expand(ctx, data, &input)...)
	if response.Diagnostics.HasError() {
		return
	}
```

### Configuration in Terraform
- Actions must use the `config` meta block:

```terraform
action "aws_ec2_stop_instance" "test" {
  config {
    instance_id = aws_instance.test.id
  }
}
```

Without `config`, you’ll get `Unsupported argument` errors.

### Triggering Actions in Tests

Use `terraform_data` to trigger actions in acceptance tests:

```terraform
resource "terraform_data" "trigger" {
  lifecycle {
    action_trigger {
      events  = [before_create, before_update]
      actions = [action.aws_lambda_invoke.test]
    }
  }
}
```

### Common Pitfalls

* Missing `Region` field → schema validation error.
* Wrong list types → `MISSING TYPE` error.
* Using `nil` instead of `basetypes.ObjectAsOptions{}` in `.As()` calls.

### Testing

* Actions require `TF_ACC=1` for acceptance tests.
* Focus tests on schema validation and API call success.