# Databricks Workspace Setup Guide

Step-by-step guide to configure a Databricks workspace for the Multi-Agent Financial Analyst.

---

## Prerequisites

- Databricks workspace on AWS (Premium plan or above)
- Workspace administrator access
- A SQL Warehouse (Serverless or Pro recommended)

---

## Step 1: Create a Service Principal

The service principal is the identity your application uses to authenticate with Databricks.

1. Log in to your Databricks workspace as an admin
2. Click your **username** (top-right) → **Settings**
3. Go to **Identity and access** tab
4. Next to "Service principals," click **Manage**
5. Click **Add service principal** → **Add new**
6. Enter a name (e.g., `finserv-analyst-sp`) → click **Add**
7. On the **Configurations** tab, note the **Application ID** — this is your `DATABRICKS_CLIENT_ID`

---

## Step 2: Generate an OAuth Secret

OAuth M2M (machine-to-machine) is the recommended authentication method. It produces short-lived tokens (1 hour) with automatic refresh — more secure than PATs.

1. In Settings → Service principals → select your SP
2. Go to the **Secrets** tab
3. Click **Generate secret**
4. Set a lifetime (up to 2 years)
5. Click **Generate**
6. **Copy the secret value immediately** — it is shown only once
7. This is your `DATABRICKS_CLIENT_SECRET`

---

## Step 3: Get Your Workspace URL

1. Look at the URL in your browser when logged into Databricks
2. It will be something like: `https://dbc-abc123de.cloud.databricks.com` or `https://your-alias.cloud.databricks.com`
3. This is your `DATABRICKS_HOST` (include the `https://`, no trailing slash)

---

## Step 4: Get Your SQL Warehouse ID

1. In the left sidebar, click **SQL Warehouses**
2. Click on the warehouse you want to use (or create a new one)
3. The warehouse ID is visible in:
   - The URL: `.../sql/warehouses/<warehouse-id>`
   - Or click the warehouse name → look in the "Connection details" section
4. This is your `DATABRICKS_WAREHOUSE_ID`

---

## Step 5: Grant the Service Principal Access to the SQL Warehouse

The SP needs "Can Use" permission on the warehouse to execute queries.

1. Go to **SQL Warehouses** → click your warehouse
2. Click the **Permissions** tab (or kebab menu → Manage permissions)
3. Search for your service principal (by Application ID or name)
4. Grant **Can Use** permission
5. Click **Save**

Alternatively, an admin can run this SQL:
```sql
GRANT CAN_USE ON SQL WAREHOUSE `<warehouse-id>` TO `<service-principal-application-id>`;
```

---

## Step 6: Grant the Service Principal Catalog Permissions

After the synthetic data is generated (Step 2 of execution), the SP needs access to the catalog. If the SP creates the catalog itself, it will already be the owner. If another user creates it, run:

```sql
GRANT USE CATALOG ON CATALOG finserv_catalog TO `<service-principal-application-id>`;
GRANT USE SCHEMA ON CATALOG finserv_catalog TO `<service-principal-application-id>`;
GRANT SELECT ON CATALOG finserv_catalog TO `<service-principal-application-id>`;
GRANT CREATE SCHEMA ON CATALOG finserv_catalog TO `<service-principal-application-id>`;
GRANT CREATE TABLE ON CATALOG finserv_catalog TO `<service-principal-application-id>`;
```

For the data generation script to create the catalog itself, the SP needs:
```sql
GRANT CREATE CATALOG ON METASTORE TO `<service-principal-application-id>`;
```

---

## Step 7: Create the `.env` File

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Edit `.env`:
```
DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
DATABRICKS_CLIENT_ID=<application-id-from-step-1>
DATABRICKS_CLIENT_SECRET=<secret-from-step-2>
DATABRICKS_WAREHOUSE_ID=<warehouse-id-from-step-4>
DATABRICKS_CATALOG=finserv_catalog
DATABRICKS_ADMIN_USER=<your-admin-email@example.com>
```

---

## Step 8: Validate Connectivity

Activate the virtual environment and run the validation script:

```bash
.venv/bin/python -m infrastructure.databricks.workspace_setup
```

