# LaunchDarkly AI Config Bootstrap Script

This script automates the creation of LaunchDarkly AI Configs, variations, segments, and targeting rules for the multi-agent educational system.

## 🚀 Quick Start

### 1. Setup Environment
```bash
cd bootstrap
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements_ai_config.txt
```

### 2. Configure Environment Variables
```bash
export LD_API_KEY="your-launchdarkly-api-key"
export LD_PROJECT_KEY="your-project-key"
```

### 3. Run the Script
```bash
python create_ai_config.py
```

## 📋 What the Script Does

1. **Creates Segments** - User role-based segments for targeting
2. **Creates AI Config** - Main configuration container
3. **Creates Variations** - Specialized prompts for each agent
4. **Sets Up Targeting** - Routes users to appropriate variations based on role

## 📁 Required Files

- `ai_config_manifest.yaml` - Configuration manifest
- `../fallback_prompts/*.txt` - Fallback prompt files for each agent

## 🎯 Targeting Flow

```
User Role → Segment → AI Config Variation → Specialized Prompt
```

Example:
- Role: `computer-science-assistant` 
- Segment: `agent-computer-science-assistant`
- Variation: `computer-science-assistant`
- Prompt: Programming and CS expertise

## 📊 Output Example

```
🚀 Starting LaunchDarkly AI Config setup...
📦 Creating segments...
  ✅ Segment 'agent-teacher-orchestrator' created
  ✅ Segment 'agent-computer-science-assistant' created
🤖 Creating AI Config: multi-agent-llm-prompt-1
  ✅ AI Config created successfully
🎭 Creating variations...
  ✅ Variation 'teacher-orchestrator' created
  ✅ Variation 'computer-science-assistant' created
📊 Available variations: ['teacher-orchestrator', 'computer-science-assistant']
🎯 Setting up AI Config targeting rules...
  Rule 1: segment='agent-teacher-orchestrator' -> variation='teacher-orchestrator'
    ✅ Created targeting rule with variationId: fd317ad1-2031-4a81-9bdb-e8c865e46e5d
📋 Total targeting rules created: 2
✅ AI Config targeting updated for environment 'production'
✨ Setup complete!
```

## 🔧 Troubleshooting

### Common Issues

**Missing Environment Variables**
```
❌ LD_API_KEY environment variable not set
```
Solution: Set your LaunchDarkly API key

**Variation Key Mismatch**
```
❌ Variation key 'computer_science_assistant' not found in variation map
```
Solution: Check that segment names match variation keys (use hyphens, not underscores)

**Duplicate Rules**
```
❌ Failed to update targeting: 400 - new rule is exact duplicate
```
Solution: Delete existing AI Config or modify targeting rules

### Debug Mode
Add detailed logging by modifying the script or checking the console output for step-by-step progress.

## 📝 Manifest Structure

The `ai_config_manifest.yaml` defines:
- **Segments**: User role targeting
- **AI Config**: Main configuration
- **Variations**: Agent-specific prompts
- **Rules**: Targeting logic

## 🔄 Re-running the Script

The script handles existing resources:
- **Segments**: Skips if already exist
- **AI Config**: Skips if already exists  
- **Variations**: Skips if already exist
- **Targeting**: Updates existing rules

## 🛡️ Security

- Never commit API keys to version control
- Use environment variables for sensitive data
- Ensure proper LaunchDarkly project permissions
