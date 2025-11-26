#!/bin/bash

# Deploy RIV Metadata AI Orchestrator to AWS Bedrock AgentCore

pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit

agentcore configure -e src/orchestrator/agent.py

agentcore launch
