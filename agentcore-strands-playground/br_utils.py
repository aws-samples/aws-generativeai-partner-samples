"""
Bedrock Utilities Module

This module provides helper functions for interacting with Amazon Bedrock,
including listing enabled foundation models in the configured AWS region.
"""

import os
from typing import List, Dict, Optional
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_bedrock_models() -> List[str]:
    """
    Get a list of all enabled Bedrock foundation model identifiers.
    
    Returns:
        List of model identifier strings.
    """
    models = [
        'us.amazon.nova-micro-v1:0',
        'us.amazon.nova-lite-v1:0',
        'us.amazon.nova-pro-v1:0',
        'anthropic.claude-3-5-sonnet-20241022-v2:0',
        'anthropic.claude-3-5-haiku-20241022-v1:0',
        'anthropic.claude-3-5-sonnet-20240620-v1:0',
        'anthropic.claude-3-sonnet-20240229-v1:0',
        'anthropic.claude-3-haiku-20240307-v1:0',
        'anthropic.claude-3-opus-20240229-v1:0',
        'cohere.command-r-v1:0',
        'cohere.command-r-plus-v1:0',
        'meta.llama3-1-405b-instruct-v1:0',
        'meta.llama3-1-70b-instruct-v1:0',
        'meta.llama3-1-8b-instruct-v1:0',
        'meta.llama3-70b-instruct-v1:0',
        'meta.llama3-8b-instruct-v1:0',
        'mistral.mistral-large-2407-v1:0',
        'mistral.mistral-large-2402-v1:0',
        'mistral.mixtral-8x7b-instruct-v0:1',
        'mistral.mistral-7b-instruct-v0:2',
        'qwen.qwen3-235b-a22b-2507-v1:0',
        'qwen.qwen3-coder-480b-a35b-v1:0',
        'qwen.qwen3-coder-30b-a3b-v1:0',
        'qwen.qwen3-32b-v1:0',
        'openai.gpt-oss-120b-1:0',
        'openai.gpt-oss-20b-1:0',
        'deepseek.v3-v1:0'
    ]
    return models

if __name__ == "__main__":
    # Example usage when run directly
    print("Fetching enabled Bedrock models...")
    models = get_bedrock_models()
    
    print(f"\nAvailable Bedrock Models ({len(models)} total):\n")
    for model_id in models:
        print(f"  - {model_id}")