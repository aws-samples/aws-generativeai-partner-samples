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

#### Recommended: Skip Existing Resources
```bash
python create_ai_config.py --skip-existing
```

#### Other Options
```bash
# Normal mode (may encounter conflicts)
python create_ai_config.py

# Force targeting updates (use with caution)
python create_ai_config.py --skip-existing --force-targeting

# Show help
python create_ai_config.py --help
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

### Fixed Issues (Latest Version)

The script has been updated to handle common errors:

1. **Resources already exist**: Gracefully handles existing segments, AI model configs, AI configs, and variations
2. **YAML syntax error**: Fixed malformed YAML in the manifest file
3. **Targeting rule conflicts**: Smart conflict detection to avoid duplicate targeting rules
4. **Internal service errors**: Improved error handling and resource existence checking

### Common Issues & Solutions

**Missing Environment Variables**
```
❌ LD_API_KEY environment variable not set
```
Solution: Set your LaunchDarkly API key or add to `.env` file

**"Already exists" errors**
```
❌ Segment already exists
```
Solution: Use `--skip-existing` flag

**Variation Key Mismatch**
```
❌ Variation key 'computer_science_assistant' not found in variation map
```
Solution: Check that segment names match variation keys (use hyphens, not underscores)

**Duplicate Targeting Rules**
```
❌ Failed to update targeting: 400 - new rule is exact duplicate
```
Solution: Script now automatically detects and skips duplicate rules

**Internal Service Errors**
```
❌ 500 Internal Server Error
```
Solution: Usually resolved by improved error handling in latest version

### Debug Mode
Add detailed logging by modifying the script or checking the console output for step-by-step progress.

## 📝 Manifest Structure

The `ai_config_manifest.yaml` defines:
- **Segments**: User role targeting
- **AI Config**: Main configuration
- **Variations**: Agent-specific prompts
- **Rules**: Targeting logic

## 🔄 Re-running the Script

The script intelligently handles existing resources:
- **Segments**: Skips if already exist (with `--skip-existing`)
- **AI Config**: Skips if already exists  
- **Variations**: Skips if already exist
- **Targeting**: Detects and avoids duplicate rules

### Command Line Options

- `--skip-existing`: Skip creating resources that already exist (recommended)
- `--force-targeting`: Force targeting rule updates even if rules exist (use with caution)
- `--help`: Show all available options

## 🛡️ Security

- Never commit API keys to version control
- Use environment variables for sensitive data
- Ensure proper LaunchDarkly project permissions
