#!/usr/bin/env python3
"""
Direct LaunchDarkly AI Config creation script to replace MCP tools.
Reads from bootstrap/ai_config_manifest.yaml and creates AI Config + variations.
"""

import os
import yaml
import requests
import json
import time
from pathlib import Path

class LaunchDarklyAIConfigCreator:
    def __init__(self, api_key, base_url="https://app.launchdarkly.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.REQUEST_TIMEOUT = 30  # 30 seconds timeout
        self.headers = {
            "Authorization": api_key,
            "LD-API-Version": "beta",
            "Content-Type": "application/json"
        }

    def create_ai_model_config(self, project_key, model_config_data):
        """Create AI Model Config using direct API call"""
        url = f"{self.base_url}/api/v2/projects/{project_key}/ai-model-configs"
        
        payload = {
            "key": model_config_data["key"],
            "name": model_config_data["name"],
            "provider": model_config_data["provider"],
            "id": model_config_data["id"],
            "costPerInputToken": model_config_data.get("costPerInputToken"),
            "costPerOutputToken": model_config_data.get("costPerOutputToken")
        }
        
        response = requests.post(url, headers=self.headers, json=payload, timeout=self.REQUEST_TIMEOUT)
        
        if response.status_code in [200, 201]:
            print(f"✅ AI Model Config '{model_config_data['key']}' created successfully")
            time.sleep(0.5)  # Rate limiting delay
            return response.json()
        elif response.status_code == 409:
            print(f"⚠️  AI Model Config '{model_config_data['key']}' already exists")
            return None
        elif response.status_code == 429:
            print(f"⏳ Rate limited, waiting 2 seconds...")
            time.sleep(2)
            return self.create_ai_model_config(project_key, model_config_data)
        else:
            print(f"❌ Failed to create AI Model Config '{model_config_data['key']}': {response.status_code} - {response.text}")
            return None

    def create_ai_config(self, project_key, config_data):
        """Create AI Config using direct API call"""
        url = f"{self.base_url}/api/v2/projects/{project_key}/ai-configs"
        
        payload = {
            "key": config_data["key"],
            "name": config_data.get("name", config_data["key"]),
            "mode": "completion"
        }
        
        if "description" in config_data:
            payload["description"] = config_data["description"]
            
        response = requests.post(url, headers=self.headers, json=payload, timeout=self.REQUEST_TIMEOUT)
        
        if response.status_code == 201:
            print(f"✅ AI Config '{config_data['key']}' created successfully")
            return response.json()
        elif response.status_code == 409 or (response.status_code == 400 and "enabled" in response.text):
            print(f"⚠️  AI Config '{config_data['key']}' already exists")
            return self.get_ai_config(project_key, config_data["key"])
        else:
            print(f"❌ Failed to create AI Config: {response.status_code} - {response.text}")
            return None

    def get_ai_config(self, project_key, config_key):
        """Get existing AI Config"""
        url = f"{self.base_url}/api/v2/projects/{project_key}/ai-configs/{config_key}"
        response = requests.get(url, headers=self.headers, timeout=self.REQUEST_TIMEOUT)
        return response.json() if response.status_code == 200 else None

    def get_segment(self, project_key, environment_key, segment_key):
        """Get existing segment"""
        url = f"{self.base_url}/api/v2/segments/{project_key}/{environment_key}/{segment_key}"
        response = requests.get(url, headers=self.headers, timeout=self.REQUEST_TIMEOUT)
        return response.json() if response.status_code == 200 else None

    def create_variation(self, project_key, config_key, variation_data):
        """Create AI Config variation using direct API call"""
        url = f"{self.base_url}/api/v2/projects/{project_key}/ai-configs/{config_key}/variations"
        
        # Read system prompt from file
        prompt_file = Path("../fallback_prompts") / variation_data["system_prompt_source"].split("/")[-1]
        if not prompt_file.exists():
            print(f"❌ Prompt file not found: {prompt_file}")
            return None
            
        system_prompt = prompt_file.read_text(encoding="utf-8").strip()
        
        payload = {
            "key": variation_data["key"],
            "name": variation_data["key"].replace("-", " ").replace("_", " ").title(),
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]
        }
        
        # Add model config key if specified
        if "model_config_key" in variation_data:
            payload["modelConfigKey"] = variation_data["model_config_key"]
            
        response = requests.post(url, headers=self.headers, json=payload, timeout=self.REQUEST_TIMEOUT)
        
        if response.status_code == 201:
            print(f"✅ Variation '{variation_data['key']}' created successfully")
            time.sleep(0.5)  # Rate limiting delay
            return response.json()
        elif response.status_code == 409:
            print(f"⚠️  Variation '{variation_data['key']}' already exists")
            return None
        elif response.status_code == 429:
            print(f"⏳ Rate limited, waiting 2 seconds...")
            time.sleep(2)
            return self.create_variation(project_key, config_key, variation_data)  # Retry
        else:
            print(f"❌ Failed to create variation '{variation_data['key']}': {response.status_code} - {response.text}")
            return None

    def create_segment(self, project_key, environment_key, segment_data):
        """Create segment using direct API call"""
        url = f"{self.base_url}/api/v2/segments/{project_key}/{environment_key}"
        
        # Create segment without rules first
        payload = {
            "key": segment_data["key"],
            "name": segment_data["key"].replace("-", " ").replace("_", " ").title(),
            "description": f"Segment for {segment_data['key']}"
        }
        
        response = requests.post(url, headers=self.headers, json=payload, timeout=self.REQUEST_TIMEOUT)
        
        if response.status_code == 201:
            print(f"✅ Segment '{segment_data['key']}' created successfully")
            segment_result = response.json()
            
            # Add rules via PATCH if specified
            if "rules" in segment_data and segment_data["rules"]:
                self.add_segment_rules(project_key, environment_key, segment_data["key"], segment_data["rules"])
            
            time.sleep(0.5)  # Rate limiting delay
            return segment_result
        elif response.status_code == 409:
            print(f"⚠️  Segment '{segment_data['key']}' already exists")
            return self.get_segment(project_key, environment_key, segment_data["key"])
        elif response.status_code == 429:
            print(f"⏳ Rate limited, waiting 2 seconds...")
            time.sleep(2)
            return self.create_segment(project_key, environment_key, segment_data)  # Retry
        else:
            print(f"❌ Failed to create segment '{segment_data['key']}': {response.status_code} - {response.text}")
            return None

    def add_segment_rules(self, project_key, environment_key, segment_key, rules):
        """Add rules to segment using PATCH API"""
        url = f"{self.base_url}/api/v2/segments/{project_key}/{environment_key}/{segment_key}"
        
        # Build JSON Patch operations to add rules
        patch_operations = []
        for rule in rules:
            rule_value = {
                "clauses": [{
                    "attribute": rule["attribute"],
                    "op": rule["op"],
                    "values": rule["values"],
                    "negate": rule.get("negate", False)
                }]
            }
            if "contextKind" in rule:
                rule_value["clauses"][0]["contextKind"] = rule["contextKind"]
            
            patch_operations.append({
                "op": "add",
                "path": "/rules/-",
                "value": rule_value
            })
        
        response = requests.patch(url, headers=self.headers, json=patch_operations, timeout=self.REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            print(f"  ✅ Rules added to segment '{segment_key}'")
            return response.json()
        elif response.status_code == 429:
            print(f"  ⏳ Rate limited, waiting 2 seconds...")
            time.sleep(2)
            return self.add_segment_rules(project_key, environment_key, segment_key, rules)
        else:
            print(f"  ❌ Failed to add rules to segment '{segment_key}': {response.status_code} - {response.text}")
            return None

    def update_ai_config_targeting(self, project_key, config_key, environment_key, targeting_rules):
        """Update AI Config targeting using direct API call"""
        url = f"{self.base_url}/api/v2/projects/{project_key}/ai-configs/{config_key}/targeting"
        
        # Build targeting instructions from rules
        instructions = []
        
        for rule in targeting_rules:
            instruction = {
                "kind": "addRule",
                "clauses": rule["clauses"],
                "variationId": rule.get("variationId"),
                "trackEvents": rule.get("trackEvents", False)
            }
            instructions.append(instruction)
        
        payload = {
            "environmentKey": environment_key,
            "instructions": instructions,
            "comment": "Setting up multi-agent targeting rules"
        }
        
        response = requests.patch(url, headers=self.headers, json=payload, timeout=self.REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            print(f"✅ AI Config targeting updated for environment '{environment_key}'")
            time.sleep(0.5)  # Rate limiting delay
            return response.json()
        elif response.status_code == 429:
            print(f"⏳ Rate limited, waiting 2 seconds...")
            time.sleep(2)
            return self.update_ai_config_targeting(project_key, config_key, environment_key, targeting_rules)
        else:
            print(f"❌ Failed to update targeting: {response.status_code} - {response.text}")
            return None

    def get_ai_config(self, project_key, config_key):
        """Get AI Config details"""
        url = f"{self.base_url}/api/v2/projects/{project_key}/ai-configs/{config_key}"
        response = requests.get(url, headers=self.headers, timeout=self.REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            return response.json()
        return None

    def get_variation_map(self, ai_config_data):
        """Build variation map from AI Config data using variation IDs"""
        variation_map = {}
        if ai_config_data and "variations" in ai_config_data:
            for variation in ai_config_data["variations"]:
                variation_map[variation["key"]] = variation["_id"]  # Use _id, not id
        return variation_map

def main():
    # Get API key from environment
    api_key = os.getenv("LD_API_KEY")
    if not api_key:
        print("❌ LD_API_KEY environment variable not set")
        return
    
    # Load manifest
    manifest_path = Path("ai_config_manifest.yaml")
    if not manifest_path.exists():
        print(f"❌ Manifest file not found: {manifest_path}")
        return
        
    with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    
    creator = LaunchDarklyAIConfigCreator(api_key)
    
    project_key = manifest["project"]["key"]
    
    # Create segments if defined
    if "segment" in manifest["project"]:
        print(f"🎯 Creating segments in project: {project_key}")
        environment_key = "production"  # Default environment
        
        for segment in manifest["project"]["segment"]:
            creator.create_segment(project_key, environment_key, segment)
    
    # Create AI Model Configs
    ai_config = manifest["project"]["ai-config"]
    if "ai-model-configs" in ai_config:
        print(f"\n🤖 Creating {len(ai_config['ai-model-configs'])} AI Model Configs...")
        for model_config in ai_config["ai-model-configs"]:
            creator.create_ai_model_config(project_key, model_config)
    
    # Create AI Config
    ai_config = manifest["project"]["ai-config"]
    print(f"\n🚀 Creating AI Config in project: {project_key}")
    
    config_result = creator.create_ai_config(project_key, ai_config)
    if not config_result:
        return
    
    # Create variations
    print(f"\n📝 Creating {len(ai_config['variations'])} variations...")
    variation_map = {}
    for variation in ai_config["variations"]:
        result = creator.create_variation(project_key, ai_config["key"], variation)
        if result and "_id" in result:
            variation_map[variation["key"]] = result["_id"]  # Store variation ID
    
    # If no variations were created (already exist), get fresh AI Config data
    if not variation_map:
        print("📋 Loading existing variation mapping...")
        # Get fresh AI Config data with variations
        fresh_config = creator.get_ai_config(project_key, ai_config["key"])
        if fresh_config:
            variation_map = creator.get_variation_map(fresh_config)
        print(f"📊 Available variations: {list(variation_map.keys())}")
    else:
        print(f"📊 Available variations: {list(variation_map.keys())}")
    
    # Setup targeting rules if defined
    if "rules" in ai_config and variation_map:
        print(f"\n🎯 Setting up AI Config targeting rules...")
        print(f"📊 Available variations: {list(variation_map.keys())}")
        environment_key = "production"  # Default environment
        
        # Build targeting rules with variation indices
        targeting_rules = []
        print(f"🎯 Processing {len(ai_config['rules'])} targeting rules...")
        
        for i, rule in enumerate(ai_config["rules"], 1):
            # Find variation index based on segment name
            segment_key = rule["clauses"][0]["values"][0]  # e.g., "agent-teacher-orchestrator"
            variation_key = segment_key.replace("agent-", "")  # Keep hyphens: "teacher-orchestrator"
            
            print(f"  Rule {i}: segment='{segment_key}' -> variation='{variation_key}'")
            
            if variation_key in variation_map:
                variation_id = variation_map[variation_key]
                targeting_rule = {
                    "clauses": rule["clauses"],
                    "variationId": variation_id,
                    "trackEvents": rule.get("trackEvents", False)
                }
                targeting_rules.append(targeting_rule)
                print(f"    ✅ Created targeting rule with variationId: {variation_id}")
            else:
                print(f"    ❌ Variation key '{variation_key}' not found in variation map")
        
        print(f"📋 Total targeting rules created: {len(targeting_rules)}")
        
        if targeting_rules:
            creator.update_ai_config_targeting(project_key, ai_config["key"], environment_key, targeting_rules)
    
    print(f"\n✨ Setup complete!")

if __name__ == "__main__":
    main()