Expected output when everything is configured correctly:
```
WORKSPACE VALIDATION RESULTS
  [PASS] connection
  [PASS] catalog        ← will be FAIL until you run data generation
  [PASS] schemas        ← will be FAIL until you run data generation
  [PASS] warehouse
  [PASS] mcp
```

The `catalog` and `schemas` checks will fail until you run the data generation script — that's expected.

---

## Configuration Reference

| Environment Variable | Description | Example | Where to Find It |
|---------------------|-------------|---------|-------------------|
| `DATABRICKS_HOST` | Workspace URL | `https://dbc-abc123.cloud.databricks.com` | Browser URL bar when logged in |
| `DATABRICKS_CLIENT_ID` | Service principal Application ID | `5256a2ee-c1c0-4256-a317-8f863ff2e9e9` | Settings → Service principals → Configurations tab |
| `DATABRICKS_CLIENT_SECRET` | OAuth secret for the SP | `dose...` (long string) | Settings → Service principals → Secrets tab → Generate |
| `DATABRICKS_WAREHOUSE_ID` | SQL Warehouse ID | `e1d19de1ed186c46` | SQL Warehouses → click warehouse → Connection details |
| `DATABRICKS_CATALOG` | Unity Catalog name | `finserv_catalog` | Default; created by data generation script |
| `DATABRICKS_ADMIN_USER` | Your admin email for UI access | `you@example.com` | The email you log into the Databricks workspace with |

---

## How OAuth M2M Works (Background)

When you set `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET`:

1. The Databricks SDK calls the workspace's OIDC token endpoint:
   ```
   POST https://<workspace>/oidc/v1/token
   Body: grant_type=client_credentials&scope=all-apis
   Auth: Basic <client_id>:<client_secret>
   ```
2. Databricks returns a short-lived access token (expires in 1 hour)
3. The SDK caches the token and automatically refreshes it before expiry
4. All API calls use `Authorization: Bearer <access_token>`

You never manage tokens manually — the SDK handles everything.

---

## Step 9: Deploy Agents to Model Serving

After data is generated and validated:

```bash
.venv/bin/python -m databricks_agents.deploy_agents
```

This registers the agents in Unity Catalog and creates serving endpoints. Takes 5-10 minutes for containers to start.

Check status: **Serving** (left sidebar) → look for `finserv-data-analyst` and `finserv-validator` → status should be "Ready".

**Important**: The deploy script passes your OAuth credentials (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`, `DATABRICKS_HOST`) as environment variables to the serving container. The agents use these to authenticate with the workspace at runtime.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `is not authorized to use or monitor this SQL Endpoint` | SP lacks warehouse access | Grant "Can Use" on the SQL Warehouse (Step 5) |
| `Catalog 'finserv_catalog' does not exist` | Data not generated yet | Run `python -m data.generate_synthetic` |
| `INVALID_PARAMETER_VALUE: Invalid client_id or client_secret` | Wrong credentials | Verify client_id matches Application ID; regenerate secret if needed |
| `default auth: cannot configure default credentials` (in serving logs) | Serving container has no auth | Redeploy with `environment_vars` in ServedEntityInput |
| `Model server failed to load the model` | Import errors or missing auth | Check Serving → endpoint → Logs tab for stack trace |
| `PERMISSION_DENIED: does not have read permission for /workspace` | SP not in workspace users group | Add SP to the `users` group in Settings → Identity and access → Groups |
| `Warehouse not running` | Warehouse is stopped | It will auto-start on first query; or start it manually in the UI |
| `Unable to resolve host` | Wrong DATABRICKS_HOST | Check URL format — must include `https://`, no trailing slash |
| `Token endpoint returned 401` | Secret expired or revoked | Generate a new secret (Step 2) |

---

## Security Notes

- **Never commit `.env` to git** — it's in `.gitignore`
- OAuth secrets expire (max 2 years) — set a calendar reminder to rotate
- The SP should have **minimum required permissions** — only grant access to catalogs/schemas it needs
- Use Unity Catalog row/column-level security for fine-grained access control
- All MCP tool calls are logged in Databricks AI Gateway for audit
