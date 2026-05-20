# Lessons Learned: Deploying Agents to Databricks Model Serving

Issues encountered and resolved during Phase 2 agent deployment.

---

## 1. Model Serving containers have no implicit auth

**Problem**: `WorkspaceClient()` with no arguments fails inside Model Serving containers with:
```
ValueError: default auth: cannot configure default credentials
```

**Root cause**: Unlike Databricks notebooks (which inherit the user's credentials), Model Serving containers run in isolated environments with no implicit workspace authentication.

**Solution**: Pass OAuth credentials as `environment_vars` in the `ServedEntityInput`:
```python
ServedEntityInput(
    entity_name=model_name,
    entity_version="1",
    scale_to_zero_enabled=True,
    workload_size="Small",
    environment_vars={
        "DATABRICKS_HOST": "https://...",
        "DATABRICKS_CLIENT_ID": "...",
        "DATABRICKS_CLIENT_SECRET": "...",
    },
)
```

And in the agent code, read from env vars:
```python
def load_context(self, context):
    import os
    from databricks.sdk import WorkspaceClient

    host = os.environ.get("DATABRICKS_HOST", "")
    if host:
        self.ws = WorkspaceClient(
            host=host,
            client_id=os.environ.get("DATABRICKS_CLIENT_ID", ""),
            client_secret=os.environ.get("DATABRICKS_CLIENT_SECRET", ""),
        )
    else:
        self.ws = WorkspaceClient()
```

---

## 2. Agent code must be self-contained (no local imports)

**Problem**: MLflow code-based logging uploads only the single agent file. Any imports from local project modules (e.g., `from databricks_agents.data_analyst.prompts import SYSTEM_PROMPT`) fail at serving time with `ModuleNotFoundError`.

**Solution**: Inline everything into the agent file — system prompts, constants, helper functions. The file logged via `mlflow.pyfunc.log_model(python_model="path/to/agent.py")` must be fully self-contained.

---

## 3. MLflow requires `mlflow.models.set_model()` for code-based logging

**Problem**: Without `mlflow.models.set_model(MyAgent())` at the bottom of the agent file, MLflow raises:
```
MlflowException: If the model is logged as code, ensure the model is set using mlflow.models.set_model()
```

**Solution**: Add at the bottom of every agent file:
```python
mlflow.models.set_model(DataAnalystAgent())
```

---

## 4. Unity Catalog models require a signature

**Problem**: Registering a model to UC without a signature fails:
```
MlflowException: Model passed for registration did not contain any signature metadata
```

**Solution**: Use `mlflow.models.rag_signatures` to create a ChatCompletion-compatible signature:
```python
from mlflow.models.rag_signatures import ChatCompletionRequest, ChatCompletionResponse
from mlflow.models.signature import ModelSignature
from mlflow.types.schema import convert_dataclass_to_schema

signature = ModelSignature(
    inputs=convert_dataclass_to_schema(ChatCompletionRequest),
    outputs=convert_dataclass_to_schema(ChatCompletionResponse),
)
```

---

## 5. `agents.deploy()` vs direct SDK — use SDK for more control

**Problem**: `databricks.agents.deploy()` failed with:
```
InvalidParameterValue: Scale to zero must be enabled... workloadSizeId is undefined
```
It also adds a feedback model and has strict schema validation requirements.

**Solution**: Use the Databricks SDK directly for endpoint creation:
```python
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

ws.serving_endpoints.create(
    name=endpoint_name,
    config=EndpointCoreConfigInput(
        name=endpoint_name,
        served_entities=[
            ServedEntityInput(
                entity_name=model_name,
                entity_version="1",
                scale_to_zero_enabled=True,
                workload_size="Small",
                environment_vars=env_vars,
            )
        ],
    ),
)
```

This gives full control over workload size, env vars, and avoids the `agents.deploy()` schema compatibility checks.

---

## 6. OAuth M2M with SQL Connector (v4.x)

**Problem**: The `credentials_provider` pattern documented for older versions doesn't work cleanly with `databricks-sql-connector` v4.x:
```
Error: 'dict' object is not callable
```

**Solution**: Get the token via the SDK and pass it directly:
```python
from databricks.sdk import WorkspaceClient

ws = WorkspaceClient(host=host, client_id=client_id, client_secret=client_secret)
headers = ws.config.authenticate()
token = headers["Authorization"].replace("Bearer ", "")

conn = databricks_sql.connect(
    server_hostname=host,
    http_path=f"/sql/1.0/warehouses/{warehouse_id}",
    access_token=token,
)
```

Note: Token is short-lived (1 hour). For long-running scripts, re-fetch before expiry.

---

## 7. Service Principal permissions checklist

The SP needs these permissions (grant as workspace admin):

| Permission | What it enables |
|-----------|----------------|
| `GRANT CAN_USE ON SQL WAREHOUSE` | Execute queries |
| `GRANT CREATE CATALOG ON METASTORE` | Create new catalogs (data generation) |
| Workspace "users" group membership | MLflow experiment creation |
| SP home directory exists | Auto-created when added to workspace |

---

## 8. MLflow experiment path for Service Principals

**Problem**: Creating experiments at workspace root (`/experiment-name`) fails:
```
PERMISSION_DENIED: does not have read permission for node with aclPath /workspace
```

**Solution**: Use the SP's home directory:
```python
experiment_name = f"/Users/{client_id}/{endpoint_name}"
mlflow.set_experiment(experiment_name)
```

---

## 9. MLflow + OAuth M2M environment setup

**Problem**: MLflow tracking URI `"databricks"` doesn't auto-detect OAuth M2M credentials.

**Solution**: Set environment variables before importing MLflow:
```python
import os
os.environ["DATABRICKS_HOST"] = settings.databricks.host
os.environ["DATABRICKS_CLIENT_ID"] = settings.databricks.client_id
os.environ["DATABRICKS_CLIENT_SECRET"] = settings.databricks.client_secret

import mlflow  # Must import AFTER env vars are set
```

---

## Summary: Deployment Recipe

A successful Model Serving deployment requires:
1. Self-contained agent `.py` file with `mlflow.models.set_model()` at the bottom
2. ChatCompletion-compatible MLflow signature
3. Environment variables passed via `ServedEntityInput.environment_vars`
4. Direct SDK endpoint creation (not `agents.deploy()`) for full control
5. MLflow env vars set before import for OAuth M2M auth

---

# Lessons Learned: Amazon Bedrock AgentCore Gateway Setup

Issues encountered and resolved while configuring AgentCore Gateway to route to Databricks serving endpoints.

---

## 10. Use `gatewayId` (not name) for API calls

**Problem**: Using the gateway name as `gatewayIdentifier` in `create_gateway_target` returns `AccessDeniedException` even with `AdministratorAccess`.

```python
# FAILS with AccessDeniedException
agentcore.create_gateway_target(gatewayIdentifier="finserv-multi-agent-gateway", ...)

# WORKS
agentcore.create_gateway_target(gatewayIdentifier="finserv-multi-agent-gateway-vabirxeraz", ...)
```

**Root cause**: The API requires the full `gatewayId` (which includes a random suffix), not the human-readable name. The `gatewayId` is returned in the `list_gateways()` response.

**Solution**: After creating a gateway, use `list_gateways()` to get the `gatewayId` field, and use that for all subsequent API calls.

---

## 11. Credential provider vendor casing matters

**Problem**: `credentialProviderVendor` value is case-sensitive:
```
"CustomOAuth2"  → ValidationException (invalid enum)
"CustomOauth2"  → Works
```

**Solution**: Use exact enum values. Valid options include:
`CustomOauth2`, `GoogleOauth2`, `GithubOauth2`, `SlackOauth2`, `SalesforceOauth2`, `MicrosoftOauth2`, `AtlassianOauth2`, `LinkedinOauth2`, `CognitoOauth2`, `Auth0Oauth2`, `OktaOauth2`, etc.

---

## 12. OAuth provider config field casing

**Problem**: The nested config key is `customOauth2ProviderConfig` (lowercase 'a' in Oauth), not `customOAuth2ProviderConfig`.

```python
# FAILS
oauth2ProviderConfigInput={"customOAuth2ProviderConfig": {...}}

# WORKS
oauth2ProviderConfigInput={"customOauth2ProviderConfig": {...}}
```

**Solution**: Always match the exact casing from the boto3 parameter validation error message — it lists the valid field names.

---

## 13. `credentialProviderConfigurations` is required for targets

**Problem**: Creating a gateway target without `credentialProviderConfigurations` fails:
```
ValidationException: Credential provider configurations is not defined
```

**Solution**: Always include `credentialProviderConfigurations` when creating a target, even for OpenAPI targets. For Databricks OAuth:
```python
credentialProviderConfigurations=[{
    "credentialProviderType": "OAUTH",
    "credentialProvider": {
        "oauthCredentialProvider": {
            "providerArn": "<credential-provider-arn>",
            "grantType": "CLIENT_CREDENTIALS",
            "scopes": ["all-apis"],
        }
    }
}]
```

---

## 14. AWS credential chain override in Claude Code environment

**Problem**: The `AWS_PROFILE=claude-code-DO-NOT-DELETE` environment variable is set by the Claude Code runtime, overriding any `aws configure` changes or `~/.aws/credentials` updates.

**Solution**: Use explicit credentials from `.env` and create a `boto3.Session` directly:
```python
session = boto3.Session(
    aws_access_key_id=settings.aws.aws_access_key_id,
    aws_secret_access_key=settings.aws.aws_secret_access_key,
    region_name=settings.aws.aws_region,
)
client = session.client("bedrock-agentcore-control")
```

This bypasses the environment variable chain entirely.

---

## 15. Gateway IAM role naming for PassRole

**Problem**: The `BedrockAgentCoreFullAccess` policy only allows `iam:PassRole` for roles with "BedrockAgentCore" in the name:
```json
"Resource": "arn:aws:iam::*:role/*BedrockAgentCore*"
```

**Solution**: Include "BedrockAgentCore" in your gateway service role name, OR add a separate PassRole policy. Our role `agentcore-gateway-finserv-multi-agent-gateway-role` worked because `create_gateway` was called before PassRole was needed.

---

## 16. OpenAPI spec requirements for Gateway targets

The OpenAPI spec provided to `create_gateway_target` must:
- Use OpenAPI 3.0 (not Swagger 2.0)
- Include `operationId` for each operation (becomes the MCP tool name)
- Have `servers[].url` pointing to the actual endpoint base URL
- Use `application/json` content type
- Can be provided inline via `inlinePayload` (JSON string) or from S3

```python
targetConfiguration={
    "mcp": {
        "openApiSchema": {
            "inlinePayload": json.dumps(openapi_spec)
        }
    }
}
```

---

## 17. Databricks OAuth discovery URL for AgentCore

When creating the OAuth credential provider for Databricks, the discovery URL is:
```
https://<workspace>.cloud.databricks.com/oidc/.well-known/openid-configuration
```

This tells AgentCore where to fetch tokens. The Gateway will automatically:
1. Request a token using client credentials
2. Cache it (1 hour lifetime)
3. Refresh before expiry
4. Attach it to outbound requests to Databricks

---

## 18. Gateway IAM role needs Secrets Manager access for OAuth

**Problem**: After creating the Gateway, OAuth credential provider, and targets (all showing `READY`), calling `tools/call` returns:
```json
{"isError": true, "content": [{"text": "An internal error occurred. Please retry later."}]}
```
The response comes back in <1 second (too fast to have reached Databricks).

**Root cause**: The Gateway's service IAM role couldn't read the OAuth client secret from Secrets Manager. When you create an OAuth credential provider, AgentCore stores the client_secret in:
```
arn:aws:secretsmanager:<region>:<account>:secret:bedrock-agentcore-identity!default/oauth2/<provider-name>-<random>
```

The Gateway role needs `secretsmanager:GetSecretValue` on this secret to perform the OAuth token exchange.

**Solution**: Add an inline policy to the Gateway's IAM role:
```python
iam.put_role_policy(
    RoleName="agentcore-gateway-<name>-role",
    PolicyName="GatewaySecretsAndAgentCore",
    PolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
            "Resource": "arn:aws:secretsmanager:<region>:<account>:secret:bedrock-agentcore*"
        }]
    }),
)
```

**Symptom to watch for**: `tools/list` works (no auth needed), but `tools/call` fails with internal error in <1 second. This means the Gateway can't obtain an outbound token.

---

## 19. Gateway timeout for slow agents

**Problem**: Agents that take >300 seconds to respond cause a `ReadTimeout` on the client side and possibly a Gateway-side timeout.

**Root cause**: The Databricks-hosted agents (especially Validator with multiple MCP tool calls + LLM reasoning loops) can take 60-300+ seconds. The Gateway may have its own timeout limit.

**Workaround**: 
- Optimize agent prompts to reduce LLM iterations
- Use a faster model (or reduce tool-call depth)
- Increase client-side timeout
- For the demo, use simpler queries that the Data Analyst can answer in one iteration

**Note**: The Data Analyst agent responded in 62.6s through the Gateway — this is acceptable. The Validator's multi-tool loop needs prompt optimization.

---

## 20. SigV4 authentication for Gateway MCP endpoint

**Problem**: The AgentCore Gateway MCP endpoint requires AWS SigV4 authentication, not a simple Bearer token.

**Solution**: Sign requests using `botocore.auth.SigV4Auth`:
```python
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

credentials = session.get_credentials().get_frozen_credentials()
request = AWSRequest(
    method="POST",
    url=gateway_url,
    data=json.dumps(payload),
    headers={"Content-Type": "application/json"},
)
SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)

resp = requests.post(gateway_url, data=json.dumps(payload), headers=dict(request.headers))
```

The service name for signing is `bedrock-agentcore` (not `bedrock` or `execute-api`).

---

## 21. MCP tool names include target prefix

**Problem**: Tool names exposed through the Gateway are prefixed with the target name and separator `___`:
```
databricks-finserv-data-analyst___invoke_finserv_data_analyst
```
Not just `invoke_finserv_data_analyst` as defined in the OpenAPI spec's `operationId`.

**Implication**: When calling `tools/call`, use the full prefixed name. This allows the Gateway to route to the correct target when multiple targets expose tools with the same operation name.

---

## Summary: AgentCore Gateway Setup Recipe

1. Create IAM role with `bedrock-agentcore.amazonaws.com` trust policy
2. **Add Secrets Manager permissions** to the role (`secretsmanager:GetSecretValue` on `bedrock-agentcore*` secrets)
3. Create Gateway (`create_gateway`) — note the `gatewayId` from response
4. Create OAuth credential provider (`create_oauth2_credential_provider`) with `CustomOauth2` vendor
5. Create targets (`create_gateway_target`) using `gatewayId` (not name) with:
   - Inline OpenAPI spec (operationId becomes tool name)
   - Credential provider ARN + CLIENT_CREDENTIALS grant type
6. Wait for targets to become READY
7. Connect agents to Gateway MCP endpoint: `https://<gatewayId>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp`
8. Authenticate with SigV4 (service: `bedrock-agentcore`)
9. Tools are named: `<target-name>___<operationId>`

## Gateway Test Results

| Test | Result | Time | Notes |
|------|--------|------|-------|
| `tools/list` | PASS | <1s | Returns all tools from all targets |
| `tools/call` Data Analyst | PASS | 62.6s | Correctly queried Databricks lakehouse |
| `tools/call` Validator | Timeout | >300s | Agent too slow (prompt optimization needed) |
