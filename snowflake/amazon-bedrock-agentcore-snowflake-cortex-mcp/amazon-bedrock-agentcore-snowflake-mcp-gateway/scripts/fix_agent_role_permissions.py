"""Add KB + Gateway permissions to the AgentCore Runtime execution role.

The auto-created runtime role only has basic permissions (logs, model invocation, memory).
This script adds bedrock:Retrieve (KB), aoss:APIAccessAll (OpenSearch), and
bedrock-agentcore:InvokeGateway (MCP Gateway).

Run AFTER `agentcore deploy` (which creates the role).

Usage:
  python3 scripts/fix_agent_role_permissions.py --profile accounts-lob
"""
import boto3
import json
import os
import argparse
import yaml

REGION = "us-east-1"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    account_id = session.client("sts").get_caller_identity()["Account"]
    iam_client = session.client("iam")

    # Read runtime role from agent config
    config_path = os.path.join(PROJECT_DIR, "agent", ".bedrock_agentcore.yaml")
    if not os.path.exists(config_path):
        print("❌ agent/.bedrock_agentcore.yaml not found. Run `agentcore deploy` first.")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    agent_name = config.get("default_agent", "")
    role_arn = config.get("agents", {}).get(agent_name, {}).get("aws", {}).get("execution_role", "")
    if not role_arn:
        print("❌ No execution_role found in agent config.")
        return

    role_name = role_arn.split("/")[-1]
    print(f"Adding permissions to: {role_name}")

    policy_doc = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {"Sid": "BedrockKBRetrieve", "Effect": "Allow",
             "Action": ["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
             "Resource": [f"arn:aws:bedrock:{REGION}:{account_id}:knowledge-base/*"]},
            {"Sid": "AOSSAccess", "Effect": "Allow",
             "Action": ["aoss:APIAccessAll"],
             "Resource": [f"arn:aws:aoss:{REGION}:{account_id}:collection/*"]},
            {"Sid": "GatewayInvoke", "Effect": "Allow",
             "Action": ["bedrock-agentcore:InvokeGateway"],
             "Resource": [f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:gateway/*"]},
        ]
    })

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName="CreditRiskAgentPermissions",
        PolicyDocument=policy_doc,
    )
    print(f"✅ Added KB/Gateway/AOSS permissions to {role_name}")


if __name__ == "__main__":
    main()
