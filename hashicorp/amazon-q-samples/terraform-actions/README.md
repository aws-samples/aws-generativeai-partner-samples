# Adding Terraform Actions Context to Amazon Q

This guide explains how to provide Amazon Q with context about Terraform actions for Day 2 operations support. Terraform actions are new additions to the Terraform language that enable infrastructure lifecycle management beyond initial provisioning.

## Method 1: Using the `/context` Command

The simplest way to add Terraform actions context is through Q's built-in context command:

```bash
/context add file://path/to/create_terraform_action.md
```

### Steps:
1. Locate your `create_terraform_action.md` file
2. Use the `/context` command to add it:
   ```bash
   /context add file://hashicorp/amazon-q-samples/terraform-actions/create_terraform_action.md
   ```
3. Verify the context was added:
   ```bash
   /context list
   ```

### Benefits:
- Immediate availability in current session
- Simple one-command setup
- Context persists for the session duration

## Method 2: Custom Agent Configuration

For persistent, automated context loading, create a custom agent:

### Creating the Agent

1. **Start a Q chat session:**
   ```bash
   q chat
   ```

2. **Create a new agent:**
   ```bash
   /agent create --name terraform-actions
   ```

   Amazon Q can also generate the agent configuration for you automatically based on your requirements.

3. **Configure the agent** (opens in your default editor):
   ```json
{
    "name": "terraform-actions",
    "description": "Terraform actions and Day 2 operations specialist",
    "prompt": "You are a Terraform expert specializing in actions and Day 2 operations. Use the provided documentation to help with infrastructure lifecycle management.",
    "tools": [
        "fs_read",
        "execute_bash",
        "use_aws"
    ],
    "allowedTools": [
        "fs_read"
    ],
    "resources": [
        "./hashicorp/amazon-q-samples/terraform-actions/create_terraform_action.md"
    ]
}
   ```

4. **Use the agent:**
   ```bash
   q chat --agent terraform-actions
   ```

### Benefits:
- Persistent context across sessions
- Automatic updates when source file changes
- Reusable configuration
- Can be shared with team members

## Usage Examples

Once context is loaded, you can ask Q about creating a new Terraform action:

```bash
Create a Terraform action called aws_sns_publish_topic
```

## Context File Requirements

Ensure your `create_terraform_action.md` includes:
- Terraform action syntax and structure
- Day 2 operations examples
- Best practices and patterns
- Common use cases and scenarios

Choose Method 1 for quick, session-based context or Method 2 for persistent, production-ready setups.
